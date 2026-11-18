"""Pins the self-restart counter's rule (2026-11-18): the saved count (NVS key heal_n) is written in one place, and that place is
reached only through maipai_heal_restart. A flash, a power-on or any reset reason must never raise it. Reads the replayed tree
named by STACKCHAN_FW_TREE (default ~/esp/stackchan-rebuild/landcheck); skips when there is no tree."""
import os
import pathlib
import re

import pytest

TREE = pathlib.Path(os.environ.get("STACKCHAN_FW_TREE", str(pathlib.Path.home() / "esp/stackchan-rebuild/landcheck")))
HAL = TREE / "firmware/main/hal"


@pytest.mark.skipif(not (HAL / "maipai_heal.cc").exists(), reason="no replayed firmware tree; run scripts/fw-rebuild.sh first")
def test_only_a_self_restart_writes_the_count():
    src = (HAL / "maipai_heal.cc").read_text()
    assert len(re.findall(r'nvs_set_i32\(h, "heal_n"', src)) == 1
    assert len(re.findall(r"\bsave_locked\(", src)) == 2  # the definition and the one call
    # the one call sits in restart_task, and only maipai_heal_restart creates that task
    assert src.index("save_locked(request->why)") < src.index("void maipai_heal_restart(const char* why")
    assert len(re.findall(r'xTaskCreate\([^;]*"heal_restart"', src)) == 1
    for p in (q for q in HAL.glob("*.cc") if q.name != "maipai_heal.cc"):
        assert '"heal_n"' not in p.read_text(), f"{p.name} writes the self-restart count"
    assert "esp_reset_reason()" not in src.split("void maipai_heal_boot_report")[0]  # the reset reason is only read to report it, never to count
