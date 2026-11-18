"""Every unit tool name the host sends is defined by a firmware patch or stated in tool_parity.py."""

import re
from pathlib import Path

from maipai_body.bodies.stackchan import tool_parity as tp

ROOT = Path(__file__).resolve().parents[2]
NAME = re.compile(r"""["'](self\.[a-z_]+\.[a-z_0-9]+)["']""")
ANY = re.compile(r"self\.[a-z_]+\.[a-z_0-9]+")


def _host_names() -> set[str]:
    found: set[str] = set()
    for path in (ROOT / "host" / "maipai_body").rglob("*.py"):
        found |= set(NAME.findall(path.read_text(errors="ignore")))
    return found


def _firmware_names() -> set[str]:
    found: set[str] = set()
    for path in (ROOT / "firmware").rglob("*"):
        if path.is_file():
            try:
                found |= set(ANY.findall(path.read_text(errors="ignore")))
            except OSError:
                pass
    return found


def test_no_host_call_lacks_a_definition_or_a_stated_status():
    stated = tp.BASE_FIRMWARE | tp.SIMULATOR_ONLY | tp.HOST_HALF_ONLY
    unknown = sorted(_host_names() - _firmware_names() - stated)
    assert not unknown, f"the host sends tools no firmware patch defines: {unknown}. Add the patch, or list them in tool_parity.py with a reason."


def test_a_name_that_got_a_firmware_definition_leaves_the_list():
    defined = _firmware_names()
    stale = sorted((tp.HOST_HALF_ONLY | tp.SIMULATOR_ONLY) & defined)
    assert not stale, f"these now exist in the firmware, remove them from tool_parity.py: {stale}"


def test_the_fourteen_host_half_only_calls_are_all_still_sent_by_the_host():
    assert len(tp.HOST_HALF_ONLY) == 14
    assert tp.HOST_HALF_ONLY <= _host_names()
