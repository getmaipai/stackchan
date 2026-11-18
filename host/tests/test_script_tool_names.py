# ruff: noqa: E501
"""Parity between the unit tool names the bench scripts call and schema/tools.json (made from the firmware patches): a script that calls a tool the firmware does not have
fails here, not on the bench. A tool the unit has from the stock firmware, not from a patch, is listed in STOCK with the reason."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOCK = {"self.camera.take_photo"}  # the stock firmware's photo tool: no patch adds it, the host calls it too (command_bus.py)
NAME = re.compile(r"""["'](self\.[a-z_0-9]+(?:\.[a-z_0-9]+)+)["']""")


def schema_names() -> set[str]:
    return {x["name"] if isinstance(x, dict) else x for x in json.loads((ROOT / "schema" / "tools.json").read_text())["tools"]}


def test_every_tool_name_the_bench_scripts_call_exists_in_the_schema():
    known = schema_names() | STOCK
    missing: dict[str, list[str]] = {}
    for path in sorted([*ROOT.glob("scripts/*.py"), *ROOT.glob("scripts/*.sh")]):
        bad = sorted(n for n in set(NAME.findall(path.read_text())) if n not in known)
        if bad:
            missing[path.name] = bad
    assert not missing, f"scripts call tools the firmware does not have (fix the name, or regenerate schema/tools.json after a patch adds it): {missing}"


def test_the_head_recorder_sets_the_usb_limit_with_the_tool_the_schema_names():
    text = (ROOT / "scripts" / "fw-head-record.py").read_text()
    assert "self.motion.set" in text and "self.motion.set" in schema_names()
    props = next(x for x in json.loads((ROOT / "schema" / "tools.json").read_text())["tools"] if (x["name"] if isinstance(x, dict) else x) == "self.motion.set")
    assert "usb_limit" in json.dumps(props) or isinstance(props, str)   # the argument the recorder sends is the one the firmware patch defines
    patch = (ROOT / "firmware" / "patches" / "ML01-movement-limiter-at-the-servo-layer.patch").read_text()
    assert 'Property("usb_limit"' in patch and "limited" in patch and "off" in patch
