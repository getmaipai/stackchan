"""The Network page in the new dashboard look (settings_ui_p_network.py)."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from maipai_body import i18n
from maipai_body.settings_page import render_page
from maipai_body.settings_ui_p_network import JS

KEYS = ("more/network", "more/network-away", "more/network-robots")


def _script(code: str) -> str:
    match = re.search(r"<script>([\s\S]*)</script>", render_page(code).decode())
    assert match is not None
    return match.group(1)


def _view(key: str) -> str:
    start = JS.index(f"DETAIL['{key}']")
    nxt = JS.find("DETAIL['", start + 10)
    return JS[start : nxt if nxt > 0 else len(JS)]


@pytest.mark.parametrize("code", list(i18n.SUPPORTED))
def test_the_page_script_has_the_network_views_and_parses(code: str) -> None:
    script = _script(code)
    for key in KEYS:
        assert f"DETAIL['{key}']" in script
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run([node, "--check", "/dev/stdin"], input=script, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_at_most_six_rows_before_the_fold() -> None:
    for key in KEYS:
        body = _view(key)
        front = body.split("moreFold(")[0]
        rows = len(re.findall(r"\browEl\(|\bswRow\(|\bslRow\(|\bsgRow\(", front))
        assert rows <= 6, (key, rows)
    assert _view("more/network").count("moreFold(") == 1


def test_the_visible_rows_use_plain_words() -> None:
    away = _view("more/network-away").split("moreFold(")[0]
    labels = re.findall(r"label:T\('([^']+)'\)", away)
    assert "1. Get an access code" in labels
    for text in labels:
        assert not re.search(r"\b(key|token|psk|passphrase|endpoint|json)\b", text, re.I), text
    assert "\u2014" not in JS
