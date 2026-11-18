# ruff: noqa: E501
"""The renderer behind the golden frames was built from a firmware tree that holds the whole current patch series (scripts/virtual-unit/overlay_patches.py writes .runs/vu-build/tree-stamp.json
when build-face.sh runs): a stale tree fails here instead of silently drawing old pictures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STAMP = ROOT / ".runs" / "vu-build" / "tree-stamp.json"

pytestmark = pytest.mark.skipif(not STAMP.exists(), reason="renderer not built (bash scripts/virtual-unit/build-face.sh)")


def test_the_renderer_was_built_from_the_current_series():
    s = json.loads(STAMP.read_text())
    assert s["order_sha"] == hashlib.sha1((ROOT / "firmware" / "patches" / "ORDER").read_bytes()).hexdigest(), "firmware/patches/ORDER changed since the renderer was built: run bash scripts/virtual-unit/build-face.sh and build-screens.sh, then scenarios.py and look at what changed"
    assert not s["failed"], s["failed"]
    assert "b" in Path(s["tree"]).name, s["tree"]   # a replayed tree (bNN), not the old final15 tree
