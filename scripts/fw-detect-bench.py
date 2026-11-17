#!/usr/bin/env python3
"""Measurement script for the on-unit face detector experiment (firmware patches FD01 to FD04, bench image only).

  fw-detect-bench.py preflight                 tool list, detector status, memory now (is the image the right one, is vision on)
  fw-detect-bench.py format                    3 frames per model: the camera's pixel format, the window, the conversion cost
  fw-detect-bench.py timing [--frames 200]     time per frame (p50 and p99) for each model and window, back to back
  fw-detect-bench.py distance [--model pico224] [--light normal] [--runs 20]
                                               prompts for 0.5, 1, 1.5, 2 and 3 m; the hit rate and score at each
  fw-detect-bench.py order                     the same frames with rgb and with bgr order (a wrong channel order halves the hit rate)
  fw-detect-bench.py memory                    load, run, free, load again: internal free and block at each step against the admission floor
  fw-detect-bench.py soak [--minutes 1440] [--hz 3] [--model pico224]
                                               3 Hz detection for hours; counts resets (the counters restart), failures, the worst times
  fw-detect-bench.py track [--seconds 120]     arms the tracker, polls self.look.status, always disarms; moves a minute and the end reasons
  fw-detect-bench.py report                    the go or no-go numbers of docs/design/face-detect-esp-dl-2026-11-17.md section 9 from the results file

Every measurement is one JSON line in the results file (--out, default fw-detect-bench.jsonl in MAIPAI_SERIAL_TMP or the temp folder), so
a stopped run loses nothing and `report` can be run at any time. Add --yes to skip the "press Return" prompts (a person must still stand
at the marks). The script never opens the serial port: it talks to `fw-serial.py serve`, which holds the port (start it once, in the
background, before the unit window; opening the port resets the unit). The unit needs the bench image built with
sdkconfig.fdetect.defaults; a plain image answers "unknown tool".

Intent: the plan's go or no-go (section 9) needs numbers only the unit can give; this asks for them the same way every time.
Placement: Mac that holds the cable (development only). Upstream: none (ours).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DISTANCES_M = (0.5, 1.0, 1.5, 2.0, 3.0)
# The go rule (section 9 of the plan): the hit rate of Pico 224 on the 160 by 120 crop, normal light, real faces.
GO_HIT_PCT = {1.0: 90.0, 1.5: 80.0, 2.0: 60.0}
GO_INFER_P50_MS = 250
GO_CYCLE_HZ = 3.0
ADMIT_FREE = 40000
ADMIT_BLOCK = 24000
LOW_WATER_FLOOR = 30000
NOGO_HIT_PCT_AT_1_5 = 60.0
FALSE_POSITIVES_PER_1000 = 1.0

MODELS = (("pico224", "center"), ("pico224", "full"), ("msrmnp", "full"), ("msrmnp", "center"))


def _load_serial():
    spec = importlib.util.spec_from_file_location("fw_serial", HERE / "fw-serial.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["fw_serial"] = module
    spec.loader.exec_module(module)
    return module


class Bench:
    def __init__(self, ask, out: Path, yes: bool, say=print, ask_user=input, clock=time.time, sleep=time.sleep):
        self.ask = ask  # ask(name, args, wait) -> (reply dict, snaps)
        self.out = out
        self.yes = yes
        self.say = say
        self.ask_user = ask_user
        self.clock = clock
        self.sleep = sleep

    # -- plumbing ----------------------------------------------------------------------------------------------------
    def tool(self, name: str, args: dict | None = None, wait: float = 60.0) -> dict:
        reply, _ = self.ask(name, args or {}, wait)
        return reply

    def record(self, kind: str, **fields) -> dict:
        row = {"t": round(self.clock(), 1), "kind": kind, **fields}
        self.out.parent.mkdir(parents=True, exist_ok=True)
        with self.out.open("a") as f:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")
        return row

    def prompt(self, text: str) -> None:
        if self.yes:
            self.say(text)
            return
        self.ask_user(text + "  [press Return] ")

    def detect(self, model: str, frames: int, crop: str = "", order: str = "rgb", hz: int = 0, force: bool = False) -> dict:
        """One detect_test, waiting for its end (the tool waits up to 25 s; a longer one is read back from detect_status)."""
        args = {"model": model, "frames": frames, "crop": crop, "order": order, "hz": hz, "force": force, "wait_s": 25}
        reply = self.tool("self.look.detect_test", args, wait=45.0)
        deadline = self.clock() + max(120.0, frames * 1.2)
        while reply.get("ok") and not reply.get("done") and self.clock() < deadline:
            self.sleep(3.0)
            reply = self.tool("self.look.detect_status", {"detail": True}, wait=30.0)
        return reply

    @staticmethod
    def line(r: dict) -> str:
        if not r.get("ok"):
            return f"refused: {r.get('error', r)}"
        ms = r.get("ms", {})
        mem = r.get("mem", {})
        return (
            f"{r.get('model')}/{r.get('crop')} {r.get('frames_done')} frames, faces in {r.get('frames_with_face')} "
            f"(score best {r.get('score_best_pct')}, avg {r.get('score_avg_pct')}); infer p50/p99 {ms.get('infer')}, total {ms.get('total')}, "
            f"conv {ms.get('conv')}, grab {ms.get('grab')}, cycle {ms.get('cycle')}; internal free/block during {mem.get('during_min', [])[:2]}, "
            f"fmt {r.get('fmt')}"
        )

    # -- the steps ---------------------------------------------------------------------------------------------------
    def preflight(self) -> int:
        st = self.tool("self.look.detect_status", {})
        look = self.tool("self.look.status", {})
        self.record("preflight", detect=st, look=look)
        if not st.get("ok"):
            self.say(f"not the detector image: {st}")
            return 1
        self.say(f"detector status: {json.dumps(st)}")
        self.say(f"look status: owner {look.get('owner')}, setting {look.get('setting')}, state {look.get('state')}, fov {look.get('fov_deg')}, x_sign {look.get('x_sign')}")
        if look.get("owner") == "host":
            self.say("a host holds the look lease: release it (self.look.release) so the unit's own camera work is not refused")
        return 0

    def format_check(self) -> int:
        for model, crop in MODELS[:3]:
            r = self.detect(model, 3, crop)
            self.record("format", model=model, crop=crop, reply=r)
            self.say(self.line(r))
            if r.get("ok"):
                self.say(f"  pixel format {r.get('fmt')}, frame {r.get('frame')}, window {r.get('window')}, conversion [p50,p99] {r['ms']['conv']} ms, first frame {r['ms']['first']} ms")
        return 0

    def timing(self, frames: int) -> int:
        for model, crop in MODELS:
            r = self.detect(model, frames, crop)
            self.record("timing", model=model, crop=crop, frames=frames, reply=r)
            self.say(self.line(r))
        return 0

    def distance(self, model: str, light: str, runs: int, crop: str, order: str) -> int:
        self.say(f"model {model}, crop {crop or 'default'}, light {light}, {runs} frames at each mark; a real face, frontal, looking at the unit")
        for d in DISTANCES_M:
            self.prompt(f"Stand with your face {d:g} m from the unit")
            r = self.detect(model, runs, crop, order)
            ok = r.get("ok")
            hit = (100.0 * r["frames_with_face"] / max(1, r["frames_done"])) if ok else None
            self.record("distance", model=model, crop=crop, light=light, order=order, meters=d, runs=runs, hit_pct=hit, reply=r)
            self.say(f"  {d:g} m: " + (f"hit {hit:.0f} percent, score avg {r['score_avg_pct']}, infer p50 {r['ms']['infer'][0]} ms" if ok else self.line(r)))
        return 0

    def order(self, frames: int = 20) -> int:
        self.prompt("Face the unit about 1.5 m away and hold still for both runs")
        rows = {}
        for order in ("rgb", "bgr"):
            r = self.detect("pico224", frames, "center", order)
            rows[order] = r
            self.record("order", order=order, reply=r)
            self.say(f"  {order}: " + self.line(r))
        if all(r.get("ok") for r in rows.values()):
            a, b = rows["rgb"]["frames_with_face"], rows["bgr"]["frames_with_face"]
            self.say(f"  rgb {a} of {frames}, bgr {b} of {frames}: " + ("rgb is the right order" if a >= b else "bgr hits more: the camera delivers a different order, check the conversion"))
        return 0

    def memory(self) -> int:
        failures = 0
        steps = []
        r0 = self.detect("msrmnp", 5, "full")
        steps.append(("after first run (model loaded)", r0))
        self.say("waiting 14 s for the idle unload")
        self.sleep(14.0)
        st = self.tool("self.look.detect_status", {})
        self.record("memory_unload", status=st)
        self.say(f"  after the wait: loaded {st.get('loaded')}")
        r1 = self.detect("msrmnp", 5, "full")
        steps.append(("after unload and a second load", r1))
        r2 = self.detect("pico224", 5, "center")
        steps.append(("pico224 after msrmnp", r2))
        for name, r in steps:
            self.record("memory", step=name, reply=r)
            if not r.get("ok"):
                self.say(f"  {name}: {r.get('error')}")
                failures += 1
                continue
            mem = r["mem"]
            self.say(f"  {name}: before {mem['before']}, during min {mem['during_min']}, after {mem['after']}, low water {mem['int_low_water']}")
        self.say(f"  admission floor: free {ADMIT_FREE}, block {ADMIT_BLOCK}; low-water floor {LOW_WATER_FLOOR}")
        return 1 if failures else 0

    def soak(self, minutes: float, hz: int, model: str) -> int:
        end = self.clock() + minutes * 60.0
        frames_total = faces_total = resets = failures = 0
        runs_seen = 0
        worst_infer = worst_total = 0
        low_free = 1 << 30
        hour = self.clock()
        self.say(f"soak {minutes:g} min at {hz} Hz, model {model}; Ctrl-C stops and keeps what was written")
        try:
            while self.clock() < end:
                try:
                    r = self.detect(model, 100, "", "rgb", hz)
                except (TimeoutError, OSError) as error:
                    failures += 1
                    self.record("soak_fail", error=str(error))
                    self.say(f"  no answer: {error} (the unit may have reset)")
                    self.sleep(20.0)
                    continue
                if not r.get("ok"):
                    failures += 1
                    self.record("soak_fail", reply=r)
                    self.sleep(5.0)
                    continue
                st = self.tool("self.look.detect_status", {})
                runs = st.get("runs", 0)
                if runs < runs_seen:  # the counters restarted: the unit reset
                    resets += 1
                    self.record("soak_reset", runs_before=runs_seen, runs_now=runs)
                    self.say(f"  RESET seen: the run counter fell from {runs_seen} to {runs}; read the coredump (scripts/fw-coredump.py)")
                runs_seen = runs
                frames_total += r["frames_done"]
                faces_total += r["frames_with_face"]
                worst_infer = max(worst_infer, r["ms"]["infer"][1])
                worst_total = max(worst_total, r["ms"]["total"][1])
                low_free = min(low_free, r["mem"]["int_low_water"])
                self.record("soak", reply=r)
                if self.clock() - hour >= 3600:
                    hour = self.clock()
                    self.say(f"  hour: {frames_total} frames, {resets} resets, {failures} failures, worst infer {worst_infer} ms, internal low water {low_free}")
        except KeyboardInterrupt:
            self.say("stopped")
        self.record("soak_summary", frames=frames_total, faces=faces_total, resets=resets, failures=failures, worst_infer_ms=worst_infer, worst_total_ms=worst_total, internal_low_water=low_free, minutes=minutes, hz=hz, model=model)
        self.say(f"soak done: {frames_total} frames, {resets} resets, {failures} failures, worst infer {worst_infer} ms, worst total {worst_total} ms, internal low water {low_free}")
        return 1 if resets or failures else 0

    def track(self, seconds: float) -> int:
        self.prompt("Stand 1 to 2 m from the unit; talk to it (say its wake word, then talk) and walk slowly left and right")
        armed = self.tool("self.look.detect_track", {"on": True})
        self.record("track_arm", reply=armed)
        self.say(f"armed: {armed}")
        t0 = self.clock()
        last = {}
        try:
            while self.clock() - t0 < seconds:
                self.sleep(2.0)
                last = self.tool("self.look.status", {})
                self.record("track_poll", state=last.get("fd_track"), moves=last.get("fd_moves"), moves_min=last.get("fd_moves_min"), stalls=last.get("fd_stalls"), end=last.get("fd_end"), face_age=last.get("fd_age_ms"), score=last.get("fd_score_pct"), cx=last.get("fd_cx"))
                self.say(f"  {last.get('fd_track')} moves {last.get('fd_moves')} (last minute {last.get('fd_moves_min')}), stalls {last.get('fd_stalls')}, end {last.get('fd_end')}, face {last.get('fd_score_pct')} percent at {last.get('fd_cx')}, age {last.get('fd_age_ms')} ms")
        finally:
            off = self.tool("self.look.detect_track", {"on": False})
            self.record("track_disarm", reply=off)
            self.say(f"disarmed: {off}")
        return 0

    # -- the verdict -------------------------------------------------------------------------------------------------
    def rows(self) -> list[dict]:
        if not self.out.exists():
            return []
        return [json.loads(x) for x in self.out.read_text().splitlines() if x.strip()]

    def report(self) -> int:
        rows = self.rows()
        verdicts: list[tuple[str, str, str]] = []

        def add(name: str, ok: bool | None, detail: str) -> None:
            verdicts.append((name, "PASS" if ok else ("FAIL" if ok is False else "NOT MEASURED"), detail))

        dist = [r for r in rows if r["kind"] == "distance" and r.get("model") == "pico224" and r.get("light", "normal") == "normal" and r.get("hit_pct") is not None]
        latest: dict[float, float] = {}
        for r in dist:
            latest[r["meters"]] = r["hit_pct"]
        for m, need in GO_HIT_PCT.items():
            got = latest.get(m)
            add(f"Pico 224 crop hits {need:.0f} percent at {m:g} m", None if got is None else got >= need, "no run" if got is None else f"{got:.0f} percent")
        timing = [r for r in rows if r["kind"] == "timing" and r.get("model") == "pico224" and r.get("crop") == "center" and r["reply"].get("ok")]
        if timing:
            p50 = timing[-1]["reply"]["ms"]["infer"][0]
            add(f"model run at most {GO_INFER_P50_MS} ms median", p50 <= GO_INFER_P50_MS, f"p50 {p50} ms, p99 {timing[-1]['reply']['ms']['infer'][1]} ms")
        else:
            add(f"model run at most {GO_INFER_P50_MS} ms median", None, "no timing run")
        mem = [r for r in rows if r["kind"] == "memory" and r["reply"].get("ok")]
        if mem:
            worst_free = min(r["reply"]["mem"]["before"][0] for r in mem)
            worst_block = min(r["reply"]["mem"]["before"][1] for r in mem)
            low = min(r["reply"]["mem"]["int_low_water"] for r in mem)
            add(f"admitted after an unload cycle (free at least {ADMIT_FREE}, block at least {ADMIT_BLOCK})", worst_free >= ADMIT_FREE and worst_block >= ADMIT_BLOCK, f"before-load free {worst_free}, block {worst_block}")
            add(f"no internal low-water mark below {LOW_WATER_FLOOR}", low >= LOW_WATER_FLOOR, f"low water {low}")
        else:
            add("admitted after an unload cycle", None, "no memory run")
        soak = [r for r in rows if r["kind"] == "soak_summary"]
        if soak:
            s = soak[-1]
            add("zero panics in the soak", s["resets"] == 0 and s["failures"] == 0, f"{s['minutes']:g} min at {s['hz']} Hz, {s['frames']} frames, {s['resets']} resets, {s['failures']} failures")
        else:
            add("zero panics in the soak (24 hours at 240 MHz; if it panics, again at 160 MHz)", None, "no soak run")
        track = [r for r in rows if r["kind"] == "track_poll" and r.get("moves_min") is not None]
        if track:
            worst = max(r["moves_min"] for r in track)
            add("the servo moves at most 20 times a minute", worst <= 20, f"worst minute {worst}")
        else:
            add("the servo moves at most 20 times a minute", None, "no track run")
        add("false positives under 1 per 1000 frames (poster, screen, mirror, empty room, plant)", None, "measure with `distance` pointed at the case and read faces in an empty scene by hand; this script does not score it")
        add("no task watchdog and no late loops beyond today's", None, "read the cable log and the memory line during the soak")
        width = max(len(v[0]) for v in verdicts)
        for name, verdict, detail in verdicts:
            self.say(f"{verdict:12} {name.ljust(width)}  {detail}")
        at15 = latest.get(1.5)
        if at15 is not None and at15 < NOGO_HIT_PCT_AT_1_5:
            self.say(f"NO-GO: hits at 1.5 m are {at15:.0f} percent, under {NOGO_HIT_PCT_AT_1_5:.0f}: stay on the blob path and let Home follow faces")
        bad = [v for v in verdicts if v[1] == "FAIL"]
        if bad:
            self.say(f"{len(bad)} criterion failed: not a go")
            return 1
        missing = [v for v in verdicts if v[1] == "NOT MEASURED"]
        self.say(f"{len(missing)} criteria not measured yet" if missing else "every criterion measured and passed: go")
        return 0


def main(argv: list[str] | None = None, ask=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("step", choices=["preflight", "format", "timing", "distance", "order", "memory", "soak", "track", "report"])
    p.add_argument("--out", default=None)
    p.add_argument("--yes", action="store_true")
    p.add_argument("--frames", type=int, default=200)
    p.add_argument("--model", default="pico224", choices=["pico224", "msrmnp"])
    p.add_argument("--crop", default="", choices=["", "full", "center", "follow"])
    p.add_argument("--order", default="rgb", choices=["rgb", "bgr"])
    p.add_argument("--light", default="normal", choices=["normal", "dim"])
    p.add_argument("--runs", type=int, default=20)
    p.add_argument("--minutes", type=float, default=1440.0)
    p.add_argument("--seconds", type=float, default=120.0)
    p.add_argument("--hz", type=int, default=3, choices=[2, 3, 4, 5])
    a = p.parse_args(argv)
    out = Path(a.out or os.path.join(os.environ.get("MAIPAI_SERIAL_TMP") or tempfile.gettempdir(), "fw-detect-bench.jsonl"))
    if ask is None and a.step != "report":
        ask = _load_serial().ask
    b = Bench(ask, out, a.yes)
    if a.step == "preflight":
        return b.preflight()
    if a.step == "format":
        return b.format_check()
    if a.step == "timing":
        return b.timing(a.frames)
    if a.step == "distance":
        return b.distance(a.model, a.light, a.runs, a.crop, a.order)
    if a.step == "order":
        return b.order()
    if a.step == "memory":
        return b.memory()
    if a.step == "soak":
        return b.soak(a.minutes, a.hz, a.model)
    if a.step == "track":
        return b.track(a.seconds)
    return b.report()


if __name__ == "__main__":
    sys.exit(main())
