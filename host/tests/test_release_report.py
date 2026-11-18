"""scripts/release-report.py: images against the slot rule, memory only from a real log, never invented."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "release_report", ROOT / "scripts" / "release-report.py"
)
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)


def _tree(tmp_path, plain=3_000_000):
    root = tmp_path / "b0" / "firmware"
    root.mkdir(parents=True)
    (root / "partitions.csv").write_text(
        "# Name, Type, SubType, Offset, Size\nota_0, app, ota_0, 0x20000, 0x4f0000,\nassets, data, spiffs, 0xA00000, 0x5F0000,\n"
    )
    for folder, size in (
        ("build-plain", plain),
        ("build-gate", plain + 400),
        ("build-bench", 4_400_000),
    ):
        (root / folder).mkdir()
        (root / folder / "maipai-stackchan.bin").write_bytes(b"\0" * size)
    (root / "build-plain" / "generated_assets.bin").write_bytes(b"\0" * 1000)
    return root


def test_image_rows_show_room_before_the_rule_and_the_bench_build_is_exempt(tmp_path):
    text = "\n".join(rr.image_section(_tree(tmp_path)))
    assert "3,000,000" in text and "5,177,344" in text
    assert (
        "1,141,875" in text
    )  # room left: 5,177,344 - 3,000,000 - 20 percent of the slot (1,035,468)
    assert "developer build: the rule is not applied" in text
    low = "\n".join(rr.image_section(_tree(tmp_path / "x", plain=4_500_000)))
    assert "BELOW the rule" in low


def test_memory_is_measured_from_a_log_or_said_to_be_missing(tmp_path):
    assert "Not measured" in "\n".join(rr.memory_section(None))
    log = tmp_path / "stress.log"
    log.write_text(
        "boot\n"
        + "".join(
            f"mem internal_free={50000 + i} internal_min={40000 + i} int_big={30000} psram_free=7000000 psram_min=6500000\n"
            for i in range(20)
        )
    )
    text = "\n".join(rr.memory_section(log))
    assert "20 memory lines" in text and "40,000" in text and "30,000" in text
    empty = tmp_path / "empty.log"
    empty.write_text("nothing here")
    assert "Nothing measured" in "\n".join(rr.memory_section(empty))
