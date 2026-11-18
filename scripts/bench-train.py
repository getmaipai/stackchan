#!/usr/bin/env python3
"""One bench train, start to finish, with no model in the loop: flash, soak and proof checklist in parallel, pixel-diff against the goldens, one result file.

  bench-train.py MANIFEST.json [--no-flash] [--queue QUEUE.json] [--out-dir DIR]
  bench-train.py --queue QUEUE.json          run every waiting manifest back to back (a queue file is {"waiting": [paths], "done": []})

Intent: the single bench unit is the slow part of every proof. A train used to be a soak of 10.5 minutes and then the checks. This runs the soak and the checks at
once, so a train takes about the soak time (11 minutes), and it needs no one to read anything: the result file says PASS or FAIL for each check, the memory gate
and the restart counter. Steps: (1) check the build, flash the app and the assets, wait for the unit to answer; (2) put the unit in the silent bench state (mute, full
quiet, sounds off, volume 0), and put it back every time the unit restarts, because a restart resets it to volume 70 (found by the bench, 2026-11-18); (3) sample the
heap during the soak while the checklist runs: tool checks with expected values, and snapshots compared with the playground goldens within a tolerance file;
(4) write result.md and result.json, then restore the silent state. A failing check never stops the train: the bench agent reads the result and handles failures
and the touch-only items listed under "person". Opening the serial port resets the unit, so the train opens it once.
Manifest: {"name", "build_dir", "soak_s" (630), "settle_s" (2), "goldens_dir", "tolerance_file", "heap_interval_s" (20), "gate": {...}, "checks": [...], "person": ["touch only items"]}.
A check is {"name", "tool", "args", "expect": {"path": value | {"min","max","regex"}}, "wait"} or {"name", "snapshot": "<golden name>", "pre": [{"tool","args"}], "post": [...]}.
Placement: the machine that holds the cable (development only). Upstream: none. The unit is never flashed unless the manifest says so and --no-flash is absent.
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import re
import statistics
import struct
import subprocess
import sys
import threading
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE = [
    ("self.privacy.set", {"mute": 1, "quiet": 1}),
    ("self.audio.set_sound_policy", {"enabled": False, "muted": True, "quiet_now": True}),
    ("self.audio_speaker.set_volume", {"volume": 0}),
]
GATE = {"internal_free_median_min": 40000, "internal_min_min": 24000, "internal_big_median_min": 24000, "internal_big_min_min": 16000}
HEAP_KEYS = {"free": "internal_free", "min": "internal_min", "big": "internal_big"}
BOOT = re.compile(r"ESP-ROM:|rst:0x|Rebooting\.\.\.")
PANIC = re.compile(r"assert failed|Guru Meditation|abort\(\) was called|Backtrace:|panic'ed", re.I)


# ---------- pure parts (tested without a unit) ----------
def lookup(obj, path: str):
    for part in path.split("."):
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        elif isinstance(obj, list) and part.isdigit() and int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return None
    return obj


def expect_failures(reply: dict, expect: dict) -> list[str]:
    bad = []
    for path, want in expect.items():
        got = lookup(reply, path)
        if isinstance(want, dict):
            if "min" in want and not (isinstance(got, (int, float)) and got >= want["min"]):
                bad.append(f"{path} is {got!r}, wanted at least {want['min']}")
            if "max" in want and not (isinstance(got, (int, float)) and got <= want["max"]):
                bad.append(f"{path} is {got!r}, wanted at most {want['max']}")
            if "regex" in want and not (isinstance(got, str) and re.search(want["regex"], got)):
                bad.append(f"{path} is {got!r}, wanted a match for {want['regex']}")
        elif got != want:
            bad.append(f"{path} is {got!r}, wanted {want!r}")
    return bad


def memory_verdict(samples: list[dict], gate: dict) -> tuple[bool, dict, list[str]]:
    free = [s["free"] for s in samples if s.get("free") is not None]
    mins = [s["min"] for s in samples if s.get("min") is not None]
    big = [s["big"] for s in samples if s.get("big") is not None]
    if not free or not big:
        return False, {}, ["no heap samples were read: check the heap_keys of the manifest and that the image is a bench image"]
    nums = {
        "internal_free_median": int(statistics.median(free)),
        "internal_min": min(mins) if mins else min(free),
        "internal_big_median": int(statistics.median(big)),
        "internal_big_min": min(big),
    }
    bad = []
    if nums["internal_free_median"] < gate["internal_free_median_min"]:
        bad.append(f"internal free median {nums['internal_free_median']} is under {gate['internal_free_median_min']}")
    if nums["internal_min"] < gate["internal_min_min"]:
        bad.append(f"internal lowest {nums['internal_min']} is under {gate['internal_min_min']}")
    if nums["internal_big_median"] < gate["internal_big_median_min"]:
        bad.append(f"largest block median {nums['internal_big_median']} is under {gate['internal_big_median_min']}")
    if nums["internal_big_min"] < gate["internal_big_min_min"]:
        bad.append(f"largest block lowest {nums['internal_big_min']} is under {gate['internal_big_min_min']}")
    return not bad, nums, bad


def scan_console(text: str) -> dict:
    return {"boots": len(BOOT.findall(text)), "panics": len(PANIC.findall(text))}


def read_png(path: Path) -> tuple[int, int, bytes]:
    """RGB bytes of a PNG: Pillow when it is installed, else a small reader (8 bit, not interlaced, RGB, RGBA or gray)."""
    try:
        from PIL import Image  # type: ignore

        im = Image.open(path).convert("RGB")
        return im.width, im.height, im.tobytes()
    except ImportError:
        pass
    data = path.read_bytes()
    pos, chunks = 8, {}
    idat = b""
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + n]
        if kind == b"IDAT":
            idat += body
        else:
            chunks[kind] = body
        pos += 12 + n
    w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", chunks[b"IHDR"])
    if depth != 8 or interlace or ctype not in (0, 2, 6):
        raise ValueError(f"{path.name}: install Pillow to read this kind of PNG (uv run --with pillow)")
    bpp = {0: 1, 2: 3, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * bpp
    prev = bytearray(stride)
    out = bytearray()
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        prev = line
        for x in range(w):
            px = line[x * bpp : (x + 1) * bpp]
            out += bytes(px[:3]) if bpp >= 3 else bytes((px[0],) * 3)
    return w, h, bytes(out)


def pixel_diff(a: tuple[int, int, bytes], b: tuple[int, int, bytes], channel: int, ignore: list[list[int]]) -> tuple[int, int]:
    """(pixels that differ by more than `channel` in any color, pixels compared), outside the ignored rectangles. Sizes must match."""
    (w, h, da), (w2, h2, db) = a, b
    if (w, h) != (w2, h2):
        return -1, 0
    bad = total = 0
    for y in range(h):
        for x in range(w):
            if any(rx <= x < rx + rw and ry <= y < ry + rh for rx, ry, rw, rh in ignore):
                continue
            i = (y * w + x) * 3
            total += 1
            if abs(da[i] - db[i]) > channel or abs(da[i + 1] - db[i + 1]) > channel or abs(da[i + 2] - db[i + 2]) > channel:
                bad += 1
    return bad, total


def compare_snapshot(shot: Path, golden: Path, tol: dict) -> tuple[str, str]:
    """(PASS | FAIL | NOGOLDEN, detail)."""
    if not golden.exists():
        return "NOGOLDEN", f"no golden at {golden.name}: the snapshot is kept as the candidate"
    bad, total = pixel_diff(read_png(shot), read_png(golden), tol["channel"], tol.get("ignore", []))
    if bad < 0:
        return "FAIL", "the snapshot and the golden have different sizes"
    frac = bad / max(total, 1)
    return ("PASS" if frac <= tol["fraction"] else "FAIL"), f"{bad} of {total} pixels differ ({frac:.2%}; allowed {tol['fraction']:.2%} at channel tolerance {tol['channel']})"


def tolerance_for(tolerances: dict, name: str) -> dict:
    out = {"channel": 12, "fraction": 0.01, "ignore": []}
    out.update(tolerances.get("default", {}))
    out.update(tolerances.get(name, {}))
    return out


# ---------- the unit ----------
class SerialUnit:
    """The real unit through scripts/fw-serial.py's serve socket (one port holder, one request at a time)."""

    def __init__(self, out_dir: Path, port: str | None = None):
        os.environ["MAIPAI_SERIAL_TMP"] = str(out_dir)
        if port:
            os.environ["MAIPAI_SERIAL_PORT"] = port
        spec = importlib.util.spec_from_file_location("fw_serial", ROOT / "scripts" / "fw-serial.py")
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.out = out_dir
        self.lock = threading.Lock()
        self.proc: subprocess.Popen | None = None

    @property
    def log_path(self) -> Path:
        return Path(self.mod.LOG)

    def start(self) -> None:
        self.proc = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "fw-serial.py"), "serve"], env=os.environ.copy(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def call(self, name: str, args: dict | None = None, wait: float = 30.0) -> dict:
        with self.lock:
            return self.mod.ask(name, args or {}, wait)[0]

    def snapshot(self, path: Path) -> None:
        with self.lock:
            _, snaps = self.mod.ask("self.face.snapshot", {}, 30.0)
        self.mod.snaps_to_png(snaps, str(path))

    def console(self) -> str:
        return self.log_path.read_text(errors="replace") if self.log_path.exists() else ""

    def stop(self) -> None:
        if self.proc:
            self.proc.terminate()


def flash(build_dir: Path, port: str | None) -> None:
    """Flash the app and the assets partition with esptool from the build folder (the build kind decides the assets image)."""
    env_sh = ROOT / "scripts" / "fw-env.sh"
    port = port or next(iter(sorted(glob.glob("/dev/cu.usbmodem*"))), "")
    if not port:
        raise RuntimeError("no USB serial port found. Plug the unit in with the data cable, then run the train again.")
    cmd = (
        f"source {env_sh} && cd {build_dir} && "
        f"python -m esptool --chip esp32s3 -p {port} -b 921600 write_flash @flash_args && "
        f"python -m esptool --chip esp32s3 -p {port} -b 921600 write_flash 0xA00000 generated_assets.bin"
    )
    done = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"flashing failed: {(done.stderr or done.stdout)[-400:]}. Check the cable and the build folder, then run the train again.")


