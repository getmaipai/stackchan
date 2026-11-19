# ruff: noqa: E501
"""The Lock page in the dashboard look: its keys are in the page script, the script parses in every language, the view stays inside the row budget."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from maipai_body import i18n
from maipai_body.settings_page import render_page
from maipai_body.settings_ui_p_lock import JS

ROW = re.compile(r"\b(?:rowEl|swRow|sgRow|slRow)\(")


def test_the_page_script_holds_the_lock_keys() -> None:
    page = render_page("en").decode()
    assert "DETAIL['safety/lock']" in page and "DETAIL['safety/lock-code']" in page


def test_the_script_parses_in_every_language() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    for code in i18n.SUPPORTED:
        script = re.search(r"<script>([\s\S]*)</script>", render_page(code).decode())
        assert script is not None
        result = subprocess.run([node, "--check", "/dev/stdin"], input=script.group(1), capture_output=True, text=True)
        assert result.returncode == 0, (code, result.stderr)


def test_the_view_has_at_most_six_rows_before_the_fold() -> None:
    body = JS.split("DETAIL['safety/lock']=", 1)[1].split("DETAIL['safety/lock-code']", 1)[0]
    before_fold = body.split("moreFold(", 1)[0]
    assert len(ROW.findall(before_fold)) <= 6
    assert body.count("moreFold(") == 1


def test_the_code_never_leaves_through_a_url_or_storage() -> None:
    assert "localStorage" not in JS and "sessionStorage" not in JS and "console." not in JS
    assert "unitPath(UNIT.device_id,'lock')" in JS
    assert all(w not in JS for w in ("\u2014",))


def test_the_calls_are_the_old_ones() -> None:
    for call in ("'lock'", "'lock/clear'", "'lock/now'", "'lock/auto'"):
        assert call in JS
