"""Firmware wiring for the first-run brain choice and the hosted leave notice."""
import os
import re
from pathlib import Path


DEFAULT_HAL = Path("/Users/jessetorres/esp/stackchan-rebuild/b89/firmware/main/hal")
HAL = Path(os.environ.get("STACKCHAN_FIRMWARE_HAL", DEFAULT_HAL))


def source(name: str) -> str:
    path = HAL / name
    assert path.is_file(), f"Firmware source is missing: {path}"
    return path.read_text()


def function_body(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for end in range(brace, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : end]
    raise AssertionError(f"Unclosed function body for {signature}")


def test_first_run_saves_selected_route_in_the_sf98_brain_pref():
    core = source("maipai_hosted_core.h")
    assert re.search(r'#define\s+MHS_ROUTE_NS\s+"mp_brain"', core)
    assert re.search(r'"hosted"\s+or\s+"custom"', core)

    wire = source("maipai_firstrun_wire.cc")
    finished = function_body(wire, "void finished(")
    assert '#include "maipai_hosted_core.h"' in wire
    assert '#include "maipai_firstrun_core.h"' in wire
    assert 'Settings brain(MHS_ROUTE_NS, true)' in finished
    assert 'brain.SetString("route", mode == MFR_MODE_HOSTED ? "hosted" : "custom")' in finished
    assert finished.index('brain.SetString("route"') < finished.index('st.SetInt("done", 1)')

    boot = function_body(wire, "void maipai_firstrun_boot_poll(")
    assert "if (record_exists()) return" in boot


def test_leaving_hosted_builds_the_finished_notice_before_restart():
    hosted = source("maipai_hosted.cc")
    leave = function_body(hosted, "void maipai_hosted_leave(")
    assert '#include "maipai_brain_notice.h"' in hosted
    assert "mbn::build(lv_layer_top(), language_index(), on_ok, nullptr)" in leave
    assert "arm_restart(60ll * 1000 * 1000)" in leave
    assert "arm_restart(300 * 1000)" in hosted
