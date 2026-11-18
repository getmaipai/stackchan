"""Tool parity: every firmware tool is either simulated or a named gap. Unsimulated tools xfail (strict), so this list is the work queue:
simulate a tool, add it to SIMULATED in scripts/virtual-unit/vunit.py, and its xfail turns into a failure that tells you to drop the marker."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit", ROOT / "scripts" / "virtual-unit" / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)
TOOLS = sorted(json.loads((ROOT / "schema" / "tools.json").read_text())["tools"])
needs_render = pytest.mark.skipif(not (ROOT / ".runs" / "vu-build" / "render").exists(), reason="renderer not built")


def test_simulated_tools_exist_in_the_firmware():
    assert vunit.SIMULATED <= set(TOOLS), vunit.SIMULATED - set(TOOLS)


@needs_render
@pytest.mark.parametrize("name", TOOLS)
def test_tool_is_simulated(name):
    if name not in vunit.SIMULATED:
        pytest.xfail("gap: the firmware has this tool, the virtual unit has no behavior for it yet")
    with vunit.VirtualUnit() as u:
        args = {}
        out = u.call(name, args)
        assert "not simulated" not in out.get("text", ""), out


@needs_render
def test_arguments_are_checked_against_the_schema():
    with vunit.VirtualUnit() as u:
        bad = u.call("self.face.bench_speak", {"loudness": 3})
        assert bad["isError"] and "no argument" in bad["text"]
        assert u.call("self.face.bench_speak", {"level": "loud"})["isError"]
