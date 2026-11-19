"""Patch UX30 (docs/plan/unit-settings-simplification.md): the unit's Settings app has fewer rows, header only. The patch touches maipai_apps_core.h and nothing else, carries its header lines, moves the two
switches to the Look tab and drops the rows the plan names; the renderer draws the tabs (the goldens are checked by the scenario test). The patch waits on the branch ux/unproven-games for a flash."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "firmware" / "patches"
NAME = "UX30-settings-fewer-rows.patch"
if not (PATCHES / NAME).exists():
    pytest.skip("the settings simplification patch is not in firmware/patches yet", allow_module_level=True)


def _lines(prefix):
    return [l[1:].strip() for l in (PATCHES / NAME).read_text().splitlines() if l.startswith(prefix) and not l.startswith(prefix * 3)]


def test_header_only_and_it_has_its_header_lines():
    text = (PATCHES / NAME).read_text()
    assert re.findall(r"^diff --git a/(\S+) b/", text, re.M) == ["firmware/main/hal/maipai_apps_core.h"]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in text.split("diff --git", 1)[0], key
    assert NAME in (PATCHES / "ORDER").read_text().split()


def test_general_loses_rows_and_the_two_switches_move_to_the_look_tab():
    removed, added = "\n".join(_lines("-")), "\n".join(_lines("+"))
    for gone in ("ids[n++] = MAC_R_STATUS_ICONS;", "ids[n++] = MAC_R_LISTEN_LIGHT;", "ids[n++] = MAC_R_LOCK_NOW;", "ids[n++] = MAC_R_SIGNAL;"):
        assert gone in removed, gone
    assert added.count("ids[n++] = MAC_R_STATUS_ICONS;") == 1 and added.count("ids[n++] = MAC_R_LISTEN_LIGHT;") == 1   # moved, not dropped
    assert "ids[n++] = MAC_R_LOCK_NOW;" not in added and "ids[n++] = MAC_R_SIGNAL;" not in added
    assert '"Look"' in added and '"Aspecto"' in added                                                                      # the tab is renamed in both languages


def test_row_sizes_and_the_finger_size_numbers_are_not_touched():
    changed = "\n".join(_lines("+") + _lines("-"))
    for number in ("MAC_ROW_BOX_H", "MAC_SLIDER_ROW_H", "MAC_LINE_ROW_H", "MAC_TAB_H", "MAC_TAB_PITCH"):
        assert number not in changed, number


def test_ux31_first_run_skips_the_brain_question_with_a_hub_header_only():
    name = "UX31-first-run-skips-brain-with-hub.patch"
    if not (PATCHES / name).exists():
        pytest.skip("UX31 is not in firmware/patches yet")
    text = (PATCHES / name).read_text()
    assert re.findall(r"^diff --git a/(\S+) b/", text, re.M) == ["firmware/main/hal/maipai_firstrun_core.h"]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in text.split("diff --git", 1)[0], key
    assert name in (PATCHES / "ORDER").read_text().split()
    added = "\n".join(l[1:] for l in text.splitlines() if l.startswith("+") and not l.startswith("+++"))
    assert "MFR_SKIP_BRAIN_WITH_HUB" in added and "mfr_enter_brain" in added and "hub_known" in added
    assert "m->mode = MFR_MODE_HOME;" in added and "MFR_ANSWER_BRAIN" in added   # the answer is Home, saved as if tapped