# ---------- the train ----------
def apply_safe(unit, extra: list | None = None) -> list[str]:
    bad = []
    for name, args in SAFE + [(c["tool"], c.get("args", {})) for c in (extra or [])]:
        try:
            unit.call(name, args, 15.0)
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{name}: {exc}")
    return bad


def wait_ready(unit, timeout: float, sleep=time.sleep, clock=time.time) -> bool:
    end = clock() + timeout
    while clock() < end:
        try:
            unit.call("self.privacy.get", {}, 5.0)
            return True
        except Exception:  # noqa: BLE001
            sleep(2)
    return False


def run_check(unit, check: dict, golden_dir: Path, tolerances: dict, out: Path, settle: float, sleep=time.sleep) -> dict:
    res = {"name": check["name"], "status": "PASS", "detail": ""}
    try:
        for step in check.get("pre", []):
            unit.call(step["tool"], step.get("args", {}), step.get("wait", 30))
        if "snapshot" in check:
            sleep(check.get("settle_s", settle))
            shot = out / f"{check['name']}.png"
            unit.snapshot(shot)
            status, detail = compare_snapshot(shot, golden_dir / f"{check['snapshot']}.png", tolerance_for(tolerances, check["snapshot"]))
            res.update(status=status, detail=detail)
        else:
            reply = unit.call(check["tool"], check.get("args", {}), check.get("wait", 30))
            bad = expect_failures(reply, check.get("expect", {"ok": True}))
            res.update(status="FAIL" if bad else "PASS", detail="; ".join(bad) or json.dumps(reply)[:160])
        for step in check.get("post", []):
            unit.call(step["tool"], step.get("args", {}), step.get("wait", 30))
    except Exception as exc:  # noqa: BLE001
        res.update(status="FAIL", detail=f"the check could not run: {exc}")
    return res


