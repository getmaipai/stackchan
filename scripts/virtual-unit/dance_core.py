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


def extract_header() -> Path:
    """The header as the patch adds it (the lines that start with +, between its diff line and the next one)."""
    text = PATCH.read_text()
    m = re.search(r"^\+\+\+ b/firmware/main/hal/" + re.escape(HEADER) + r"\n@@[^\n]*\n(.*?)(?=^diff --git )", text, re.S | re.M)
    if not m:
        raise RuntimeError(f"{HEADER} is not in {PATCH.name}: the patch changed; update scripts/virtual-unit/dance_core.py")
    body = "\n".join(line[1:] for line in m.group(1).splitlines() if line.startswith("+")) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / HEADER
    if not path.exists() or path.read_text() != body:
        path.write_text(body)
    return path


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
    _LIB = L
    return L
