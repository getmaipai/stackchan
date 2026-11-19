# ruff: noqa: E501
"""The Games page in the new dashboard look: its script is in the page, parses in every language, and keeps to six rows."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from maipai_body import i18n
from maipai_body.settings_page import render_page
from maipai_body.settings_ui_p_games import JS

KEYS = ("more/games", "more/games-scores", "more/games-talk", "more/games-content")


def test_the_page_script_holds_every_games_view() -> None:
    page = render_page("en").decode()
    for key in KEYS:
        assert f"DETAIL['{key}']=" in page
    assert page.index("DETAIL['more/games']=async v=>{add(v,...detailHead(T('Games')") > page.index("'more/games':legacyView")


def test_the_script_parses_in_every_language() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    for code in i18n.SUPPORTED:
        script = re.search(r"<script>([\s\S]*)</script>", render_page(code).decode())
        assert script is not None
        result = subprocess.run([node, "--check", "/dev/stdin"], input=script.group(1), capture_output=True, text=True)
        assert result.returncode == 0, (code, result.stderr)


def _view(key: str) -> str:
    start = JS.index(f"DETAIL['{key}']=")
    end = JS.find("\nDETAIL[", start + 1)
    return JS[start : end if end > 0 else len(JS)]


def test_the_front_view_has_at_most_six_rows_before_the_fold() -> None:
    body = _view("more/games")
    before_fold = body[: body.index("moreFold(")]
    assert len(re.findall(r"rowEl\(|swRow\(|slRow\(|sgRow\(", before_fold)) <= 6
    assert "delete scores" in body.lower() and "ask(" in body
    assert body.count("moreFold(") == 1


def test_the_content_view_keeps_the_old_calls() -> None:
    body = _view("more/games-content")
    for call in ("/api/stackchan/pantry/list", "/api/stackchan/pantry/refill", "/api/stackchan/pantry/delete", "/api/stackchan/pantry/never-again"):
        assert call in body
    before_fold = body[: body.index("moreFold(")]
    assert len(re.findall(r"rowEl\(", before_fold.split("const load")[0] + before_fold.split("const refill")[1])) <= 6


def test_no_em_dash_and_no_banned_word_on_the_visible_labels() -> None:
    assert chr(0x2014) not in JS
    labels = re.findall(r"label:T\('([^']+)'\)", JS)
    assert labels
    for label in labels:
        assert 1 <= len(label.split()) <= 5, label
        assert not re.search(r"\b(psk|token|namespace|firmware|codec|jitter|passphrase|endpoint|json)\b", label, re.I)
