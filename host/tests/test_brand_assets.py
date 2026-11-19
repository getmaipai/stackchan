"""Drift test for the brand art copies (never edited, never redrawn; refreshed only by copying again).

The org art lives in getmaipai/.github (folder brand/). This repo carries two byte-for-byte copies: one for the host package
(host/maipai_body/assets/brand) and one for the docs site (docs-site/assets/brand). Each folder lists the sha256 of every file in its
PROVENANCE.md. Placement: host-side test; no firmware change. Upstream: none.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOST_COPY = ROOT / "host" / "maipai_body" / "assets" / "brand"
SITE_COPY = ROOT / "docs-site" / "assets" / "brand"
SOURCE = Path.home() / "Developer" / "github.com" / "getmaipai" / ".github-wt-wsettings" / "brand"
FILES = (
    "maipai-bot-icon-dark.png",
    "maipai-bot-icon-light.png",
    "maipai-bot-logo-dark.png",
    "maipai-bot-logo-light.png",
    "maipai-brand-icon.png",
)
LINE = re.compile(r"^([0-9a-f]{64})  (\S+\.png)$", re.M)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def listed(folder: Path) -> dict[str, str]:
    text = (folder / "PROVENANCE.md").read_text(encoding="utf-8")
    return {name: digest for digest, name in LINE.findall(text)}


@pytest.mark.parametrize("folder", [HOST_COPY, SITE_COPY], ids=["host", "docs-site"])
def test_copy_matches_its_provenance_lines(folder: Path) -> None:
    lines = listed(folder)
    assert sorted(lines) == sorted(FILES), (
        f"{folder.relative_to(ROOT)}/PROVENANCE.md must list exactly {sorted(FILES)}. Copy the art again from the source folder and rewrite the list."
    )
    for name in FILES:
        assert (folder / name).is_file(), f"{folder.relative_to(ROOT)}/{name} is missing. Copy it again from the source folder."
        assert sha(folder / name) == lines[name], (
            f"{folder.relative_to(ROOT)}/{name} differs from its PROVENANCE.md line. The art is never edited: copy the file again and update the line."
        )


def test_provenance_names_the_source_commit() -> None:
    for folder in (HOST_COPY, SITE_COPY):
        text = (folder / "PROVENANCE.md").read_text(encoding="utf-8")
        assert re.search(r"Source commit: [0-9a-f]{40}", text), f"{folder.relative_to(ROOT)}/PROVENANCE.md needs a 'Source commit: <40 hex>' line."
        assert "Never edit or redraw" in text, f"{folder.relative_to(ROOT)}/PROVENANCE.md lost the never-edit rule."


def test_the_two_copies_are_identical() -> None:
    assert listed(HOST_COPY) == listed(SITE_COPY), "The host copy and the docs-site copy list different hashes. Refresh both from the source folder."
    for name in FILES:
        assert (HOST_COPY / name).read_bytes() == (SITE_COPY / name).read_bytes(), f"{name} differs between the host copy and the docs-site copy. Copy it again into both."


def test_copies_equal_the_source_when_the_source_is_here() -> None:
    if not SOURCE.is_dir():
        pytest.skip(f"the org brand folder {SOURCE} is not on this machine, so the copies were checked against PROVENANCE.md only")
    for name in FILES:
        src = SOURCE / name
        assert src.is_file(), f"{src} is missing in the source folder. Check the source commit named in PROVENANCE.md."
        assert sha(HOST_COPY / name) == sha(src), f"{name} differs from the org brand folder. Copy it again, never edit it."
        assert sha(SITE_COPY / name) == sha(src), f"{name} (docs-site) differs from the org brand folder. Copy it again, never edit it."


def test_png_files_ship_in_the_package() -> None:
    """Hatch includes every file under packages = ["maipai_body", ...] that git does not ignore; a .gitignore rule must not hide the art."""
    import subprocess

    res = subprocess.run(["git", "check-ignore", *[str((HOST_COPY / n).relative_to(ROOT)) for n in FILES]], cwd=ROOT)
    assert res.returncode == 1, "a .gitignore rule hides the brand PNGs, so the wheel would leave them out. Remove the rule."
