"""Leak guard: the header lines of the safety patches (SF*) name no review finding id and no attack words (the repo goes public)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PATCHES = Path(__file__).resolve().parents[2] / "firmware" / "patches"
B, A = r"(^|[^A-Za-z0-9_-])", r"([^A-Za-z0-9_-]|$)"
BAD = re.compile(rf"{B}([FGQHTUB]|FP|HC|HS|FM)-[0-9]+{A}|\b(bypass\w*|attack\w*|exploit\w*)\b", re.I)


@pytest.mark.parametrize("patch", sorted(PATCHES.glob("SF*.patch")), ids=lambda p: p.name[:4])
def test_safety_patch_headers_hold_no_finding_ids_or_attack_words(patch):
    header = [line for line in patch.read_text().splitlines() if line.startswith("# ")]
    hits = [line[:120] for line in header if BAD.search(line)]
    assert not hits, f"{patch.name}: reword these header lines to say what the patch does, not what a review found: {hits}"
