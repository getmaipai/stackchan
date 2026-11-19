"""Shared fixtures: the deterministic suite runs against the fake always, and
against the live simulator only when it is reachable and asked for.
"""

from __future__ import annotations

import socket

import pytest

from maipai_body.bodies.reachy_mini.client import ReachyMiniClient
from maipai_body.bodies.reachy_mini.fake import FakeReachyMiniClient
from maipai_body.bodies.reachy_mini.profile import REACHY_MINI_PROFILE


@pytest.fixture(autouse=True)
def _end_service_threads():
    """A test that starts host service threads and never sets their stop event must not leave them running."""
    yield
    from maipai_body import service_threads

    service_threads.stop_all(timeout=2.0)


LIVE_HOST = "localhost"
LIVE_PORT = 8000


def _live_daemon_reachable() -> bool:
    try:
        with socket.create_connection((LIVE_HOST, LIVE_PORT), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.fixture(params=["fake", "live"])
def body_client(request):
    """A body client behind the seam: the fake always, the live simulator opt-in.

    Live only runs when ``MAIPAI_BODY_LIVE=1`` is set and the daemon
    answers on port 8000; otherwise it is skipped with a reason, never
    failed (AGENTS.md: "the whole suite runs twice ... otherwise skipped
    with a reason, never failed").
    """
    if request.param == "fake":
        client = FakeReachyMiniClient(REACHY_MINI_PROFILE)
        yield client
        return

    import os

    if os.environ.get("MAIPAI_BODY_LIVE") != "1":
        pytest.skip("MAIPAI_BODY_LIVE is not set to 1")
    if not _live_daemon_reachable():
        pytest.skip(f"no daemon answering on {LIVE_HOST}:{LIVE_PORT}")

    client = ReachyMiniClient(REACHY_MINI_PROFILE, host=LIVE_HOST, port=LIVE_PORT)
    yield client
    client.disconnect()


# ---- the virtual unit (scripts/virtual-unit) needs the host renderer, which is built from a firmware tree on this Mac ----
import os  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
_RENDER = _REPO / ".runs" / "vu-build" / "render"
_VU_FILES = ("test_vu_tools_", "test_virtual_unit")


def _inputs_stamp() -> str:
    """A hash of everything the renderers are built from: the build scripts, the renderer sources and the face patches the overlay applies. When it differs from the
    stamp of the last build, the renderer is stale (the goldens are drawn from the patched code, so a stale renderer fails them for no reason in the code)."""
    import hashlib
    import re

    h = hashlib.sha256()
    vu, fr = _REPO / "scripts" / "virtual-unit", _REPO / "scripts" / "fw-face-render"
    names = [vu / "build-face.sh", vu / "build-screens.sh", vu / "cover_gen.py", vu / "cover_render.cc"] + sorted(p for p in fr.iterdir() if p.is_file())
    listed = re.search(r'FACE_PATCHES="([^"]*)"', (vu / "build-face.sh").read_text())
    names += [_REPO / "firmware" / "patches" / n for n in (listed.group(1).split() if listed else [])]
    for p in names:
        h.update(p.name.encode())
        h.update(p.read_bytes() if p.exists() else b"missing")
    return h.hexdigest()


def _renderer_is_current() -> bool:
    stamp = _REPO / ".runs" / "vu-build" / "inputs.sha"
    return _RENDER.exists() and stamp.exists() and stamp.read_text().strip() == _inputs_stamp()


def _build_renderers() -> str:
    """Builds the face and screens renderers when MAIPAI_BUILD_RENDERER=1 and a firmware tree is on this Mac. Returns a reason when it cannot."""
    ref = subprocess.run([sys.executable, str(_REPO / "scripts" / "ref-tree.py")], capture_output=True, text=True)   # MAIPAI_FW_TREE_ROOT, else main's reference tree
    if ref.returncode != 0:
        return ref.stderr.strip()
    tree = Path(ref.stdout.strip())
    if shutil.which("clang") is None or not (tree / "firmware" / "managed_components").exists():
        return f"needs clang and a built firmware tree (looked at {tree})"
    face_build = _REPO / "scripts" / "fw-face-render" / "build.sh"
    for cmd in (["bash", str(_REPO / "scripts" / "virtual-unit" / "build-face.sh"), str(tree)], ["bash", str(_REPO / "scripts" / "virtual-unit" / "build-screens.sh")]):
        run = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True)
        if run.returncode != 0 or not face_build.exists():
            return "the renderer build failed: " + (run.stderr or run.stdout)[-300:]
    (_REPO / ".runs" / "vu-build" / "inputs.sha").write_text(_inputs_stamp() + "\n")
    return ""


def pytest_collection_modifyitems(config, items):
    """The virtual unit tests skip with one clear message when the renderer is not built; MAIPAI_BUILD_RENDERER=1 builds it first (the full suite does)."""
    unit_items = [i for i in items if Path(str(i.fspath)).name.startswith(_VU_FILES)]
    if not unit_items:
        return
    if not _renderer_is_current() and os.environ.get("MAIPAI_BUILD_RENDERER") == "1":   # absent or built from older inputs
        why = _build_renderers()
        if why:
            print(f"\nvirtual unit renderer not built: {why}")
    if not _RENDER.exists():
        skip = pytest.mark.skip(reason="virtual unit renderer not built: run bash scripts/virtual-unit/build-face.sh (needs clang and a firmware tree, see docs/dev/virtual-unit.md) or set MAIPAI_BUILD_RENDERER=1")
        for item in unit_items:
            item.add_marker(skip)
