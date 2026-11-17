"""The public repository holds source and a build recipe only: no vendor model or library binaries.

Espressif's speech library, its wake word and command models, and any trained keyword model are downloaded by the build
(see THIRD-PARTY.md); none may be committed here. This test fails on a tracked file that looks like one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = (".espdl", ".a", ".lib", ".tflite", ".so", ".dylib", ".elf")
FORBIDDEN_NAME_PARTS = ("wn9_", "wn9l_", "mn5q8", "esp-sr", "libwakenet", "libesp_audio_front_end")


def test_no_vendor_model_or_library_binaries_are_tracked() -> None:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    bad = [
        path
        for path in out
        if path.lower().endswith(FORBIDDEN_SUFFIXES)
        or (any(part in Path(path).name.lower() for part in FORBIDDEN_NAME_PARTS) and Path(path).suffix.lower() in {"", ".bin", ".h", ".c"})
    ]
    assert not bad, f"vendor binaries must be downloaded by the build, not committed: {bad[:5]}"
