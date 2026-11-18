# ruff: noqa: E501
"""The unit's pure C headers (``*_core.h``) as the whole of ``firmware/patches/ORDER`` leaves them.

Tests that compile a core must test the header the unit runs, not the one file a single patch added: later patches (K10 adds
a pack type, K11 changes the screen words) edit headers that earlier ones created. One shared copy per test session."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "firmware" / "patches"
_CACHE: dict[str, Path] = {}


def build_cores(work: Path) -> Path:
    """Applies every patch on ORDER to an empty folder, keeping only the ``hal/*_core.h`` files."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    names = [
        n.strip()
        for n in (PATCHES / "ORDER").read_text().splitlines()
        if n.strip() and not n.startswith("#")
    ]
    for name in names:
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        start = min(i for i in (text.find("diff --git"), text.find("\n--- ")) if i >= 0)
        diff.write_text(text[start:].lstrip("\n"))
        run = subprocess.run(
            ["git", "apply", "--include=firmware/main/hal/*_core.h", "--include=firmware/main/hal/maipai_beat.h", "--include=firmware/main/hal/maipai_music_judge.h", str(diff)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, f"{name}: {run.stderr}"
    return work / "firmware" / "main" / "hal"


def cores_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if "dir" not in _CACHE:
        _CACHE["dir"] = build_cores(tmp_path_factory.mktemp("ordercores"))
    return _CACHE["dir"]
