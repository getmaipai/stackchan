# ruff: noqa: E501
"""The Remote control and Remote access pages in the new dashboard look (settings_ui_p_remote.py)."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from maipai_body import i18n, settings_ui_p_remote
from maipai_body.settings_page import render_page

JS = settings_ui_p_remote.JS
KEYS = ("robot/remote", "safety/access", "robot/remote-head", "robot/remote-overlays", "safety/controllers", "safety/activity")


def _args(src: str, start: int) -> list[str]:
    """The top-level arguments of the call whose opening parenthesis is at ``start``."""
    depth, args, cur, quote, i = 0, [], "", "", start
    while i < len(src):
        c = src[i]
        if quote:
            cur += c
            if c == "\\":
                cur += src[i + 1]
                i += 1
            elif c == quote:
                quote = ""
        elif c in "'\"`":
            quote = c
            cur += c
        elif c in "([{":
            depth += 1
            if depth > 1:
                cur += c
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                args.append(cur)
                return [a.strip() for a in args if a.strip()]
            cur += c
        elif c == "," and depth == 1:
            args.append(cur)
            cur = ""
        else:
            cur += c
        i += 1
    raise AssertionError("unbalanced call")


def _body(key: str) -> str:
    start = JS.index(f"DETAIL['{key}']=")
    nxt = JS.find("\nDETAIL['", start + 10)
    return JS[start : nxt if nxt > 0 else len(JS)]


@pytest.mark.parametrize("code", list(i18n.SUPPORTED))
def test_the_page_script_has_the_keys_and_parses(code: str) -> None:
    page = render_page(code).decode()
    script = re.search(r"<script>([\s\S]*)</script>", page)
    assert script is not None
    for key in KEYS:
        assert f"DETAIL['{key}']=" in script.group(1), key
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run([node, "--check", "/dev/stdin"], input=script.group(1), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_at_most_six_rows_before_the_fold() -> None:
    for key in ("robot/remote", "safety/access"):
        body = _body(key)
        first = body.index("grp(null,")
        rows = _args(body, first + len("grp"))[1:]
        assert 1 <= len(rows) <= 6, (key, len(rows))
        assert body.count("moreFold(") == 1, key
        last = _args(body, body.rindex("add(v,") + len("add"))
        assert last[-1] == "fold" or last[-1].startswith("moreFold("), key


def test_the_remote_rows_are_in_the_asked_order() -> None:
    body = _body("robot/remote")
    rows = _args(body, body.index("grp(null,") + len("grp"))[1:]
    assert rows == ["sayRow", "lookRow", "danceRow", "picRow", "findRow", "muteRow"]
    for word in ("rem.say", "rem.look", "rem.dance", "rem.photo", "rem.find", "rem.mute"):
        assert f"T('{word}')" in body, word


def test_the_page_makes_the_old_calls_and_no_new_endpoint() -> None:
    for call in ("do:'say'", "'look']", "'nod']", "'shake']", "do:k", "do:'dance'", "do:'stop_dance'", "do:'photo'", "do:'find'", "do:'mute'", "do:'game'", "do:'overlay'", "do:'head'", "do:'center'"):
        assert call in JS, call
    paths = set(re.findall(r"'(/api/[^']*)'", JS))
    assert paths == {"/api/stackchan/remote-access"}
    assert "ACC+'/allow'" in JS and "ACC+'/revoke'" in JS


def test_the_visible_labels_avoid_the_banned_words() -> None:
    from maipai_body.settings_ui_shell import BANNED

    for key in ("robot/remote", "safety/access"):
        body = _body(key)
        head = body[: body.index("moreFold(")]
        for word in BANNED:
            assert word not in head.lower(), (key, word)
    assert "\u2014" not in JS