def run_train(man: dict, unit, out: Path, sleep=time.sleep, clock=time.time) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    gate = {**GATE, **man.get("gate", {})}
    keys = {**HEAP_KEYS, **man.get("heap_keys", {})}
    soak = float(man.get("soak_s", 630))
    golden_dir = ROOT / man.get("goldens_dir", "host/tests/golden/screens")
    tol_file = ROOT / man.get("tolerance_file", "host/tests/golden/tolerance.json")
    tolerances = json.loads(tol_file.read_text()) if tol_file.exists() else {}
    result: dict = {"train": man["name"], "checks": [], "problems": []}
    if not wait_ready(unit, man.get("ready_timeout_s", 120), sleep, clock):
        result["problems"].append("the unit did not answer in time: no tool reply. Check the flash and the cable.")
        return finish(result, [], "", unit, out, man)
    result["problems"] += [f"silent state: {p}" for p in apply_safe(unit)]
    began = clock()
    samples: list[dict] = []
    stop = threading.Event()
    seen_boots = [scan_console(unit.console())["boots"]]
    restarts = [0]

    def sampler():
        while not stop.is_set():
            try:
                r = unit.call("self.bench.heap_info", {}, 10.0)
                samples.append({k: (r.get(v) if isinstance(r, dict) else None) for k, v in keys.items()})
            except Exception:  # noqa: BLE001
                pass
            boots = scan_console(unit.console())["boots"]
            if boots > seen_boots[0]:   # a restart resets privacy to mute and volume 70: put the silent state back at once
                restarts[0] += boots - seen_boots[0]
                seen_boots[0] = boots
                wait_ready(unit, 60, sleep, clock)
                apply_safe(unit)
            stop.wait(man.get("heap_interval_s", 20))

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    for check in man.get("checks", []):
        result["checks"].append(run_check(unit, check, golden_dir, tolerances, out, man.get("settle_s", 2), sleep))
    while clock() - began < soak:
        sleep(min(5, max(0.1, soak - (clock() - began))))
    stop.set()
    th.join(timeout=15)
    result["restarts"] = restarts[0]
    return finish(result, samples, unit.console(), unit, out, man, gate)


