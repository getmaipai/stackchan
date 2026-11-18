"""The adapter layer between the virtual unit's Python (copied unchanged into the browser) and the WebAssembly modules. Nothing in vunit.py, dance_core.py, host_away.py,
view.py or scenarios.py is edited: this module replaces the three things they reach outside Python for, from the outside:
  1. subprocess.Popen / subprocess.run of the native renderer programs (render, lock_render, cover_render): command lines go to a WebAssembly renderer instance (bridge.js);
  2. ctypes.CDLL of the C cores (dance ladder, host reconnect): calls go to cores.wasm through the same bridge; ctypes arrays and byref values are copied in and out;
  3. the compile steps those modules run before loading a library (cc, patch): skipped, because the cores are already built.
A renderer instance is taken from a pool the page filled before (a fresh program state per unit, as a fresh process was). Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import collections
import ctypes
import os
import re
import subprocess
import sys
from pathlib import Path

import js
from pyodide.ffi import to_js

ROOT = Path("/vu")
BRIDGE = None   # set by install()


def _bridge():
    if BRIDGE is None:
        raise RuntimeError("the browser bridge is not installed: run wasm_shim.install(bridge) first")
    return BRIDGE


# ---- 1. the renderer programs ----------------------------------------------------------------------------------------------------------------------

def _kind(program: str) -> str:
    name = Path(program).name
    if name == "render":
        return "screens"
    if name in ("lock_render", "cover_render"):
        return name.split("_")[0]
    raise RuntimeError(f"{name} is not a renderer this page has: it runs only render, lock_render and cover_render (WebAssembly). Use the native playground for other programs.")


class _Pipe:
    def __init__(self, proc: "FakeProc") -> None:
        self.proc = proc

    def write(self, text: str) -> int:
        for line in text.split("\n"):
            if line.strip():
                self.proc.command(line)
        return len(text)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    def readline(self) -> str:
        return self.proc.out.popleft() + "\n" if self.proc.out else ""


class FakeProc:
    """subprocess.Popen for a renderer program: stdin takes command lines, stdout answers the lines the program prints, a `snap FILE` leaves the PNG in this Python's file system."""

    def __init__(self, args, **_kw) -> None:
        self.kind = _kind(str(args[0]))
        self.id = _bridge().take(self.kind)
        self.out: collections.deque[str] = collections.deque()
        self.stdin = self.stdout = _Pipe(self)

    def command(self, line: str) -> None:
        printed = _bridge().cmd(self.id, line)
        if printed:
            self.out.extend(printed.split("\n"))
        m = re.search(r"(\S+\.png)\s*$", line)
        if m:   # a command that wrote a PNG to a path (snap, lock, pad): bring the file over to this Python's file system
            path = m.group(1)
            data = _bridge().file(self.id, path).to_py()
            Path(path).write_bytes(bytes(data))
            _bridge().drop(self.id, path)

    def wait(self, timeout=None) -> int:
        _bridge().release(self.id)
        return 0


def _run(args, input=None, text=False, capture_output=False, check=False, timeout=None, **_kw):
    prog = str(args[0])
    try:
        kind = _kind(prog)
    except RuntimeError as err:
        raise RuntimeError(f"{err}") from None
    proc = FakeProc(args)
    for line in (input or "").split("\n"):
        if line.strip():
            proc.command(line)
    stdout = "\n".join(proc.out) + ("\n" if proc.out else "")
    proc.wait()
    return subprocess.CompletedProcess(args, 0, stdout, "")


# ---- 2. the C cores ----------------------------------------------------------------------------------------------------------------------------

def _ret_kind(restype) -> str:
    if restype is None:
        return "v"
    if restype is ctypes.c_char_p:
        return "s"
    if restype in (ctypes.c_uint32, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint64):
        return "u"
    if restype in (ctypes.c_float, ctypes.c_double):
        return "f"
    return "i"


class _Fn:
    def __init__(self, name: str) -> None:
        self.name, self.argtypes, self.restype = name, None, ctypes.c_int

    def __call__(self, *args):
        b = _bridge()
        flat, back = [], []
        for a in args:
            if isinstance(a, ctypes.Array) or type(a).__name__ == "CArgObject" or isinstance(a, (ctypes._SimpleCData, ctypes.Structure)):
                obj = a._obj if type(a).__name__ == "CArgObject" else a
                n = ctypes.sizeof(obj)
                p = b.coreMalloc(n)
                b.coreWrite(p, to_js(bytes(obj)))
                flat.append(p)
                back.append((obj, p, n))
            elif isinstance(a, bytes):
                flat.append(a.decode())
            elif isinstance(a, float):
                flat.append(a)
            else:
                flat.append(int(a) if not isinstance(a, str) else a)
        r = b.coreCall(self.name, _ret_kind(self.restype), to_js(flat))
        for obj, p, n in back:
            ctypes.memmove(ctypes.addressof(obj), bytes(b.coreRead(p, n).to_py()), n)
            b.coreFree(p)
        kind = _ret_kind(self.restype)
        if kind == "s":
            return r.encode() if r is not None else None
        if kind == "v":
            return None
        return r


class WasmLib:
    """What ctypes.CDLL returns for a core library here: attribute access gives a callable with settable argtypes and restype, as a ctypes function has."""

    def __init__(self, path: str) -> None:
        self._fns: dict[str, _Fn] = {}

    def __getattr__(self, name: str) -> _Fn:
        if name.startswith("__"):
            raise AttributeError(name)
        return self._fns.setdefault(name, _Fn(name))


def install(bridge) -> None:
    """Replace the three outside reaches. Call once, after the Python files are unpacked and before the first import of vunit."""
    global BRIDGE
    BRIDGE = bridge
    subprocess.Popen = FakeProc
    subprocess.run = _run
    ctypes.CDLL = WasmLib
    # the library files dance_core.py and host_away.py check for before they compile: present and newer than their sources, so nothing is compiled
    out = ROOT / ".runs" / "vu-dance"
    out.mkdir(parents=True, exist_ok=True)
    (out / "maipai_dance_ladder_core.h").write_text("")
    (out / "maipai_reconnect_core.h").write_text("")
    for stub in (ROOT / ".runs" / "vu-screens" / "render", ROOT / ".runs" / "vu-build" / "render", ROOT / ".runs" / "vu-screens" / "cover" / "cover_render", ROOT / ".runs" / "vu-screens" / "lock" / "lock_render"):
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text("renderer: WebAssembly module of the same name (scripts/virtual-unit/wasm/site-build.sh)\n")
    sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
    sys.path.insert(0, str(ROOT / "host"))
    import dance_core
    import host_away

    out_so = out / "ladder_sim.dylib"
    out_so.write_text("")
    os.utime(out_so, None)
    dance_core.extract_header = lambda: None   # the header is compiled into cores.wasm; the patch files are not shipped

    def _away_lib():
        if host_away._LIB is None:
            L = WasmLib("reconnect_sim")
            for name, args, res in (("rc_cap", [ctypes.c_uint32], ctypes.c_uint32), ("rc_grow", [ctypes.c_uint32] * 2, ctypes.c_uint32), ("rc_wait", [ctypes.c_uint32] * 3, ctypes.c_uint32), ("rc_notice_due", [ctypes.c_uint32] * 2, ctypes.c_int)):
                f = getattr(L, name)
                f.argtypes, f.restype = args, res
            host_away._LIB = L
        return host_away._LIB

    host_away.lib = _away_lib
