"""The unit's update header core (firmware patch SF25) against the shared vectors of the app track (host/tests/fixtures/update-header-vectors.json).

The core checks everything except the Ed25519 signature (update_verify.cc does that over the 56 header bytes): so a vector that is invalid only
because of its signature is accepted by the core, and the signature itself is covered by the host half."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
VECTORS = HERE / "fixtures" / "update-header-vectors.json"
needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")


@needs_cc
def test_the_core_agrees_with_the_shared_vectors(tmp_path, tmp_path_factory):
    if not VECTORS.exists():
        pytest.skip("the shared update header vectors are not in this checkout")
    vectors = json.loads(VECTORS.read_text())["vectors"]
    binary = tmp_path / "updatehdr"
    build = subprocess.run(
        ["cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", f"-I{cores_dir(tmp_path_factory)}", str(HERE / "firmware" / "updatehdr_core_test.c"), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    lines = []
    for v in vectors:
        installed = -1 if v["installed_build"] is None else int(v["installed_build"])
        lines.append(f"{v['package_hex'] or '00'} {v['image_hex'] or '-'} {installed}")
    run = subprocess.run([str(binary)], input="\n".join(lines) + "\n", capture_output=True, text=True)
    verdicts = run.stdout.split()
    assert len(verdicts) == len(vectors)
    for v, got in zip(vectors, verdicts, strict=True):
        accepted = got == "0"
        # a vector refused only because its signature is wrong is accepted by this core: the signature is checked by update_verify.cc
        only_signature = v["name"].startswith("signature changed")
        expected = True if only_signature else v["valid"]
        assert accepted == expected, f"{v['name']}: core said {got}, expected accepted={expected}"
