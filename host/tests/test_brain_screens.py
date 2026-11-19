"""Patches UX19 (the brain step with two equal routes) and UX20 (the Hosted link removed notice), owner decision 34. UX20's pure core is tested here against the patch text; both patches must
be on ORDER with their header lines, UX19 after UX13d, and the route and notice words must exist in all six languages. They wait on the branch ux/unproven-games until their bench proof."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
P19 = "UX19-brain-two-equal-routes.patch"
P20 = "UX20-hosted-link-removed-notice.patch"
P20B = "UX20b-notice-console-line.patch"
if not (PATCHES / P19).exists() or not (PATCHES / P20).exists() or not (PATCHES / P20B).exists():
    pytest.skip("UX19 and UX20 are not in firmware/patches yet", allow_module_level=True)


def _added(name: str, path: str) -> str:
    text = (PATCHES / name).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out) + "\n"


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_notice_core_test_passes_against_the_patch_text(tmp_path):
    tree = tmp_path / "tree"
    hal = tree / "firmware" / "main" / "hal"
    hal.mkdir(parents=True)
    for f in ("maipai_brain_notice_core.h", "maipai_brain_notice.h"):
        (hal / f).write_text(_added(P20, f"firmware/main/hal/{f}"))
    done = subprocess.run(["patch", "-p1", "-s", "-f"], input="diff --git" + (PATCHES / P20B).read_text().split("diff --git", 1)[1], cwd=tree, capture_output=True, text=True)   # UX20b adds the console line to what UX20 made
    assert done.returncode == 0, done.stdout + done.stderr
    (tmp_path / "maipai_brain_notice_core.h").write_text((hal / "maipai_brain_notice_core.h").read_text())
    binary = tmp_path / "t"
    build = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{tmp_path}", str(HERE / "firmware" / "brain_notice_core_test.c"), "-o", str(binary)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_both_patches_are_on_order_with_their_header_lines_and_ux19_follows_ux13d():
    order = (PATCHES / "ORDER").read_text().split()
    assert P19 in order and P20 in order
    assert order.index(P19) > order.index("UX13d-first-run-at-finger-size.patch")
    for name in (P19, P20):
        head = (PATCHES / name).read_text().split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
            assert key in head, f"{key} missing from the header of {name}"


def test_the_routes_have_words_in_six_languages_and_say_where_the_voice_goes():
    body = (PATCHES / P19).read_text()
    assert body.count("M5Stack/Xiaozhi") >= 6          # route A is named in every language
    for word in ("Custom", "Personalizado", "Personnalisé", "Eigene Wahl", "Personalizzato"):
        assert word in body, word
    assert "MFR_MODE_HOSTED = 3" in body and "Skip" in (PATCHES / P19).read_text()


def test_the_notice_file_stays_free_of_the_hardware():
    for f in ("firmware/main/hal/maipai_brain_notice_core.h", "firmware/main/hal/maipai_brain_notice.h"):
        assert not re.search(r"esp_|nvs_|hal_bridge|Application|Board::|malloc|calloc", _added(P20, f)), f"{f} must stay free of hardware calls so the host renderer compiles it"
