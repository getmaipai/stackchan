"""Review fix: a locked unit refuses the tools that read or change its network and pairing setup, from one table checked in the tool dispatcher."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "firmware" / "patches" / "SF106-review-fix-locked-unit-keeps-network-setup.patch"


def test_the_dispatcher_checks_the_lock_before_any_tool_runs():
    text = PATCH.read_text()
    assert "mlg_needs_unlock(tool_name.c_str()) && maipai_lock_locked()" in text
    # the check comes before the cloud brain test's allow list and before the tool is looked up
    assert text.index("mlg_needs_unlock(tool_name.c_str())") < text.index("maipai_cloudtest_tool_allowed(tool_name.c_str())")


def test_the_table_names_every_network_and_pairing_family():
    text = PATCH.read_text()
    for name in ('"self.wifi."', '"self.tailnet.set"', '"self.network.prefer_tailnet"', '"self.link."', '"self.brain.set_route"'):
        assert name in text, name