def finish(result: dict, samples: list[dict], console: str, unit, out: Path, man: dict, gate: dict | None = None) -> dict:
    gate = gate or {**GATE, **man.get("gate", {})}
    ok, nums, bad = memory_verdict(samples, gate)
    scan = scan_console(console)
    result["memory"] = {"pass": ok, "numbers": nums, "problems": bad, "samples": len(samples)}
    result["console"] = {**scan, "restarts_seen_after_first_boot": max(scan["boots"] - 1, 0)}
    result["person"] = man.get("person", [])
    result["pass"] = (
        not result["problems"]
        and ok
        and scan["panics"] == 0
        and result.get("restarts", 0) == 0
        and all(c["status"] in ("PASS", "NOGOLDEN") for c in result["checks"])
    )
    try:   # the silent state goes back last, so the unit is left as the bench agent leaves it
        apply_safe(unit, man.get("restore"))
    except Exception:  # noqa: BLE001
        pass
    (out / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    lines = [f"# Train {result['train']}: {'PASS' if result['pass'] else 'FAIL'}", ""]
    lines += [f"- {c['status']}: {c['name']}: {c['detail']}" for c in result["checks"]]
    lines += [f"- {'PASS' if ok else 'FAIL'}: memory gate {nums}; " + ("; ".join(bad) or "inside the gate"), f"- {'PASS' if scan['panics'] == 0 else 'FAIL'}: assert or panic lines {scan['panics']}"]
    lines += [f"- {'PASS' if result.get('restarts', 0) == 0 else 'FAIL'}: restarts during the train {result.get('restarts', 0)}"]
    lines += [f"- PROBLEM: {p}" for p in result["problems"]]
    lines += [f"- PERSON: {p}" for p in result["person"]]
    (out / "result.md").write_text("\n".join(lines) + "\n")
    return result


def run_manifest(path: Path, args, out_root: Path) -> dict:
    man = json.loads(path.read_text())
    out = out_root / man["name"]
    out.mkdir(parents=True, exist_ok=True)
    unit = SerialUnit(out, args.port)
    try:
        if man.get("build_dir") and not args.no_flash:
            build = Path(os.path.expanduser(man["build_dir"]))
            if not (build / "flash_args").exists() or not (build / "generated_assets.bin").exists():
                raise RuntimeError(f"{build} has no flash_args or generated_assets.bin. Build the kind first (scripts/fw-build.sh).")
            flash(build, args.port)
        unit.start()
        return run_train(man, unit, out)
    finally:
        unit.stop()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("manifest", nargs="?")
    ap.add_argument("--queue")
    ap.add_argument("--no-flash", action="store_true")
    ap.add_argument("--port")
    ap.add_argument("--out-dir", default=str(ROOT / ".runs" / "trains"))
    args = ap.parse_args(argv)
    out_root = Path(args.out_dir)
    worst = 0
    if args.manifest:
        res = run_manifest(Path(args.manifest), args, out_root)
        print(f"{res['train']}: {'PASS' if res['pass'] else 'FAIL'} ({out_root / res['train'] / 'result.md'})")
        worst = 0 if res["pass"] else 2
    if args.queue:
        qpath = Path(args.queue)
        while True:
            q = json.loads(qpath.read_text())
            if not q.get("waiting"):
                break
            nxt = q["waiting"][0]
            try:
                res = run_manifest(Path(nxt), args, out_root)
                line = {"manifest": nxt, "pass": res["pass"], "result": str(out_root / res["train"] / "result.md")}
            except RuntimeError as exc:   # a build or port problem: record it and go on to the next waiting train
                line = {"manifest": nxt, "pass": False, "error": str(exc)}
            q = json.loads(qpath.read_text())
            q["waiting"] = [w for w in q["waiting"] if w != nxt]
            q.setdefault("done", []).append(line)
            qpath.write_text(json.dumps(q, indent=1) + "\n")
            print(json.dumps(line))
            worst = max(worst, 0 if line["pass"] else 2)
    if not args.manifest and not args.queue:
        ap.print_usage()
        return 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
