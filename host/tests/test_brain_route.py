"""The brain route switch of the playground (decision 34): joining hosted writes only the cl_ settings, leaving it wipes them and shows the Hosted link removed notice, the host pairing
survives both. The notice is drawn by the unit's own screen code when the patch is built into the renderer."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))
import brain_route  # noqa: E402


def test_joining_hosted_never_touches_the_host_pairing_and_leaving_it_wipes_the_cl_settings():
    b = brain_route.BrainRoute("wss://192.0.2.10:8780/ws", "paired-token", lang=0)
    b.join_hosted()
    assert b.route == "hosted" and b.nvs["websocket"] == {"url": "wss://192.0.2.10:8780/ws", "token": "paired-token"}
    assert b.hosted_traces() == ["cl_websocket.url", "cl_websocket.token"]
    b.switch_to_custom()
    assert b.route == "custom" and b.hosted_traces() == [] and b.nvs["cl_websocket"] == {} and b.nvs["cl_mqtt"] == {}
    assert b.nvs["websocket"]["token"] == "paired-token"          # the host pairing stays
    assert b.notice == "bnotice 0" and b.events[-2:] == ["route custom", "hosted link removed"]
    b.acknowledge()
    assert b.notice is None


def test_a_switch_that_changes_nothing_shows_no_notice():
    b = brain_route.BrainRoute("wss://192.0.2.10:8780/ws", "t", lang=2)
    b.switch_to_custom()
    assert b.notice is None and b.events == []


@pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built")
def test_the_notice_is_the_golden_frame_the_unit_draws():
    scen = importlib.util.spec_from_file_location("sc", VU / "scenarios.py")
    sc = importlib.util.module_from_spec(scen)
    scen.loader.exec_module(sc)
    if "brain-removed-fr" not in sc.SCREENS:
        pytest.skip("patch UX20 is not in firmware/patches/ORDER")
    b = brain_route.BrainRoute("wss://192.0.2.10:8780/ws", "t", lang=2)
    b.join_hosted()
    b.switch_to_custom()
    with sc.vunit.VirtualUnit(profile="screens") as u:
        u.raw(b.notice)
        u.advance(400)
        png = u.snapshot()
    gold = (sc.GOLDEN_SCREENS / "brain-removed-fr.png").read_bytes()
    assert sc.png_pixels(png) == sc.png_pixels(gold)
