# ruff: noqa: E501
"""The System page in the dashboard look (settings_ui_p_system.py): found by file name, parses in every language, within the row budget."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from maipai_body import i18n, settings_ui_p_system
from maipai_body.settings_page import render_page

JS = settings_ui_p_system.JS


@pytest.mark.parametrize("code", list(i18n.SUPPORTED))
def test_the_page_script_holds_the_system_views(code: str) -> None:
    page = render_page(code).decode()
    for key in ("more/system", "more/system-update", "more/system-reset", "more/system-details"):
        assert f"DETAIL['{key}']=" in page, key


def test_the_page_script_parses_in_every_language() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    for code in i18n.SUPPORTED:
        script = re.search(r"<script>([\s\S]*)</script>", render_page(code).decode())
        assert script is not None
        result = subprocess.run([node, "--check", "/dev/stdin"], input=script.group(1), capture_output=True, text=True)
        assert result.returncode == 0, (code, result.stderr)


def test_at_most_six_rows_before_the_fold() -> None:
    view = JS.split("DETAIL['more/system']=")[1].split("DETAIL['more/system-update']")[0]
    visible = view.split("add(v,grp(null,")[1].split("moreFold(")[0]
    rows = re.findall(r"\b(?:rowEl|linkRow|swRow|slRow|sgRow)\(", visible)
    assert 1 <= len(rows) <= 6, rows
    assert view.count("moreFold(") == 1


def test_the_support_row_opens_the_sponsor_page_in_a_new_tab() -> None:
    assert "https://github.com/sponsors/JesseWebDotCom" in JS
    assert "target:'_blank',rel:'noopener noreferrer'" in JS


def test_about_goes_to_the_about_page_and_reset_needs_the_typed_word() -> None:
    assert "location.href='/about'" in JS
    assert "word.value!=='RESET'" in JS and "ask(" in JS and "confirm_word:word.value" in JS


def test_the_visible_rows_use_plain_words() -> None:
    view = JS.split("DETAIL['more/system']=")[1].split("DETAIL['more/system-update']")[0]
    visible = view.split("add(v,grp(null,")[1].split("moreFold(")[0].lower()
    for word in ("psk", "token", "namespace", "firmware", "codec", "jitter", "passphrase", "endpoint", "json"):
        assert word not in visible, word
    assert chr(0x2014) not in JS
