"""More end to end scenarios for e2e.py: the unit's own cores in the loop, the leak canary and the long idle jump.

The unit's gesture, key schedule, listening guard and remote session rules are the firmware's own headers (the patch ORDER replayed into an empty folder), compiled into
tiny command line programs, so a scenario asks the unit's code what the unit would do and sends the result to the real host. Nothing here copies a rule.
Scenarios: privacy_tap listen_ended key_exchange host_id_first_wins idle_jump soak (soak runs only with MAIPAI_SOAK=1; MAIPAI_SOAK_TURNS sets the count, default 500).
Placement: host-side development tool. Upstream: none.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".runs" / "vu-build" / "shims"
SHIM_SOURCES = {"touch_shim": "touch_shim.c", "link_shim": "link_shim.c", "remote_shim": "remote_shim.c", "listen_guard": "listen_guard.c"}


def shims() -> dict[str, Path]:
    """Build (or reuse) the unit's core programs. A stamp of the patches and sources decides when to rebuild."""
    here = Path(__file__).resolve().parent
    h = hashlib.sha1()
    for f in sorted((ROOT / "firmware" / "patches").glob("*.patch")) + [here / s for s in SHIM_SOURCES.values()]:
        h.update(f.read_bytes())
    stamp = h.hexdigest()
    BUILD.mkdir(parents=True, exist_ok=True)
    out = {name: BUILD / name for name in SHIM_SOURCES}
    if (BUILD / "stamp").is_file() and (BUILD / "stamp").read_text() == stamp and all(p.is_file() for p in out.values()):
        return out
    from firmware_order_cores import build_cores  # host/tests, on the path of e2e.py

    with tempfile.TemporaryDirectory(prefix="vu-cores-") as work:
        subprocess.run(["git", "init", "-q", work], check=True)
        cores = build_cores(Path(work))
        for name, source in SHIM_SOURCES.items():
            subprocess.run(["cc", "-std=gnu99", "-Wall", f"-I{cores}", str(here / source), "-o", str(out[name])], check=True)
    (BUILD / "stamp").write_text(stamp)
    return out


class Program:
    """A shim kept open: write a line, read a line."""

    def __init__(self, path: Path) -> None:
        self.proc = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

    def ask(self, line: str) -> str:
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        return self.proc.stdout.readline().strip()

    def send(self, line: str) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.stdin.close()  # type: ignore[union-attr]
            self.proc.wait(timeout=5)


def gesture(touch: Program, x: int, y: int, ms: int, switches: tuple[int, int, int], t0: int = 1000) -> dict[str, str]:
    """One press at (x, y) held for `ms`, with the three switches (mute, vision, quiet) as they are now; the unit's gesture core answers."""
    touch.send(f"down {x} {y} {t0}")
    line = touch.ask(f"up {t0 + ms} {switches[0]} {switches[1]} {switches[2]}")
    return dict(part.split("=", 1) for part in line.split())


def push_privacy_event(rig, state: dict[str, int], source: str = "unit") -> None:
    """What the unit does after a switch changes: its own state and the privacy event the host reads on its next poll."""
    with rig.fw.vu_lock:
        rig.vu.call("self.privacy.get", {})   # the tool groups create their state on first use
        p = rig.vu.state["audio"]["privacy"]
        p.update(state)
        p["mic_off"] = int(bool(p["muted"] or p["quiet"]))
        p["mic_off_verified"] = p["mic_off"]
        p["mute_source"] = source
        rig.vu.call("self.robot.get_events", {})   # makes the motion state exist
        rig.vu.state["motion"]["events"].append({"kind": "privacy", "at_ms": rig.vu.now_ms, "muted": p["muted"], "vision_off": p["vision_off"], "quiet": p["quiet"],
                                                   "mic_off_verified": p["mic_off_verified"], "mute_source": source})


