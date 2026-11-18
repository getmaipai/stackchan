"""Parity cases: the same Python runs in two places, natively (the real ctypes libraries, the native renderer programs, the real subprocess) and in the browser (Pyodide, WebAssembly
renderers and cores, through wasm_shim.py). Each case returns a small JSON-able result; parity is "the browser's result equals the native one", and for frames, equals the committed golden.
Groups: tool:NAME (every tool of schema/tools.json called on a fresh unit), frame:NAME (every golden-frame scenario of scenarios.py, lock keypad and covers included), dance:* (the music
dance ladder session and the hand-chosen dance), quiet:* (the quiet schedule: the tool's rule against the unit's C core), memory:walk (the memory model), away:* (reconnect core through
host_away), core:* (the C cores called directly: lock, limiter, listen guard, update trial, signed header, remote rules, link quiet, touch).
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import ctypes
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = Path("/vu") if str(HERE).startswith("/vu/") else HERE.parents[5]
VU = ROOT / "scripts" / "virtual-unit"
for p in (str(VU), str(ROOT / "host")):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios as S  # noqa: E402
import vunit  # noqa: E402

KIND = {"i": ctypes.c_int, "u": ctypes.c_uint32, "f": ctypes.c_float, "s": ctypes.c_char_p, "o": ctypes.c_uint32}
CORE = {"lib": None, "sigs": None}
HAND = {   # the hand-written wrappers (cores_api.c, cores_all.c): argtypes and result
    "lock_reset": ([], None), "lock_set": ([ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int), "lock_lock_now": ([ctypes.c_uint32], ctypes.c_int), "lock_touch": ([ctypes.c_uint32], None),
    "lock_key": ([ctypes.c_int, ctypes.c_uint32], ctypes.c_int), "lock_keypad_tick": ([ctypes.c_uint32], ctypes.c_int), "lock_is_locked": ([], ctypes.c_int), "lock_entered": ([], ctypes.c_int),
    "lock_wrong_shown": ([], ctypes.c_int), "lock_status": ([], ctypes.c_char_p), "lock_reply": ([ctypes.c_int], ctypes.c_char_p),
    "limit_reset": ([], None), "limit_step": ([ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.c_int], None), "limit_state": ([], ctypes.c_char_p), "limit_scale": ([], ctypes.c_int),
    "limit_speed_cap": ([], ctypes.c_int), "limit_dance_max": ([], ctypes.c_int), "limit_angle": ([ctypes.c_int, ctypes.c_int], ctypes.c_int),
    "hdr_parse_hex": ([ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p], ctypes.c_int), "hdr_build": ([], ctypes.c_uint32), "hdr_image_len": ([], ctypes.c_uint32), "hdr_reason": ([ctypes.c_int], ctypes.c_char_p),
}


def configure(lib, sigs: dict) -> None:
    """Give the core library its argtypes and results (the generated table plus the hand-written functions), the same on both sides."""
    for name, sig in sigs["functions"].items():
        f = getattr(lib, "c_" + name)
        f.argtypes = [KIND[a] for a in sig["args"]]
        f.restype = None if sig["ret"] == "v" else KIND[sig["ret"]]
    for name, (args, res) in HAND.items():
        f = getattr(lib, name)
        f.argtypes, f.restype = args, res
    for name in ("c_out",):
        getattr(lib, name).argtypes = [ctypes.c_int]
        getattr(lib, name).restype = ctypes.c_uint32
    CORE["lib"], CORE["sigs"] = lib, sigs


def C(name, *args):
    """Call a generated core function by its header name; strings go in as text."""
    fn = getattr(CORE["lib"], "c_" + name)
    out = fn(*[a.encode() if isinstance(a, str) else a for a in args])
    return out.decode() if isinstance(out, bytes) else (float(out) if CORE["sigs"]["functions"][name]["ret"] == "f" else out)


def H(name, *args):
    out = getattr(CORE["lib"], name)(*[a.encode() if isinstance(a, str) else a for a in args])
    return out.decode() if isinstance(out, bytes) else out


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# ---- frames ------------------------------------------------------------------------------------------------------------------------------------------

def frame_names() -> list[str]:
    return list(S.SCENARIOS) + list(S.SCREENS) + list(S.LOCK_SCENARIOS) + list(S.COVER_SCENARIOS)


def run_frame(name: str) -> dict:
    if name in S.LOCK_SCENARIOS or name in S.COVER_SCENARIOS:
        png = S.run_lock(name)
    else:
        sc = name in S.SCREENS
        with vunit.VirtualUnit(profile="screens") as u:
            S.run(u, S.SCREENS[name] if sc else S.SCENARIOS[name])
            png = u.snapshot()
    return {"sha": hashlib.sha256(S.png_pixels(png)).hexdigest()}


def frame_needs(name: str) -> str:
    return "lock" if name in S.LOCK_SCENARIOS else ("cover" if name in S.COVER_SCENARIOS else "screens")


# ---- tools -------------------------------------------------------------------------------------------------------------------------------------------

def tool_names() -> list[str]:
    return sorted(json.loads((ROOT / "schema" / "tools.json").read_text())["tools"])


def run_tool(name: str) -> dict:
    with vunit.VirtualUnit(profile="screens") as u:
        out = u.call(name, {})
        out = {k: v for k, v in out.items() if k != "png_base64"}
        return {"simulated": name in vunit.SIMULATED, "gap": "not simulated" in str(out.get("text", "")), "result": out}


# ---- dance -------------------------------------------------------------------------------------------------------------------------------------------

DANCES = {"dance:loud_peak-home": ("music", "loud_peak", "home", 40), "dance:fast-unit": ("music", "fast", "unit", 30), "dance:quiet-unit": ("music", "quiet", "unit", 30),
          "dance:session-happy": ("hand", "happy", "", 20)}


def run_dance(case: str) -> dict:
    kind, a, b, seconds = DANCES[case]
    with vunit.VirtualUnit(profile="screens") as u:
        if kind == "music":
            u.call("sim.music", {"action": "start", "song": a, "mode": b})
        else:
            u.call("self.robot.dance", {"name": a})
        samples, stages = [], []
        for i in range(seconds * 10):
            u.advance(100)
            d = u.dance
            samples.append((u.now_ms, d.stage, [list(x) for x in u.leds], list(d.overlays), d.notes, u.head()))
            if i % 5 == 0:
                stages.append(d.stage)
        st = u.dance.status()
        return {"stages": stages, "samples_sha": _sha(samples), "status": st}


# ---- quiet schedule ----------------------------------------------------------------------------------------------------------------------------------

def run_quiet() -> dict:
    sys.path.insert(0, str(VU))
    from tools import audio

    rows, py, core, odd = [], [], [], []
    for frm, to in ((1320, 420), (0, 360), (480, 1200), (1380, 60), (600, 601), (0, 1439)):
        for minute in range(0, 1440, 15):
            s = {"policy": {"dark": False, "quiet_from": frm, "quiet_to": to}, "minute": minute}
            a = bool(audio._quiet(s))
            b = bool(C("ms_in_window", frm, to, minute))
            py.append(a)
            core.append(b)
            if a != b:
                odd.append([frm, to, minute, a, b])
    # the default window (22:00 to 07:00) when none is set: the tool's rule against the core's default policy is not a plain window call, so only the tool's answer is recorded
    default = [bool(audio._quiet({"policy": {"dark": False, "quiet_from": -1, "quiet_to": -1}, "minute": m})) for m in range(0, 1440, 60)]
    return {"python_sha": _sha(py), "core_sha": _sha(core), "agree": not odd, "disagree": odd[:5], "default_window": default}


# ---- memory model ------------------------------------------------------------------------------------------------------------------------------------

def run_memory() -> dict:
    import memory_walk

    with vunit.VirtualUnit(profile="screens") as u:
        return json.loads(json.dumps(memory_walk.walk(u), default=str))


# ---- reconnect through host_away, and the cores called directly ---------------------------------------------------------------------------------------

def run_away() -> dict:
    import host_away

    L = host_away.lib()
    grid = []
    for away in (0, 1000, 30000, 600000, 3_600_000):
        cap = L.rc_cap(away)
        d = 500
        row = [away, cap]
        for rnd in (0, 7, 99999):
            row.append(L.rc_wait(d, cap, rnd))
        row.append(L.rc_grow(d, cap))
        row.append(L.rc_notice_due(away, 0))
        grid.append(row)
    return {"grid": grid}


def run_core(case: str) -> dict:
    if case == "core:lock":
        H("lock_reset")
        out = [H("lock_set", "1234", ""), H("lock_reply", 0), H("lock_lock_now", 1000), H("lock_status")]
        H("lock_touch", 1100)
        t = 1400
        for key in "12349":
            t += 300
            out.append([key, H("lock_key", ord(key), t)])
        out += [H("lock_is_locked"), H("lock_entered"), H("lock_wrong_shown"), H("lock_status"), H("lock_keypad_tick", t + 5000)]
        for key in "1233":   # a wrong code, then the right one
            t += 300
            out.append([key, H("lock_key", ord(key), t)])
        out += [H("lock_status"), [C("mlk_code_valid", c) for c in ("1234", "12", "abcd", "123456", "")], [C("mlk_auto_ok", m) for m in (0, 1, 5, 30, 61)]]
        return {"trace": out}
    if case == "core:limiter":
        H("limit_reset")
        out, t = [], 1000
        for carried, usb, level in ((0, 0, 80), (0, 1, 80), (0, 0, 10), (1, 0, 80), (0, 0, 80), (0, 1, 5), (0, 0, 100)):
            t += 3000
            H("limit_step", t, carried, usb, level)
            H("limit_step", t + 2500, carried, usb, level)
            out.append([carried, usb, level, H("limit_state"), H("limit_scale"), H("limit_speed_cap"), H("limit_dance_max"), H("limit_angle", 90, 45)])
        C("mml_init")
        for tilt in ((0.0, 0.0, 1.0, 0.0), (0.7, 0.0, 0.7, 0.0), (0.0, 0.0, -1.0, 0.0), (1.0, 0.0, 0.0, 0.0)):
            t += 1000
            C("mml_orient_feed", t, *tilt)
            out.append([tilt, C("mml_orient", t + 3000), C("mml_state_name"), C("mml_band_name"), C("mml_stiffness", 1.0)])
        return {"trace": out}
    if case == "core:listen_guard":
        return {"grid": [[a, b, c, d, C("mlg_should_end", a, b, c, d)] for a in (0, 3, 10, 30, 90) for b in (0, 2, 5, 12) for c in (5, 10) for d in (20, 60)]}
    if case == "core:update_trial":
        out = []
        for host_up, camera_at, alive, life in ((1, 3, 1, 30), (0, 3, 1, 70), (0, -1, 1, 130), (1, 3, 0, 30)):
            CORE["lib"].c_zero_muc_trial_t()
            boot = C("muc_boot", 1, 0, 0)
            dirty = CORE["lib"].c_out(0)
            row, t = [host_up, camera_at, alive, life, boot, dirty], 0
            for t in range(0, life + 1, 5):
                st = C("muc_step", t, 1 if 0 <= camera_at <= t else 0, alive, host_up, 0)
                row.append([t, st, CORE["lib"].c_out(0)])
            out.append(row)
        return {"trace": out}
    if case == "core:update_header":
        hdr = b"MPUH1\0\0\0" + (7).to_bytes(4, "little") + (4096).to_bytes(4, "little") + bytes(range(32)) + b"stkchn\0\0"
        out = [[floor, board, H("hdr_parse_hex", hdr.hex(), floor, board), H("hdr_build"), H("hdr_image_len")] for floor, board in ((0, "stkchn"), (7, "stkchn"), (6, "stkchn"), (0, "other"), (0, ""))]
        out.append([H("hdr_parse_hex", hdr[:-1].hex(), 0, "stkchn"), H("hdr_parse_hex", (b"XXXXX" + hdr[5:]).hex(), 0, "stkchn")])
        out.append([H("hdr_reason", i) for i in range(10)])
        out.append([C("muh_floor", a, b) for a, b in ((0, 0), (5, 3), (3, 5), (-1, 4))])
        return {"trace": out}
    if case == "core:remote":
        CORE["lib"].c_zero_mr_t()
        C("mr_init")
        out, now = [], 1000
        C("mr_session", 1, "bench", now)
        C("mr_set_host", 77)
        out.append([C("mr_session_on", now + 1000), C("mr_kind_by_name", "find"), C("mr_kind_by_name", "wipe"), C("mr_kind_needs_host", 0), C("mr_kind_needs_host", 1)])
        for source, kind in (("remote", "find"), ("remote", "say"), ("local", "say"), ("remote", "nothing")):
            now += 500
            out.append([source, kind, C("mr_gate_call", source, kind, 0, now)])
        C("mr_session", 0, "", now + 100000)
        out.append(C("mr_session_on", now + 100000))
        return {"trace": out}
    if case == "core:link_quiet":
        C("mq_init")
        out = [C("mq_up")]
        C("mq_down", 1000)
        for t in (1100, 5000, 20000, 60000, 130000, 400000):
            out.append([t, C("mq_poll", t, 0), C("mq_up")])
        out.append([C("mq_poll", 500000, 1), C("mq_up")])
        return {"trace": out}
    if case == "core:sounds":
        out = [[C("ms_in_window", f, t, m) for m in (0, 359, 360, 419, 420, 1319, 1320, 1439)] for f, t in ((1320, 420), (0, 360), (480, 1200))]
        out.append([C("ms_reason_word", i) for i in range(6)])
        out.append([C("ms_sound_from_name", n) for n in ("popup", "success", "needs_you", "zzz")])
        out.append([C("mh_quiet_now", m, h) for m in (-1, 0, 720, 1380) for h in (0, 1)])
        out.append([C("mh_word", i) for i in range(5)])
        return {"trace": out}
    if case == "core:touch":
        CORE["lib"].c_zero_mtc_trace_t()
        out = []
        for x, y in ((10, 10), (160, 120), (300, 230), (160, 4)):
            C("mtc_begin", x, y, 0)
            C("mtc_move", x + 2, y + 1, 80)
            out.append([x, y, C("mtc_classify"), C("mtc_region_at", x, y), C("mtc_in_start_region"), C("mtc_is_still"), C("mtc_action_on_release")])
        out.append([C("mtc_toggle_ok", k, s) for k in range(4) for s in (0, 1)])
        return {"trace": out}
    raise KeyError(case)


CORE_CASES = ["core:lock", "core:limiter", "core:listen_guard", "core:update_trial", "core:update_header", "core:remote", "core:link_quiet", "core:sounds", "core:touch"]


def all_cases() -> list[str]:
    return (["frame:" + n for n in frame_names()] + ["tool:" + n for n in tool_names()] + list(DANCES) + ["quiet:schedule", "memory:walk", "away:reconnect"] + CORE_CASES)


def needs(case: str) -> str | None:
    """The renderer kind a case starts (a fresh one has to be ready first), or None."""
    if case.startswith("frame:"):
        return frame_needs(case[6:])
    if case.startswith(("tool:", "dance:", "memory:")):
        return "screens"
    return None


def run(case: str) -> str:
    """One case; the result as JSON text. An error is a result too (the text), so a gap shows as a difference, not as a crash."""
    try:
        if case.startswith("frame:"):
            out = run_frame(case[6:])
        elif case.startswith("tool:"):
            out = run_tool(case[5:])
        elif case.startswith("dance:"):
            out = run_dance(case)
        elif case == "quiet:schedule":
            out = run_quiet()
        elif case == "memory:walk":
            out = run_memory()
        elif case == "away:reconnect":
            out = run_away()
        else:
            out = run_core(case)
    except Exception as err:   # noqa: BLE001
        out = {"error": f"{type(err).__name__}: {err}"}
    return json.dumps(out, sort_keys=True, default=str)
