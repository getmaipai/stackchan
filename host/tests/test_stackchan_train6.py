# ruff: noqa: E501
"""Train 6 (firmware patches V02 offline phrases, V03 music dance, V04 dance extras): the C cores, the patch files,
the embedded clips and the host copies of the firmware's tables."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body.bodies.stackchan.companion import BUILTIN_DANCES, DANCES, EXTRA_DANCES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
C_TESTS = HERE / "firmware"
FIRMWARE = ROOT / "host" / "maipai_body" / "bodies" / "stackchan" / "firmware"
PHRASES = FIRMWARE / "assets" / "phrases"
TRAIN6 = [
    "V02-offline-phrases.patch",
    "V03-music-dance.patch",
    "V04-dance-extras.patch",
]
SOUNDS_CHAIN = [
    "115-sounds-core.patch",
    "116-sound-policy-tools.patch",
    "T02-hourly-chime-quiet-hours.patch",
]


def _apply(work: Path, names: list[str], include: str) -> None:
    for name in names:
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        diff.write_text(text[text.index("diff --git") :])
        run = subprocess.run(
            ["git", "apply", f"--include={include}", str(diff)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, f"{name}: {run.stderr}"


@pytest.fixture(scope="module")
def headers(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The pure C headers as the patches leave them."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    work = tmp_path_factory.mktemp("cores6")
    _apply(work, SOUNDS_CHAIN, "firmware/main/hal/maipai_sounds_core.h")
    _apply(work, TRAIN6[1:], "firmware/main/hal/*.h")
    return work / "firmware" / "main" / "hal"


def _c_test(headers: Path, source: str, tmp_path: Path) -> str:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    binary = tmp_path / "t"
    build = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{headers}",
            str(C_TESTS / source),
            "-o",
            str(binary),
            "-lm",
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    return run.stdout


@pytest.mark.parametrize(
    "source", ["music_mood_test.c", "dances_core_test.c", "phrase_flow_test.c"]
)
def test_the_c_cores_pass_their_tests(headers: Path, source: str, tmp_path: Path) -> None:
    assert "all passed" in _c_test(headers, source, tmp_path)


def test_the_music_headers_are_the_ones_the_older_host_tests_compile(headers: Path) -> None:
    """beat_test.c, music_core_test.c and music_judge_test.c (and their Python tests) run on the same bytes."""
    old = (
        PATCHES.parent.parent
        / "host/maipai_body/bodies/stackchan/firmware/patches/100-music-features.patch"
    ).read_text()
    block = old.split("+++ b/firmware/main/hal/maipai_music_core.h\n", 1)[1].split(
        "\ndiff --git", 1
    )[0]
    body = "\n".join(line[1:] for line in block.splitlines()[1:] if line.startswith("+")) + "\n"
    assert (headers / "maipai_music_core.h").read_text() == body
    assert (headers / "maipai_music_judge.h").read_text() == (
        FIRMWARE / "assets/maipai_music_judge.h"
    ).read_text()
    assert (headers / "maipai_beat.h").read_text() == (
        FIRMWARE / "assets/maipai_beat.h"
    ).read_text()


# ---- the patch files ----


def test_every_train6_patch_has_its_header_lines_and_ends_the_order() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    assert order[-3:] == TRAIN6
    for name in TRAIN6:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in (
            "# Intent:",
            "# Placement: unit",
            "# Upstream:",
            "# Check after a flash:",
            "# Kconfig:",
        ):
            assert key in head, f"{name} has no '{key}' line"
        assert chr(8212) not in text, f"{name} has an em dash"
        assert not re.search(
            r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+(?:\.\d+)?\b", text
        ), f"{name} has a LAN address"


def test_every_new_feature_has_a_kconfig_switch() -> None:
    expect = {
        "V02-offline-phrases.patch": ("MAIPAI_OFFLINE_PHRASES", "default y"),
        "V03-music-dance.patch": ("MAIPAI_MUSIC_DANCE", "default y"),
        "V04-dance-extras.patch": ("MAIPAI_DANCE_EXTRAS", "default y"),
    }
    for name, (symbol, default) in expect.items():
        text = (PATCHES / name).read_text()
        block = text.split(f"+config {symbol}\n", 1)[1].split("\n+\n", 1)[0]
        assert default in block, f"{symbol}: {default}"
        assert f"# Kconfig: {symbol}" in text


# ---- V02: the clips ----


def test_the_build_embeds_exactly_the_clips_the_manifest_lists() -> None:
    text = (PATCHES / "V02-offline-phrases.patch").read_text()
    cmake = re.search(r"set\(MAIPAI_PHRASE_FILES\n(.*?)\)\n", text, re.S)
    assert cmake is not None
    listed = [n for n in cmake.group(1).replace("+", " ").split() if n.endswith(".ogg")]
    manifest = json.loads((PHRASES / "phrases.json").read_text())
    assert sorted(listed) == sorted(c["file"] for c in manifest["clips"])
    assert len(listed) == 16
    for name in listed:
        data = (PHRASES / name).read_bytes()
        assert data[:4] == b"OggS", name
    # The table in maipai_sounds.cc names every clip once, in the core's group order and sizes.
    symbols = re.findall(r"PH_CLIP\((ph_[a-z_0-9]+)\)", text)
    assert [s + ".ogg" for s in symbols] == listed
    total = sum((PHRASES / n).stat().st_size for n in listed)
    assert total < 100_000  # flash data only; a bigger set needs a new look at the app slot


def test_group_sizes_in_the_core_match_the_files(headers: Path) -> None:
    core = (headers / "maipai_sounds_core.h").read_text()
    sizes = [
        int(x)
        for x in re.search(r"MS_GROUP_SIZE\[MS_GRP_COUNT\] = \{([0-9, ]+)\}", core)
        .group(1)
        .split(",")
    ]
    names = re.search(r"MS_GROUP_NAMES\[MS_GRP_COUNT\] = \{(.*?)\}", core).group(1)
    groups = re.findall(r'"([a-z_]+)"', names)
    for group, size in zip(groups, sizes, strict=True):
        found = sorted(PHRASES.glob(f"ph_{group}_*.ogg"))
        assert len(found) == size, group


def test_fw_env_points_the_build_at_the_clips() -> None:
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'MAIPAI_PHRASES_DIR= . "{ROOT}/scripts/fw-env.sh" >/dev/null 2>&1; echo "${{MAIPAI_PHRASES_DIR:-none}}"',
        ],
        capture_output=True,
        text=True,
    )
    out = result.stdout.strip().splitlines()[-1]
    # ESP-IDF may be missing on the machine running the test: then the script returns early and sets nothing.
    assert out in ("none", str(PHRASES))


# ---- V04: the dances ----


def test_host_dance_names_equal_the_firmware_table(headers: Path) -> None:
    core = (headers / "maipai_dances_core.h").read_text()
    names = set(re.findall(r'^\s*\{"([a-z_]+)", \d+,', core, re.M))
    assert names == set(EXTRA_DANCES)
    assert BUILTIN_DANCES.isdisjoint(EXTRA_DANCES)
    assert DANCES == BUILTIN_DANCES | EXTRA_DANCES
    text = (PATCHES / "V04-dance-extras.patch").read_text()
    for name in sorted(EXTRA_DANCES):
        assert name in text.split("diff --git", 1)[0]


# ---- V03: a regression found on the unit ----


def test_the_music_worker_never_reads_flash_from_its_psram_stack() -> None:
    """The worker's stack is in PSRAM; the saved privacy choice is read from flash on first use. Reading it from the
    worker crashed the unit in a boot loop (cache assert, 2026-11-16), so init must read it first, and the worker
    code must not open flash storage itself."""
    text = (PATCHES / "V03-music-dance.patch").read_text()
    init = text.index("(void)maipai_muted();")
    create = text.index("xTaskCreatePinnedToCoreWithCaps(worker_task")
    assert init < create
    worker = text[text.index("void worker_task(void*)") : text.index("bool nvs_enabled()")]
    for forbidden in ("nvs_", "Settings", "fopen", "esp_flash", "esp_partition"):
        assert forbidden not in worker, forbidden