async def _host_saw(rig, pattern: str, mark: int, timeout: float = 15.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if any(re.search(pattern, line) for line in rig.log[mark:]):
            return True
        await asyncio.sleep(0.25)
    return False


# ---- scenarios -------------------------------------------------------------------------------------

async def privacy_tap(rig, check) -> None:
    """The unit's own gesture rule (SF02): a tap on the mouth turns the mute on, a tap while it is on does nothing, a hold turns it off. The host must follow each change."""
    touch = Program(shims()["touch_shim"])
    try:
        check("the host read the unit's privacy state after it connected", await _host_saw(rig, r"StackChan privacy: muted=False", 0, 30.0))   # events sent before this are dropped by the host's first look
        mark = len(rig.log)
        first = gesture(touch, 150, 170, 120, (0, 0, 0))
        check("the unit reads a tap on the mouth as a mute toggle", first.get("result") == "toggle:mute", str(first))
        push_privacy_event(rig, {"muted": 1})
        check("the host followed the tap: muted", await _host_saw(rig, r"privacy: muted=True", mark), "; ".join(l[-100:] for l in rig.log[mark:] if "privacy" in l)[:300])
        second = gesture(touch, 150, 170, 120, (1, 0, 0))
        check("a second tap while muted does nothing", second.get("result", "").startswith("ignored"), str(second))
        third = gesture(touch, 150, 170, 700, (1, 0, 0))
        check("a hold of 0.7 s while muted turns it off", third.get("kind") == "hold" and third.get("result") == "toggle:mute", str(third))
        mark = len(rig.log)
        push_privacy_event(rig, {"muted": 0})
        check("the host followed the hold: unmuted", await _host_saw(rig, r"privacy: muted=False", mark), "; ".join(l[-100:] for l in rig.log[mark:] if "privacy" in l)[:300])
        eyes = gesture(touch, 80, 100, 120, (0, 0, 0))
        check("a tap on an eye is the camera switch", eyes.get("result") == "toggle:vision", str(eyes))
    finally:
        touch.close()


async def listen_ended(rig, check) -> None:
    """After the wake word and no speech the unit's guard (SF03) ends listening at the follow-up time. The unit's rule says when; the host must end the turn without an answer."""
    guard = subprocess.run([str(shims()["listen_guard"]), "8", "60", "0", "0"], capture_output=True, text=True, timeout=10).stdout.strip()
    ends_at = int(re.search(r"ends at (\d+)", guard).group(1)) if "ends at" in guard else -1
    check("the unit's guard ends a quiet listening state at the follow-up time (8 s)", ends_at == 8, guard)
    mark = len(rig.log)
    await rig.quiet(float(ends_at))
    check("the host ended the quiet turn with no answer", await _host_saw(rig, r"no speech to answer|voice turn", mark, 40.0), "; ".join(l[-100:] for l in rig.log[mark:])[-300:])
    check("no model request was made for silence", not rig.models.llm_requests)
    with rig.fw.vu_lock:
        rig.vu.call("self.robot.set_idle_motion", {"enabled": False})   # makes the motion state exist
        rig.vu.state["motion"]["events"].append({"kind": "listen_ended", "at_ms": rig.vu.now_ms, "held_s": ends_at, "why": "follow_up"})
    await asyncio.sleep(2.0)
    check("the host read the unit's listen_ended event (it logs that its reaction was skipped)", rig.host_said(r"\(listen_ended\)"), "; ".join(l[-120:] for l in rig.log[-6:]))


async def key_exchange(rig, check) -> None:
    """The six digit key exchange (SF20): an unpaired unit asks to pair, computes the six digits with its own key schedule, the owner types them on the settings page, and the host answers paired."""
    import websockets
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    link = Program(shims()["link_shim"])
    device, client = "02:00:00:00:00:A1", "00000000-0000-4000-8000-0000000000a1"

    def b64(raw: bytes) -> str:
        return base64.b64encode(raw).decode()

    def post_code(code: str) -> tuple[int, str]:
        import urllib.request

        req = urllib.request.Request(f"http://127.0.0.1:{rig.settings_port}/api/stackchan/pairings/code-entry", data=json.dumps({"device_id": device, "code": code}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode()
        except Exception as error:  # noqa: BLE001
            return getattr(error, "code", 0), str(error)

    try:
        sk = X25519PrivateKey.generate()
        pk_u = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        n_u = os.urandom(16)
        async with websockets.connect(f"ws://127.0.0.1:{rig.xiaozhi_port}", additional_headers={"Device-Id": device, "Client-Id": client, "Protocol-Version": "1", "Pair-Exchange": "1"}) as ws:
            await ws.send(json.dumps({"type": "pair_start", "pk_u": b64(pk_u)}))
            host = json.loads(await asyncio.wait_for(ws.recv(), 10))
            pk_h, commitment = base64.b64decode(host["pk_h"]), base64.b64decode(host["c"])
            await ws.send(json.dumps({"type": "pair_nonce", "n_u": b64(n_u)}))
            reveal = json.loads(await asyncio.wait_for(ws.recv(), 10))
            n_h = base64.b64decode(reveal["n_h"])
            want = link.ask(f"commit {pk_h.hex()} {pk_u.hex()} {n_h.hex()}")
            check("the host's commitment matches what the unit's key schedule computes", want == commitment.hex(), f"{want[:16]} vs {commitment.hex()[:16]}")
            digits = link.ask(f"sas {pk_u.hex()} {pk_h.hex()} {n_u.hex()} {n_h.hex()}")
            check("the unit shows six digits", bool(re.fullmatch(r"\d{6}", digits)), digits)
            wrong = f"{(int(digits) + 1) % 1000000:06d}"
            status, body = await asyncio.to_thread(post_code, wrong)
            check("a wrong code is refused on the settings page", status == 400, f"{status} {body[:120]}")
            frame = json.loads(await asyncio.wait_for(ws.recv(), 10))
            check("the host tells the unit the pairing failed", frame.get("type") == "pair_failed", str(frame))
        # a second try with the right digits (the first exchange is over for good)
        sk = X25519PrivateKey.generate()
        pk_u = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        n_u = os.urandom(16)
        async with websockets.connect(f"ws://127.0.0.1:{rig.xiaozhi_port}", additional_headers={"Device-Id": device, "Client-Id": client, "Protocol-Version": "1", "Pair-Exchange": "1"}) as ws:
            await ws.send(json.dumps({"type": "pair_start", "pk_u": b64(pk_u)}))
            host = json.loads(await asyncio.wait_for(ws.recv(), 10))
            pk_h = base64.b64decode(host["pk_h"])
            await ws.send(json.dumps({"type": "pair_nonce", "n_u": b64(n_u)}))
            n_h = base64.b64decode(json.loads(await asyncio.wait_for(ws.recv(), 10))["n_h"])
            digits = link.ask(f"sas {pk_u.hex()} {pk_h.hex()} {n_u.hex()} {n_h.hex()}")
            status, body = await asyncio.to_thread(post_code, digits)
            check("the unit's six digits typed on the settings page are accepted", status == 200, f"{status} {body[:160]}")
            frame = json.loads(await asyncio.wait_for(ws.recv(), 10))
            check("the host tells the unit it is paired", frame.get("type") == "paired", str(frame))
    finally:
        link.close()


async def host_id_first_wins(rig, check) -> None:
    """The unit keeps the host id of a remote session once (SF01), refuses a cued call that carries another one, and drops the id when the session ends or goes quiet for 10 s (the unit's core).
    The host half needs a controller session, which the rig does not start."""
    remote = Program(shims()["remote_shim"])
    try:
        remote.ask("session 1 111 1000")
        again = remote.ask("session 1 222 4000")
        check("a later heartbeat with another host id does not change it", again == "active=1 host=111", again)
        check("a cued call with the first id passes", remote.ask("call dance 111 5000") == "ok")
        check("a cued call with the second id is refused", remote.ask("call dance 222 5000") == "not_host")
        check("a head move inside the safe range needs no id", remote.ask("call move_near 0 5000") == "ok")
        remote.ask("session 0 0 6000")
        check("the id is dropped with the session", remote.ask("host") == "0")
        check("a new session takes a new id", remote.ask("session 1 222 7000") == "active=1 host=222")
        check("a session silent for 10 s is gone and its id with it", remote.ask("call dance 111 18000") == "ok" and remote.ask("host") == "0")
    finally:
        remote.close()
    check("the host started a controller session and the unit kept the first id", False, known_gap="the rig has no controller client: the host sends self.remote.session only for a live remote controller (needs a controller driver in the rig)")


async def idle_jump(rig, check) -> None:
    """The unit left on for days: the fake clock jumps by 3 days, 25 days (past 2^31 ms) and 50 days (past 2^32 ms, the 32 bit tick wraps). Face, timers and a spoken turn must work after each jump."""
    day = 86_400_000
    names = []
    for label, ms in (("3 days", 3 * day), ("25 days", 22 * day), ("50 days", 25 * day)):
        with rig.fw.vu_lock:
            rig.vu.call("self.timer.set", {"seconds": 5, "label": f"after {label}"})
            rig.vu.jump(ms)
            rig.vu.advance(6000)
            listed = rig.vu.call("self.timer.list", {})
            lit = rig.vu.count(0, 30, 320, 150)["lit"]
        names.append(label)
        check(f"after {label} the unit's timer that was due rings", bool(listed.get("ringing")), json.dumps(listed)[:160])
        check(f"after {label} the face is still drawn", lit > 1500, str(lit))
        with rig.fw.vu_lock:
            rig.vu.call("self.timer.stop", {})
    rig.models.llm_script.append((r"after", "Still here."))
    await rig.say("are you still here after all this time")
    check("a spoken turn works after the jumps", any("Still here" in t for t in rig.models.tts_requests))
    check("the host did not log an error line", not rig.host_said(r"\bERROR\b|Traceback"))
    check("the host process clock jumped too", False, known_gap="the host runs on the machine's own clock; no tool here moves another process's clock (host cores are covered by fake-clock tests and the wrap soak)")


SOAK_LIMITS = {"rss_mb": 25.0, "rss_pct": 20.0, "threads": 2, "fds": 4, "sockets": 2}


def leak_verdict(before: dict, after: dict, limits: dict | None = None) -> list[str]:
    """The reasons a run counts as a leak: what grew past the limit between two samples ({rss_mb, threads, fds, sockets}). Empty means no growth worth failing on."""
    lim = {**SOAK_LIMITS, **(limits or {})}
    bad = []
    grew = after["rss_mb"] - before["rss_mb"]
    if grew > lim["rss_mb"] and grew > before["rss_mb"] * lim["rss_pct"] / 100.0:
        bad.append(f"memory grew {grew:.1f} MB ({before['rss_mb']:.0f} to {after['rss_mb']:.0f})")
    for key in ("threads", "fds", "sockets"):
        if after[key] - before[key] > lim[key]:
            bad.append(f"{key} grew from {before[key]} to {after[key]}")
    return bad


def sample(pid: int) -> dict:
    import psutil

    p = psutil.Process(pid)
    try:
        sockets = len(p.net_connections(kind="inet"))
    except (psutil.AccessDenied, NotImplementedError):
        sockets = -1
    return {"rss_mb": p.memory_info().rss / 1e6, "threads": p.num_threads(), "fds": p.num_fds(), "sockets": max(0, sockets)}


async def soak(rig, check) -> None:
    """A long run of spoken turns against the real host, sampling its memory, threads, descriptors and sockets: a leak canary. Only with MAIPAI_SOAK=1 (it takes minutes)."""
    if os.environ.get("MAIPAI_SOAK") != "1":
        print("  skip soak: set MAIPAI_SOAK=1 to run it (MAIPAI_SOAK_TURNS sets the count, default 500)")
        return
    turns = int(os.environ.get("MAIPAI_SOAK_TURNS", "500"))
    rig.models.llm_script.append((r"soak", "Noted."))
    for i in range(10):   # warm up: the first turns load models and caches, so the baseline is taken after them
        await rig.say(f"soak warm {i}", speech_s=0.5, tail_s=0.9, pace=0.03, wait_stop=30.0)
    before = sample(rig.proc.pid)
    series = [before]
    ok = 0
    start = time.time()
    for i in range(turns):
        mark = len(rig.models.tts_requests)
        await rig.say(f"soak turn {i}", speech_s=0.5, tail_s=0.9, pace=0.03, wait_stop=30.0)
        ok += int(len(rig.models.tts_requests) > mark)
        if (i + 1) % max(1, turns // 10) == 0:
            series.append(sample(rig.proc.pid))
            print(f"    turn {i + 1}/{turns}: " + ", ".join(f"{k} {v:.0f}" for k, v in series[-1].items()) + f", {time.time() - start:.0f} s", flush=True)
    after = sample(rig.proc.pid)
    check(f"{turns} turns all got a spoken reply", ok == turns, f"{ok} of {turns}")
    problems = leak_verdict(before, after)
    check("the host did not grow in memory, threads, descriptors or sockets", not problems, "; ".join(problems))
    check("the host did not log an error line", not rig.host_said(r"\bERROR\b|Traceback"), "; ".join(l[:140] for l in rig.log if re.search(r"\bERROR\b|Traceback", l))[:300])


EXTRA = {"privacy_tap": privacy_tap, "listen_ended": listen_ended, "key_exchange": key_exchange, "host_id_first_wins": host_id_first_wins, "idle_jump": idle_jump, "soak": soak}
