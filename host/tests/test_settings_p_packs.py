# ruff: noqa: E501
"""The Packs page in the new dashboard look (brief api36): its views exist, the page script parses in every language,
the front view has at most six rows before the fold, and every call the views make is answered by the stand-in."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import i18n
from maipai_body.settings_page import render_page
from maipai_body.settings_sim import KITCHEN, build
from maipai_body.settings_ui_p_packs import JS

KEYS = ("more/packs", "more/packs-languages", "more/packs-look", "more/packs-pictures", "more/packs-character", "more/packs-sounds", "more/packs-installed")
EM = chr(0x2014)


def _front_view() -> str:
    start = JS.index("DETAIL['more/packs']=")
    return JS[start : JS.index("DETAIL['more/packs-languages']")]


@pytest.mark.parametrize("code", list(i18n.SUPPORTED))
def test_the_page_script_holds_every_packs_view_and_parses(code: str) -> None:
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


def test_the_front_view_has_six_rows_and_one_fold() -> None:
    front = _front_view()
    before_fold = front[: front.index("moreFold(")]
    assert before_fold.count("rowEl(") == 6
    assert front.count("moreFold(") == 1
    for label in ("Languages", "Look packs", "Pictures", "Character pack", "Sounds", "Installed on the robot"):
        assert f"T('{label}')" in before_fold
    for key in KEYS[1:]:
        assert f"nav('more','{key.split('/')[1]}')" in before_fold


def test_the_file_has_no_em_dash_and_no_disabled_rows() -> None:
    assert EM not in JS
    assert "disabled:" not in JS.replace("b.disabled", "")


def test_every_call_the_views_make_is_answered_by_the_stand_in(tmp_path: Path) -> None:
    backend, _ = build(tmp_path)
    get = lambda path: backend.route_get(path, "en", True)  # noqa: E731
    unit = f"/api/stackchan/unit/{KITCHEN}/"
    for path in ("/api/stackchan/packs", unit + "packs", unit + "pictures", unit + "phrases", f"/api/stackchan/faces/{KITCHEN}"):
        assert get(path)[0] == 200, path
    assert "screen-words" in " ".join(str(p) for p in __import__("json").loads(get("/api/stackchan/packs")[2])["packs"])
    for what in ("pictures/send", "pictures/clear"):
        assert backend.route_post(unit + what, {"lang": "en"}, True)[0] in (200, 400), what
    status, _payload = backend.route_post(unit + "packs/activate", {"lang": "en", "type": "look", "pack_id": ""}, True)
    assert status == 200
    status, _payload = backend.route_post(f"/api/stackchan/faces/{KITCHEN}", {"lang": "en", "screen_lang": "en"}, True)
    assert status == 200
    status, _payload = backend.route_post(unit + "packs/sync", {"lang": "en"}, True)
    assert status == 200
