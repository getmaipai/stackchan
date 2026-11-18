"""Builds and loads the real dance ladder core for the virtual unit (firmware patch MD01): the header is cut out of the patch file, compiled with a small C interface
(dance/ladder_sim.c) into a shared library under .runs/vu-dance, and loaded with ctypes. Nothing here copies the rule. Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import ctypes
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "firmware" / "patches" / "MD01-music-dance-ladder-and-beat-dance.patch"
OUT = ROOT / ".runs" / "vu-dance"
HEADER = "maipai_dance_ladder_core.h"


def _section(patch_text: str, path: str) -> str | None:
    """The part of a patch that changes one file (from its diff line to the next diff line)."""
    m = re.search(r"^(diff --git a/" + re.escape(path) + r" b/.*?)(?=^diff --git |\Z)", patch_text, re.S | re.M)
    return m.group(1) if m else None


def extract_header() -> Path:
    """The header as the series leaves it: the file MD01 adds (the lines that start with +), then every later patch of ORDER that changes it (SF51 adds the synthetic beat and the show),
    applied in order with `patch`. Nothing is copied by hand and no firmware tree is needed."""
    order = [l.strip() for l in (ROOT / "firmware" / "patches" / "ORDER").read_text().splitlines() if l.strip() and not l.startswith("#")]
    path = "firmware/main/hal/" + HEADER
    OUT.mkdir(parents=True, exist_ok=True)
    work = OUT / "series"
    work.mkdir(exist_ok=True)
    target = work / HEADER
    first = _section(PATCH.read_text(), path)
    if first is None:
        raise RuntimeError(f"{HEADER} is not in {PATCH.name}: the patch changed; update scripts/virtual-unit/dance_core.py")
    body = "\n".join(line[1:] for line in first.split("@@", 2)[2].split("\n", 1)[1].splitlines() if line.startswith("+")) + "\n"
    target.write_text(body)
    seen = False
    for name in order:
        if name == PATCH.name:
            seen = True
            continue
        if not seen:
            continue
        text = (ROOT / "firmware" / "patches" / name).read_text(errors="ignore")
        sec = _section(text, path)
        if sec is None:
            continue
        diff = sec.replace(f"a/{path}", f"a/{HEADER}").replace(f"b/{path}", f"b/{HEADER}")
        done = subprocess.run(["patch", "-p1", "-s", "-d", str(work)], input=diff.encode(), capture_output=True)
        if done.returncode != 0:
            raise RuntimeError(f"{name} does not apply to {HEADER}: {done.stdout.decode()[-200:]}")
    final = OUT / HEADER
    if not final.exists() or final.read_text() != target.read_text():
        final.write_text(target.read_text())
    return final


_LIB = None


def lib() -> ctypes.CDLL:
    global _LIB
    if _LIB is not None:
        return _LIB
    extract_header()
    src = Path(__file__).resolve().parent / "dance" / "ladder_sim.c"
    so = OUT / "ladder_sim.dylib"
    if not so.exists() or so.stat().st_mtime < max(src.stat().st_mtime, (OUT / HEADER).stat().st_mtime):
        subprocess.run(["cc", "-O1", "-std=c99", "-shared", "-fPIC", "-Wall", "-I", str(OUT), str(src), "-o", str(so)], check=True)
    L = ctypes.CDLL(str(so))
    L.sim_new.restype = ctypes.c_void_p
    for name in ("sim_start", "sim_set_max"):
        getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32] if name == "sim_start" else [ctypes.c_void_p, ctypes.c_int]
    L.sim_stage.argtypes = L.sim_down.argtypes = [ctypes.c_void_p]
    L.sim_tick.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    L.sim_effective.argtypes = [ctypes.c_int, ctypes.c_uint32]
    L.sim_dwell.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
    L.sim_dwell.restype = ctypes.c_uint32
    L.sim_budget_reset.argtypes = [ctypes.c_void_p]
    L.sim_budget_take.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    L.sim_swell.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    L.sim_pose.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint32, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    L.sim_ring.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
    L.sim_consts.argtypes = [ctypes.c_int]
    L.synth_new.restype = ctypes.c_void_p
    L.synth_start.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32]
    L.synth_period.argtypes = [ctypes.c_void_p]
    L.synth_period.restype = ctypes.c_uint32
    L.sim_synth_tick.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
    L.synth_bpm_for.argtypes = [ctypes.c_char_p]
    L.show_for_step.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    L.synth_face_next.argtypes = [ctypes.c_void_p, ctypes.c_int]
    L.face_name.argtypes = [ctypes.c_int]
    L.face_name.restype = ctypes.c_char_p
    L.ring_breath.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int]
    L.ring_chase.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint32, ctypes.c_int, ctypes.c_int]
    _LIB = L
    return L
