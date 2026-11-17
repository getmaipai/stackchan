"""Track B firmware patches TB01 to TB05 (2026-11-16): the cores are plain C; compile and run their host tests, and check the
rules the patches must keep (listed on ORDER, header lines, no em dashes, the remote cue cannot be turned off)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
NAMES = [
    "TB01-listening-cues.patch",
    "TB02-pack-loader-and-flash-cache.patch",
    "TB03-while-it-thinks-filler.patch",
    "TB04-pickup-detection.patch",
    "TB05-visible-remote-control.patch",
]
CORES = {
    "maipai_listen_core.h": (NAMES[0], "listen_core_test.c", []),
    "maipai_pack_core.h": (NAMES[1], "pack_core_test.c", ["-lz"]),
    "maipai_packcache_core.h": (NAMES[1], "packcache_core_test.c", []),
    "maipai_filler_core.h": (NAMES[2], "filler_core_test.c", []),
    "maipai_pickup_core.h": (NAMES[3], "pickup_core_test.c", []),
    "maipai_remote_core.h": (NAMES[4], "remote_core_test.c", []),
}


def added_file(patch: str, path: str) -> str:
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def _extract_all(tmp_path: Path, ordered: Path) -> None:
    for header, (patch, _t, _l) in CORES.items():
        if header in ("maipai_pack_core.h", "maipai_packcache_core.h"):  # patches K10 to K13 change these two: test what ORDER leaves
            (tmp_path / header).write_text((ordered / header).read_text())
        else:
            (tmp_path / header).write_text(added_file(patch, f"firmware/main/hal/{header}"))


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
@pytest.mark.parametrize("header", list(CORES))
def test_core_c_tests_pass(tmp_path, header, tmp_path_factory):
    _extract_all(tmp_path, cores_dir(tmp_path_factory))
    patch, test, libs = CORES[header]
    binary = tmp_path / "t"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{tmp_path}", str(HERE / "firmware" / test), "-o", str(binary), *libs, "-lm"],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_patches_are_on_order_after_z01_and_carry_header_lines():
    order = (PATCHES / "ORDER").read_text().split()
    first = order.index(NAMES[0])
    assert first > order.index("Z01-boot-event-names-the-crash.patch")
    for name in NAMES:
        assert name in order
        text = (PATCHES / name).read_text()
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:"):
            assert key in text.split("diff --git", 1)[0], (name, key)
        assert chr(8212) not in text


def test_the_remote_glyph_and_tint_have_no_switch():
    text = (PATCHES / NAMES[4]).read_text()
    assert "CONFIG_MAIPAI" not in added_file(NAMES[4], "firmware/main/hal/maipai_remote.cc")
    assert "config MAIPAI_REMOTE" not in text


def test_the_cache_region_clears_the_asset_image():
    core = added_file(NAMES[1], "firmware/main/hal/maipai_packcache_core.h")
    assert "#define TPC_REGION_BYTES 0x180000u" in core and "#define TPC_ASSETS_PARTITION_BYTES 0x5F0000u" in core
    built = Path.home() / "esp/stackchan-rebase/trackB/firmware/build/generated_assets.bin"
    if built.exists():
        assert built.stat().st_size + 100_000 < 0x5F0000 - 0x180000
