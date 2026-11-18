"""Shared fixtures: the deterministic suite runs against the fake always, and
against the live simulator only when it is reachable and asked for.
"""

from __future__ import annotations

import socket

import pytest

from maipai_body.bodies.reachy_mini.client import ReachyMiniClient
from maipai_body.bodies.reachy_mini.fake import FakeReachyMiniClient
from maipai_body.bodies.reachy_mini.profile import REACHY_MINI_PROFILE

pytest_plugins = ["tests.exit_guard"]

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
from pathlib import Path  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
_RENDER = _REPO / ".runs" / "vu-build" / "render"
_VU_FILES = ("test_vu_tools_", "test_virtual_unit")


def _build_renderers() -> str:
    """Builds the face and screens renderers when MAIPAI_BUILD_RENDERER=1 and a firmware tree is on this Mac. Returns a reason when it cannot."""
    tree = Path(os.environ.get("MAIPAI_FW_TREE_ROOT", Path.home() / "esp" / "stackchan-rebase" / "final15"))
    if shutil.which("clang") is None or not (tree / "firmware" / "managed_components").exists():
        return f"needs clang and a built firmware tree (set MAIPAI_FW_TREE_ROOT; looked at {tree})"
    face_build = _REPO / "scripts" / "fw-face-render" / "build.sh"
    for cmd in (["bash", str(_REPO / "scripts" / "virtual-unit" / "build-face.sh"), str(tree)], ["bash", str(_REPO / "scripts" / "virtual-unit" / "build-screens.sh")]):
        run = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True)
        if run.returncode != 0 or not face_build.exists():
            return "the renderer build failed: " + (run.stderr or run.stdout)[-300:]
    return ""


def pytest_collection_modifyitems(config, items):
    """The virtual unit tests skip with one clear message when the renderer is not built; MAIPAI_BUILD_RENDERER=1 builds it first (the full suite does)."""
    unit_items = [i for i in items if Path(str(i.fspath)).name.startswith(_VU_FILES)]
    if not unit_items:
        return
    if not _RENDER.exists() and os.environ.get("MAIPAI_BUILD_RENDERER") == "1":
        why = _build_renderers()
        if why:
            print(f"\nvirtual unit renderer not built: {why}")
    if not _RENDER.exists():
        skip = pytest.mark.skip(reason="virtual unit renderer not built: run bash scripts/virtual-unit/build-face.sh (needs clang and a firmware tree, see docs/dev/virtual-unit.md) or set MAIPAI_BUILD_RENDERER=1")
        for item in unit_items:
            item.add_marker(skip)
