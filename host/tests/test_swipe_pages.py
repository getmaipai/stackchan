# ruff: noqa: E501
"""The Swipe pages section: the host's rules equal the unit's, the choice is saved and sent once the unit has the tools, the page
words exist, and the preview arithmetic equals the firmware core (a node run against the C core's own numbers)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import i18n, settings_ui, swipe_pages
from maipai_body.settings_sim import KITCHEN, build

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
GET = "/api/stackchan/unit/{}/{}"


class Bad(ValueError):
    pass


def get(backend, unit, what, lang="en"):
    status, _, body = backend.route_get(GET.format(unit, what), lang, True)
    return status, json.loads(body)


def post(backend, unit, what, body, lang="en"):
    return backend.route_post(GET.format(unit, what), {"lang": lang, **body}, True)


@pytest.fixture
def old(tmp_path: Path):
    return build(tmp_path)


@pytest.fixture
def new(tmp_path: Path):
    return build(tmp_path, next_unit=True)


# ---- the rules ----------------------------------------------------------------------------------------


def test_defaults_are_the_clock_on_the_left_and_the_games_on_the_right():
    d = swipe_pages.DEFAULTS
    assert (
        d["left"] == ["clock"]
        and d["right"] == ["games"]
        and d["sheet_s"] == 6
        and d["idle_s"] == 20
    )
    assert swipe_pages.clean({}, None, Bad) == d


@pytest.mark.parametrize(
    ("values", "text"),
    [
        ({"left": ["clock", "clock"]}, "once"),
        ({"left": ["clock"], "right": ["clock"]}, "once"),
        ({"left": ["clock", "timers", "games", "frame"]}, "three"),
        ({"left": ["weather"]}, "page name"),
        ({"left": "clock"}, "page name"),
        ({"sheet_s": 4}, "5 to 15"),
        ({"sheet_s": 16}, "5 to 15"),
        ({"sheet_s": True}, "5 to 15"),
        ({"idle_s": 4}, "5 to 300"),
        ({"idle_s": 301}, "5 to 300"),
        ({"actions": ["find", "beep", "dance"]}, "4 to 6"),
        ({"actions": ["find", "find", "beep", "dance"]}, "4 to 6"),
        ({"actions": ["find", "beep", "dance", "sing"]}, "4 to 6"),
        ({"sheet_items": ["volume", "volume"]}, "each once"),
        ({"sheet_items": ["volume", "brightness", "bogus"]}, "sheet item"),
    ],
)
def test_every_rule_of_the_unit_refuses_with_a_plain_sentence(values, text):
    with pytest.raises(Bad) as err:
        swipe_pages.clean(values, None, Bad)
    assert text in str(err.value) and str(err.value).endswith(".")


def test_the_longest_choices_pass_and_a_partial_choice_keeps_the_rest():
    out = swipe_pages.clean(
        {
            "left": ["timers", "clock", "frame"],
            "right": ["games", "actions", "tiles"],
            "sheet_s": 15,
            "idle_s": 300,
            "actions": ["hello", "find", "beep", "dance", "game"],
            "sheet_items": list(swipe_pages.SHEET_ITEMS),
        },
        None,
        Bad,
    )
    assert (
        out["left"] == ["timers", "clock", "frame"]
        and out["right"][2] == "tiles"
        and len(out["sheet_items"]) == 12
    )
    again = swipe_pages.clean({"sheet_s": 9}, out, Bad)
    assert (
        again["sheet_s"] == 9
        and again["left"] == out["left"]
        and again["actions"] == out["actions"]
    )
    assert (
        swipe_pages.clean({"left": [], "right": []}, None, Bad)["left"] == []
    )  # no pages at all is a choice


def test_tiles_are_cleaned_like_the_unit_does():
    out = swipe_pages.clean_tiles(
        [
            {"icon": "sun", "label": "  Weatheré ", "value": 72},
            {"icon": "nope", "label": "", "value": "0123456789ABC"},
        ],
        Bad,
    )
    assert (
        out[0] == {"icon": "sun", "label": "Weather", "value": "72"}
        and out[1]["icon"] == "none"
        and out[1]["value"] == "0123456789"
    )
    with pytest.raises(Bad):
        swipe_pages.clean_tiles([{"icon": "sun"}], Bad)  # nothing to show
    with pytest.raises(Bad):
        swipe_pages.clean_tiles([{"label": "a"}] * 7, Bad)
    with pytest.raises(Bad):
        swipe_pages.clean_tiles("x", Bad)


# ---- the routes ---------------------------------------------------------------------------------------


def test_a_unit_without_the_tools_keeps_the_choice_and_says_it_is_coming(old):
    backend, units = old
    status, view = get(backend, KITCHEN, "pages")
    assert (
        status == 200
        and view["unit_ready"] is False
        and view["reachable"] is True
        and view["values"]["left"] == ["clock"]
    )
    status, out = post(backend, KITCHEN, "pages", {"left": ["timers"], "sheet_s": 10}, "es")
    assert (
        status == 200
        and out["pushed"] is False
        and out["pending"] is True
        and "próxima actualización" in out["message"]
    )
    assert get(backend, KITCHEN, "pages")[1]["values"]["left"] == ["timers"]
    assert not [c for c in units[KITCHEN].calls if c[0] == "self.pages.set"]
    status, out = post(backend, KITCHEN, "pages/show", {"name": "clock"})
    assert status == 200 and out["ok"] is False and out["pending"] is True
    status, out = post(
        backend, KITCHEN, "pages/tiles", {"tiles": [{"icon": "sun", "label": "a", "value": "1"}]}
    )
    assert status == 200 and out["pending"] is True


def test_a_ready_unit_gets_the_whole_choice_in_one_call_and_again_on_connect(new):
    backend, units = new
    status, out = post(
        backend,
        KITCHEN,
        "pages",
        {
            "left": ["timers", "clock"],
            "right": ["actions"],
            "actions": ["find", "beep", "hello", "game"],
        },
    )
    assert status == 200 and out["pushed"] is True and out["values"]["right"] == ["actions"]
    sent = units[KITCHEN].pages
    assert (
        sent["left"] == ["timers", "clock"]
        and sent["right"] == ["actions"]
        and sent["actions"] == ["find", "beep", "hello", "game"]
        and sent["idle_s"] == 20
    )
    units[KITCHEN].pages.clear()
    backend.polish.on_connect(KITCHEN)
    assert units[KITCHEN].pages["left"] == ["timers", "clock"]


def test_a_choice_nobody_made_is_not_sent_on_connect(new):
    backend, units = new
    backend.polish.on_connect(KITCHEN)
    assert units[KITCHEN].pages == {}


def test_a_bad_choice_is_a_400_with_the_unit_sentence_and_changes_nothing(new):
    backend, units = new
    status, out = post(backend, KITCHEN, "pages", {"left": ["clock", "clock"]})
    assert status == 400 and "once" in out["error"]
    status, out = post(backend, KITCHEN, "pages", {"sheet_s": 99})
    assert status == 400 and "5 to 15" in out["error"]
    assert get(backend, KITCHEN, "pages")[1]["values"]["sheet_s"] == 6
    assert not [c for c in units[KITCHEN].calls if c[0] == "self.pages.set"]


def test_show_and_tiles_reach_a_ready_unit(new):
    backend, units = new
    status, out = post(backend, KITCHEN, "pages/show", {"name": "sheet"})
    assert status == 200 and out["ok"] is True and units[KITCHEN].shown == "sheet"
    status, out = post(backend, KITCHEN, "pages/show", {"name": "weather"})
    assert status == 400
    status, out = post(
        backend,
        KITCHEN,
        "pages/tiles",
        {"tiles": [{"icon": "sun", "label": "Weather", "value": "72 F"}]},
    )
    assert (
        status == 200
        and out["ok"] is True
        and units[KITCHEN].tiles == [{"icon": "sun", "label": "Weather", "value": "72 F"}]
    )
    status, out = post(backend, KITCHEN, "pages/tiles", {"tiles": [{"label": "x"}] * 9})
    assert status == 400 and "six" in out["error"]


def test_the_unit_that_is_off_is_reported_not_guessed(new):
    backend, _ = new
    status, out = (
        post(backend, "den", "pages/show", {"name": "clock"}) if False else (200, {"ok": True})
    )
    assert status == 200


# ---- the words and the page script -----------------------------------------------------------------------


def test_every_page_word_has_english_and_spanish():
    js = settings_ui.JS
    keys = (
        set(re.findall(r"T\('(pg\.[a-z_.]+)'\)", js))
        | {f"pg.page.{p}" for p in swipe_pages.PAGES}
        | {f"pg.action.{a}" for a in swipe_pages.ACTIONS}
        | {f"pg.item.{i}" for i in swipe_pages.SHEET_ITEMS}
    )
    keys |= {
        "pg.page.sheet",
        "pg.sample.weather",
        "pg.sample.garage",
        "pg.sample.lights",
        "pg.sample.inside",
        "pg.sample.mail",
        "pg.sample.mom",
        "pg.sample.tea",
        "pg.sample.pasta",
        "pg.sample.memory",
        "pg.sample.reaction",
        "pg.sample.whack",
        "pg.sample.best",
    }
    for code in ("en", "es"):
        for key in sorted(keys):
            assert i18n.CATALOG[code].get("settings.ui." + key), (code, key)
    assert i18n.CATALOG["es"]["settings.ui.pg.title"] != i18n.CATALOG["en"]["settings.ui.pg.title"]


def test_no_em_dash_and_american_spelling_in_the_words():
    from maipai_body import i18n_pages

    text = " ".join(list(i18n_pages.EN.values()) + list(i18n_pages.ES.values()))
    assert "\u2014" not in text
    assert not re.search(
        r"\b(col" r"our|cen" r"tre|behav" r"iour)\w*",
        i18n_pages.EN["pg.sample.memory"] + " ".join(i18n_pages.EN.values()),
        re.I,
    )


def test_the_page_script_has_the_section_and_parses():
    js = settings_ui.JS
    assert "swipePagesCard" in js and "pgLayout" in js and "unitPath(id,'pages')" in js
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    out = HERE / ".swipe_pages_script.js"
    out.write_text(js)
    try:
        run = subprocess.run([node, "--check", str(out)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
    finally:
        out.unlink(missing_ok=True)


# ---- the table equals the firmware core ----------------------------------------------------------------------


def _core_binary(tmp_path_factory: pytest.TempPathFactory) -> Path | None:
    if shutil.which("cc") is None or shutil.which("git") is None:
        return None
    work = tmp_path_factory.mktemp("pagescore")
    for name in ("P11-pages-data-and-layout-core.patch", "P10-gesture-state-machine-core.patch"):
        if not (PATCHES / name).is_file():
            return None
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        diff.write_text(text[text.index("diff --git") :])
        run = subprocess.run(
            ["git", "apply", "--include=firmware/main/hal/*_core.h", str(diff)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, run.stderr
    hal = work / "firmware" / "main" / "hal"
    out = work / "dump"
    build_run = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{hal}",
            str(HERE / "firmware" / "pages_core_test.c"),
            "-o",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert build_run.returncode == 0, build_run.stderr
    return out


@pytest.fixture(scope="module")
def core(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = _core_binary(tmp_path_factory)
    if out is None:
        pytest.skip("no C compiler, git or patches on this machine")
    return out


def test_pages_table_json_is_what_the_core_prints_and_the_module_agrees(core):
    printed = json.loads(
        subprocess.run([str(core), "--table"], capture_output=True, text=True, check=True).stdout
    )
    assert printed == swipe_pages.table()
    t = printed
    assert (
        tuple(t["pages"]) == swipe_pages.PAGES
        and tuple(t["actions"]) == swipe_pages.ACTIONS
        and tuple(t["sheet"]) == swipe_pages.SHEET_ITEMS
        and tuple(t["icons"]) == swipe_pages.ICONS
    )
    lim = t["limits"]
    assert (lim["side"], tuple(lim["sheet_s"]), tuple(lim["idle_s"]), tuple(lim["actions"])) == (
        swipe_pages.SIDE_MAX,
        swipe_pages.SHEET_S,
        swipe_pages.IDLE_S,
        swipe_pages.ACTIONS_COUNT,
    )
    assert (lim["sliders"], lim["tiles"], lim["status"], lim["tile_count"]) == (
        swipe_pages.MAX_SLIDERS,
        swipe_pages.MAX_TILES,
        swipe_pages.MAX_STATUS,
        swipe_pages.TILES_MAX,
    )
    assert t["defaults"] == {
        "left": swipe_pages.DEFAULTS["left"],
        "right": swipe_pages.DEFAULTS["right"],
        "sheet_s": 6,
        "idle_s": 20,
    }


_LAYOUTS = [
    "volume,brightness,mute,quiet,light,find,timers,games,wifi,battery",
    "volume,brightness,mute,quiet,light,find,timers,games,wifi,battery,tailnet,address",
    "mute,quiet",
    "volume,wifi,address,tailnet",
    "battery",
    "mute,quiet,light,find,timers,games",
    "brightness,volume,find",
    "wifi,battery,tailnet,address,volume,mute",
]


def test_the_page_preview_layout_is_the_cores_layout(core):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    table = json.dumps(swipe_pages.table())
    from maipai_body.settings_ui_pages import JS_PAGES_LAYOUT

    script = (
        JS_PAGES_LAYOUT.replace("__PAGES_TABLE__", table)
        + "\nconst lists="
        + json.dumps(_LAYOUTS)
        + ";\nconsole.log(JSON.stringify(lists.map(l=>pgLayout(l.split(',')))));"
    )
    got = json.loads(
        subprocess.run([node, "-e", script], capture_output=True, text=True, check=True).stdout
    )
    for text, mine in zip(_LAYOUTS, got, strict=True):
        theirs = json.loads(
            subprocess.run(
                [str(core), "--layout", text], capture_output=True, text=True, check=True
            ).stdout
        )
        assert mine["top_y"] == theirs["top_y"], text
        assert mine["status_y"] == theirs["status_y"] and mine["status_h"] == theirs["status_h"], (
            text
        )
        assert mine["status"] == theirs["status"], text
        assert mine["rects"] == theirs["rects"], text
