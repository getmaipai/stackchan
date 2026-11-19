# ruff: noqa: E501
"""The Voice and listening page in the dashboard look: its view is in the script, the script parses in every language, and the rows stay few."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from maipai_body import i18n, settings_ui_p_voice
from maipai_body.settings_page import render_page


def _block(js: str, key: str) -> str:
    start = js.index(f"DETAIL['{key}']=")
    nxt = js.find("\nDETAIL[", start + 1)
    return js[start : nxt if nxt != -1 else len(js)]


def test_the_page_script_has_the_voice_views() -> None:
    page = render_page("en").decode()
    for key in ("robot/voice", "robot/voice-more", "robot/wakeword"):
        assert f"DETAIL['{key}']=" in page


def test_the_script_parses_in_every_language() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    for code in i18n.SUPPORTED:
        page = render_page(code).decode()
        script = re.search(r"<script>([\s\S]*)</script>", page)
        assert script is not None
        result = subprocess.run([node, "--check", "/dev/stdin"], input=script.group(1), capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def test_at_most_six_rows_before_the_fold_and_one_fold() -> None:
    for key in ("robot/voice", "robot/wakeword"):
        block = _block(settings_ui_p_voice.JS, key)
        assert block.count("moreFold(") == 1
        main = block[block.index("add(v,grp(null,") : block.index("moreFold(")]
        rows = len(re.findall(r"\b(?:slRow|sgRow|swRow|rowEl)\(", main))
        assert 1 <= rows <= 6, (key, rows)


def test_every_word_the_voice_page_asks_for_exists() -> None:
    asked = set(re.findall(r"\bT\('([a-z0-9_]+\.[a-z0-9_.]+)'\)", settings_ui_p_voice.JS))
    assert asked
    for code in i18n.SUPPORTED:
        for key in asked:
            assert f"settings.ui.{key}" in i18n.CATALOG[code], (code, key)


def test_the_page_uses_the_old_save_calls() -> None:
    js = settings_ui_p_voice.JS
    for name in ("speech_speed", "wait_after_talking", "ignore_noise", "screen_lang", "speech_pitch", "volume_cap"):
        assert name in js
