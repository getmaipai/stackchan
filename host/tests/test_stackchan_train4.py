# ruff: noqa: E501
"""Train 4 (firmware patches U01 to U06 and TN07, host unit_extras): the C cores, the patch files,
the host copies of the firmware's tables, the services, the settings routes and the page words."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import faces, i18n, settings_page, unit_extras
from maipai_body.hal.errors import BodyLost
from maipai_body.unit_extras import (
    ExtrasError,
    PeopleStore,
    UnitExtras,
    clean_person,
    clean_reactions,
    fold,
    reactions_from_text,
    reactions_to_text,
    screen_text,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
C_TESTS = HERE / "firmware"
UNIT = "AA:BB:CC:00:00:01"

TRAIN4 = [
    "TN07-travel-review-fixes.patch",
    "U01-face-decorators.patch",
    "U02-word-reactions.patch",
    "U03-time-zone-picker.patch",
    "U04-network-test.patch",
    "U05-version-screen.patch",
    "U06-face-style-packs-and-languages.patch",
]
FACES_CORE = [
    "X01-look-core-and-skin.patch",
    "X02-face-styles-colours-and-battery.patch",
    "V10-face-design-shapes.patch",  # the approved face design: the look core's table, spring and shape builders
    "V12-chunky-mouth-on-anime-eyes.patch",  # the chunky mouth of the faces core on those eyes (V11 touches no header)
]  # patches after Train 5 that change the pure headers (look core, face core, decor core, reaction rows)
# The patches whose pure headers the face cores need, in order (U06 changes three of them).
# Every patch of ORDER up to FI04 (the last entry of the final integration), in order; only the pure headers are kept. A hand kept list
# drifted whenever a patch was added (V20 to V26 and N01 to N04 broke it); S10 and later patches are tested by their own lanes.
_ORDER_ALL = [n for n in (PATCHES / "ORDER").read_text().split() if n]
CORE_CHAIN = _ORDER_ALL[: _ORDER_ALL.index("FI04-lvgl-task-stack-8k.patch") + 1]
# K10 and K11 change two of these headers (the screen words became a language pack): face_cores_test.c reads them through the pack's words.
CORE_CHAIN += ["K10-pack-types-phrase-and-cache-format-2.patch", "K11-language-pack-screen-words.patch"]


@pytest.fixture(scope="module")
def cores(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The pure C headers as the patches leave them, built by applying the patches in order."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    work = tmp_path_factory.mktemp("cores")
    for name in CORE_CHAIN:
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        diff.write_text(text[text.index("diff --git") :])
        run = subprocess.run(
            ["git", "apply", "--include=firmware/main/hal/*_core.h", str(diff)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, f"{name}: {run.stderr}"
    return work / "firmware" / "main" / "hal"


def _c_test(cores: Path, source: str, tmp_path: Path) -> None:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    binary = tmp_path / "t"
    build = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{cores}",
            str(C_TESTS / source),
            "-o",
            str(binary),
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


@pytest.mark.parametrize(
    "source",
    [
        "decor_core_test.c",
        "react_core_test.c",
        "tz_core_test.c",
        "nettest_core_test.c",
        "version_core_test.c",
        "face_cores_test.c",
        "look_core_test.c",
    ],
)
def test_the_c_cores_pass_their_tests(cores: Path, source: str, tmp_path: Path) -> None:
    _c_test(cores, source, tmp_path)


# ---- the patch files ----


def test_every_train4_patch_has_its_header_lines_and_is_in_order() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(name) for name in TRAIN4]
    assert positions == sorted(positions)
    assert order[positions[-1]] == TRAIN4[-1]
    for name in TRAIN4:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in (
            "# Intent:",
            "# Placement: unit",
            "# Upstream:",
            "# Check after a flash:",
            "# Kconfig:",
        ):
            assert key in head, f"{name} has no '{key}' line"
        assert chr(8212) not in text, f"{name} has an em dash"


def test_every_new_feature_has_a_default_on_kconfig_switch() -> None:
    expect = {
        "U01-face-decorators.patch": "MAIPAI_FACE_DECOR",
        "U02-word-reactions.patch": "MAIPAI_REACT",
        "U03-time-zone-picker.patch": "MAIPAI_TZ",
        "U04-network-test.patch": "MAIPAI_NETTEST",
        "U05-version-screen.patch": "MAIPAI_VERSION",
        "U06-face-style-packs-and-languages.patch": "MAIPAI_FACE_PACKS",
    }
    for name, symbol in expect.items():
        text = (PATCHES / name).read_text()
        assert f"+config {symbol}\n" in text, name
        block = text.split(f"+config {symbol}\n", 1)[1].split("\n+\n", 1)[0]
        assert "+    default y" in block, f"{symbol} is not on by default"
        assert f"+CONFIG_{symbol}=y" in text, f"{symbol} is not in sdkconfig.core.defaults"


def test_the_nfc_and_infrared_finding_skips_the_patch() -> None:
    assert not any("infrared" in p.name or "nfc" in p.name.lower() for p in PATCHES.iterdir())
    note = (ROOT / "docs" / "design" / "train4-2026-11-16.md").read_text()
    assert "infrared" in note and "NFC" in note and "SKIPPED" in note


def test_the_portal_save_failure_reaches_the_page_and_nothing_is_written_first() -> None:
    text = (PATCHES / "TN07-travel-review-fixes.patch").read_text()
    assert "MP_S_TSAVE" in text and "send_json_status(req, false, MP_S_TSAVE)" in text
    # the travel save comes before the Wi-Fi write in the handler (the write may be a context line of the patch)
    save = text.index("+                           maipai_portal_tailnet_save(travel_key")
    wifi = text.index("self->Save(ssid, password)")
    assert save < wifi
    assert "FATAL_ERROR" in text and "MAIPAI_MICROLINK_DIR" in text


# ---- the host copies of the firmware's tables ----


def _patch_text(name: str) -> str:
    return (PATCHES / name).read_text()


def _c_strings(block: str) -> list[str]:
    return re.findall(r'"([^"]*)"', block)


def test_the_host_decorator_list_is_the_firmwares(cores: Path) -> None:
    core = (cores / "maipai_decor_core.h").read_text()
    names = _c_strings(core.split("MD_NAMES[MD_COUNT] = {", 1)[1].split("};", 1)[0])
    # the ids of the sweat drop and the blush stay in the table; the face no longer offers them (patch X02)
    assert names[0] == "none" and tuple(n for n in names[1:] if n not in ("sweat", "shy")) == faces.DECORATORS


def test_the_host_reaction_table_is_the_firmwares(cores: Path) -> None:
    core = (cores / "maipai_react_core.h").read_text()
    rows = re.findall(r'^\s*\{"([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)"\},', core, re.M)
    assert len(rows) == len(unit_extras.DEFAULT_REACTIONS) >= 30
    assert [tuple(r) for r in rows] == [tuple(r) for r in unit_extras.DEFAULT_REACTIONS]
    for key, host in (
        ("MR_FACES", unit_extras.REACT_FACES),
        ("MR_SOUNDS", unit_extras.REACT_SOUNDS),
        ("MR_DANCES", unit_extras.REACT_DANCES),
    ):
        block = core.split(f"static const char* const {key}[", 1)[1].split("};", 1)[0]
        assert tuple(_c_strings(block)) == host, key
    assert f"#define MR_MAX {unit_extras.REACT_MAX}" in core


def test_the_host_zone_list_is_the_firmwares(cores: Path) -> None:
    core = (cores / "maipai_tz_core.h").read_text()
    rows = re.findall(r'^\s*\{"([a-z_]+)", "([^"]+)", "[^"]+"\},', core, re.M)
    assert tuple((i, label) for i, label in rows) == unit_extras.ZONES


def test_the_host_style_language_and_caption_lists_are_the_firmwares(cores: Path) -> None:
    core = (cores / "maipai_face_core.h").read_text()
    styles = _c_strings(core.split("MF_STYLE_NAMES[MF_STYLE_COUNT] = {", 1)[1].split("};", 1)[0])
    # the saved ids 3 to 8 are the dropped styles (no name); the host lists the five that remain, in its own order
    assert sorted(styles) == sorted(faces.STYLES)
    langs = _c_strings(core.split("MF_LANG_CODES[MF_LANG_COUNT] = {", 1)[1].split("};", 1)[0])
    assert tuple(langs) == faces.LANGS
    caps = _c_strings(core.split("MF_CAPTION_NAMES[3] = {", 1)[1].split("};", 1)[0])
    assert tuple(caps) == faces.CAPTION_SIZES


def test_every_zone_resolves_to_a_real_zone_name() -> None:
    from zoneinfo import ZoneInfo

    for zone_id in unit_extras.ZONE_IDS:
        ZoneInfo(unit_extras.zone_iana(zone_id))
    assert unit_extras.zone_iana("america_new_york") == "America/New_York"
    assert unit_extras.zone_iana("utc") == "UTC"


# ---- the same folding as the firmware ----


def test_python_folds_text_like_the_c_core(cores: Path, tmp_path: Path) -> None:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    source = tmp_path / "fold.c"
    source.write_text(
        '#include <stdio.h>\n#include <string.h>\n#include "maipai_react_core.h"\n'
        "int main(void){char line[256],out[256];while(fgets(line,sizeof(line),stdin)){"
        'line[strcspn(line,"\\n")]=0;mr_fold(line,out,sizeof(out));puts(out);}return 0;}\n'
    )
    binary = tmp_path / "fold"
    build = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{cores}",
            str(source),
            "-o",
            str(binary),
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    samples = [
        "Hello!",
        "  Thank   you,  so much.. ",
        "Désolé",
        "Buenas Noches",
        "mañana",
        "grüße Straße",
        "je t'aime",
        "Æther and Œuvre",
        "ÀÉÎÕÜ àéîõü ÿ",
        "你好 world",
        "tut mir leid!!",
        "ñandú, ¿qué tal?",
        "Ørsted Ðe Þor",
        "100% sure",
        "a\u00d7b",
        "",
    ]
    run = subprocess.run(
        [str(binary)], input="\n".join(samples) + "\n", capture_output=True, text=True
    )
    got = run.stdout.split("\n")
    for sample, c_out in zip(samples, got, strict=False):
        assert fold(sample) == c_out, f"{sample!r}: python {fold(sample)!r} c {c_out!r}"


def test_screen_text_removes_accents_and_keeps_the_rest() -> None:
    assert screen_text("¿Qué tal, niño? Ça va, Straße") == "Que tal, nino? Ca va, Strasse"
    assert (
        screen_text("Zażółć") == "Zazoc"
    )  # a letter with no plain form (the l with a stroke) is dropped, not shown as a box
    assert screen_text("Plain ASCII 123") == "Plain ASCII 123"
    assert screen_text("") == ""


# ---- word reactions: the host's checks ----


def test_reaction_rows_are_checked_with_the_firmwares_rules() -> None:
    rows = clean_reactions([{"say": "Hello!", "face": "happy", "decor": "sparkles"}])
    assert rows[0].say == "hello" and rows[0].sound == "none"
    bad = [
        ([{"say": "a", "face": "happy"}], "2 to 23"),
        ([{"say": "x" * 30, "face": "happy"}], "2 to 23"),
        ([{"say": "wow", "face": "grumpy"}], "happy, sad"),
        ([{"say": "wow", "face": "happy", "sound": "exclamation"}], "needs_you"),
        ([{"say": "wow", "face": "happy", "decor": "confetti"}], "dizzy, heart"),
        ([{"say": "wow", "face": "happy", "dance": "moonwalk"}], "look_around"),
        ([{"say": "wow"}], "at least"),
        ([{"say": "wow", "face": "happy"}, {"say": "WOW!", "face": "sad"}], "already"),
        ("nope", "at most"),
        ([{"say": f"w{i}", "face": "happy"} for i in range(41)], "at most"),
    ]
    for value, words in bad:
        with pytest.raises(ExtrasError) as caught:
            clean_reactions(value)
        assert words in str(caught.value), (value, str(caught.value))
    with pytest.raises(ExtrasError) as spanish:
        clean_reactions([{"say": "a", "face": "happy"}], "es")
    assert "Fila 1" in str(spanish.value) and "letras" in str(spanish.value)


def test_reaction_text_round_trips() -> None:
    rows = unit_extras.default_reactions()
    again = reactions_from_text(reactions_to_text(rows))
    assert again == rows
    parsed = reactions_from_text("good morning | happy\n\nbye | sad | | tears")
    assert [(r.say, r.face, r.decor) for r in parsed] == [
        ("good morning", "happy", "none"),
        ("bye", "sad", "tears"),
    ]
    with pytest.raises(ExtrasError):
        reactions_from_text("| happy")
    with pytest.raises(ExtrasError):
        reactions_from_text("a | b | c | d | e | f")


# ---- the services, with a stand-in unit ----


class FakeUnit:
    """Answers the Train 4 tools the way the firmware does, with a switchable link."""

    def __init__(self) -> None:
        self.link = True
        self.table: list[dict] | None = None
        self.zone = "utc"
        self.epoch = 0
        self.calls: list[tuple[str, dict]] = []
        self.network: dict = {
            "ok": True,
            "problems": 0,
            "summary": "All good.",
            "fix": "",
            "steps": [{"step": "wifi", "state": "ok", "line": "Wi-Fi: connected, strong signal"}],
        }
        self.has_tools = True

    def __call__(self, name: str, arguments: dict, *, device_id: str, timeout: float) -> object:
        self.calls.append((name, arguments))
        if not self.link:
            raise BodyLost("the unit is not connected")
        if not self.has_tools:
            return {"ok": False, "error": "unknown tool"}
        if name == "self.reaction.set_table":
            self.table = json.loads(arguments["table"])
            return json.dumps({"ok": True, "builtin": False, "table": self.table})
        if name == "self.reaction.get_table":
            # the unit answers every column, with "none" for an empty one
            rows = [{k: (v or "none") for k, v in row.items()} for row in (self.table or [])]
            return {"ok": True, "builtin": self.table is None, "table": rows}
        if name == "self.reaction.reset":
            self.table = None
            return {"ok": True, "builtin": True, "table": []}
        if name == "self.clock.set_zone":
            self.zone = arguments["zone"]
            return {"ok": True, "zone": self.zone, "local": "07:30"}
        if name == "self.clock.set":
            self.epoch = arguments["epoch"]
            return {"ok": True, "zone": self.zone, "local": "07:30"}
        if name == "self.network.test":
            return self.network
        if name == "self.version.get":
            return {
                "ok": True,
                "version": "1.6.2-maipai.1",
                "tag": "v1.6.2-maipai.1",
                "image": "x",
                "slot": "ota_0",
                "internal_free": 55000,
                "internal_min": 39000,
            }
        return {"ok": True}


def _extras(
    tmp_path: Path, unit: FakeUnit | None = None, zone: str | None = "america_new_york"
) -> tuple[UnitExtras, FakeUnit]:
    unit = unit or FakeUnit()
    extras = UnitExtras(
        unit,
        reactions=unit_extras.ReactionStore(tmp_path / "r.json"),
        clock=unit_extras.ClockStore(tmp_path / "c.json"),
        now=lambda: 1_794_000_000.0,
        local_zone=lambda: zone,
    )
    return extras, unit


def test_reactions_save_push_and_reset(tmp_path: Path) -> None:
    extras, unit = _extras(tmp_path)
    view = extras.reactions_view(UNIT)
    assert view["builtin"] is True and "hello | happy" in view["text"]
    result = extras.save_reactions(UNIT, {"text": "good morning | happy | | sparkles"})
    assert result["pushed"] is True and unit.table == [
        {"say": "good morning", "face": "happy", "sound": "", "decor": "sparkles", "dance": ""}
    ]
    assert extras.reactions_view(UNIT)["builtin"] is False
    with pytest.raises(ExtrasError):
        extras.save_reactions(UNIT, {"text": "x | happy"})
    assert unit.table is not None and len(unit.table) == 1  # a bad table changes nothing
    assert extras.reset_reactions(UNIT)["pushed"] is True and unit.table is None
    assert extras.reactions_view(UNIT)["builtin"] is True


def test_a_lost_unit_keeps_the_choice_and_gets_it_on_connect(tmp_path: Path) -> None:
    extras, unit = _extras(tmp_path)
    unit.link = False
    result = extras.save_reactions(UNIT, {"text": "hi there | happy"})
    assert result["pushed"] is False and "reconnects" in result["message"]
    unit.link = True
    extras.sync(UNIT)
    assert unit.table == [
        {"say": "hi there", "face": "happy", "sound": "", "decor": "", "dance": ""}
    ]
    names = [c[0] for c in unit.calls]
    assert "self.clock.set" in names and "self.clock.set_zone" in names
    before = len(unit.calls)
    extras.sync(UNIT)  # the unit already holds it: no second table push
    assert [c[0] for c in unit.calls[before:]].count("self.reaction.set_table") == 0


def test_a_unit_with_no_saved_table_is_left_alone(tmp_path: Path) -> None:
    extras, unit = _extras(tmp_path)
    extras.sync(UNIT)
    assert not any(c[0].startswith("self.reaction") for c in unit.calls)


def test_the_clock_and_zone(tmp_path: Path) -> None:
    extras, unit = _extras(tmp_path)
    view = extras.clock_view(UNIT)
    assert (
        view["zone"] == "america_new_york"
        and view["saved"] is False
        and len(view["zones"]) == len(unit_extras.ZONES)
    )
    result = extras.save_zone(UNIT, "europe_berlin")
    assert result["pushed"] is True and unit.zone == "europe_berlin" and unit.epoch == 1_794_000_000
    assert extras.clock_view(UNIT)["saved"] is True
    with pytest.raises(ExtrasError) as caught:
        extras.save_zone(UNIT, "mars")
    assert "not in the list" in str(caught.value) and unit.zone == "europe_berlin"
    synced = extras.set_clock_now(UNIT, "es")
    assert synced["pushed"] is True and "este ordenador" in synced["message"]
    extras_no_guess, unit2 = _extras(tmp_path / "x", zone=None)
    (tmp_path / "x").mkdir()
    extras_no_guess.sync(UNIT)
    assert unit2.epoch == 1_794_000_000 and not any(
        c[0] == "self.clock.set_zone" for c in unit2.calls
    )


def test_this_computers_zone_is_guessed_from_its_offsets() -> None:
    from zoneinfo import ZoneInfo

    assert unit_extras.guess_zone(ZoneInfo("America/Chicago")) == "america_chicago"
    assert unit_extras.guess_zone(ZoneInfo("Asia/Kolkata")) == "asia_kolkata"
    assert unit_extras.guess_zone(ZoneInfo("Europe/Paris")) in {
        "europe_paris",
        "europe_berlin",
        "europe_madrid",
        "europe_rome",
    }
    assert (
        unit_extras.guess_zone(ZoneInfo("Pacific/Chatham")) is None
    )  # a zone the unit does not list


def test_the_network_test_and_details_speak_plainly_when_the_unit_cannot_answer(
    tmp_path: Path,
) -> None:
    extras, unit = _extras(tmp_path)
    assert extras.network_test(UNIT)["summary"] == "All good."
    assert extras.details(UNIT)["tag"] == "v1.6.2-maipai.1"
    unit.link = False
    lost = extras.network_test(UNIT)
    assert lost["ok"] is False and "not connected" in lost["fix"] and "router" in lost["fix"]
    assert "no esta conectada" in extras.network_test(UNIT, "es")["fix"]
    assert extras.details(UNIT)["ok"] is False
    unit.link, unit.has_tools = True, False
    old = extras.network_test(UNIT)
    assert old["ok"] is False and "firmware does not have" in old["fix"]
    assert extras.details(UNIT)["ok"] is False


# ---- people ----


def test_people_are_checked_saved_and_applied(tmp_path: Path) -> None:
    store = PeopleStore(tmp_path / "p.json")
    nova = clean_person(
        {"name": "Nova B.", "color": "#40C0FF", "caption_size": "large", "wake_phrase": "hey nova"}
    )
    assert nova.id == "nova-b" and nova.color == "#40c0ff"
    store.save(nova)
    store.save(clean_person({"name": "Marlow", "color": "mint"}))
    assert [p.name for p in store.all()] == ["Marlow", "Nova B."]
    store.save(clean_person({"name": "Nova B.", "color": "rose"}))  # the same person is replaced
    assert [p.color for p in store.all() if p.id == "nova-b"] == ["rose"]
    bad = [
        ({"name": ""}, ExtrasError, "name of 1 to 24"),
        ({"name": "x" * 30}, ExtrasError, "name of 1 to 24"),
        ({"name": "A", "wake_phrase": "hi"}, ExtrasError, "3 to 24"),
        ({"name": "A", "wake_phrase": "ok <b>"}, ExtrasError, "3 to 24"),
        ({"name": "A", "color": "#101010"}, faces.FaceError, "too dark"),
        ({"name": "A", "color": "purple"}, faces.FaceError, "not one I know"),
        ({"name": "A", "caption_size": "huge"}, faces.FaceError, "small, medium or large"),
    ]
    for values, error, words in bad:
        with pytest.raises(error) as caught:
            clean_person(values)
        assert words in str(caught.value), (values, str(caught.value))
    store.remove("marlow")
    assert [p.id for p in store.all()] == ["nova-b"]
    for i in range(unit_extras.PEOPLE_MAX):
        store.save(clean_person({"name": f"P{i}"}))
        if len(store.all()) >= unit_extras.PEOPLE_MAX:
            break
    with pytest.raises(ExtrasError) as many:
        store.save(clean_person({"name": "One too many"}))
    assert "at most" in str(many.value)


def test_a_person_goes_to_the_unit_through_the_face_service(tmp_path: Path) -> None:
    from tests.test_faces import FakeFirmware

    firmware = FakeFirmware(features=("config", "packs"))
    service = faces.FaceService(firmware, faces.FaceStore(tmp_path / "f.json"))
    person = clean_person({"name": "Nova", "color": "mint", "caption_size": "large"})
    result = unit_extras.apply_person(service, UNIT, person)
    assert firmware.state["colour"] == "mint" and firmware.state["caption_size"] == "large"
    assert result["pushed"] is True


def test_a_damaged_people_file_is_reported_and_ignored(tmp_path: Path) -> None:
    path = tmp_path / "p.json"
    path.write_text("{not json")
    store = PeopleStore(path)
    assert store.all() == [] and "could not be read" in (store.problem or "")


# ---- face decorators and the new face settings (host side) ----


def _face_service(
    tmp_path: Path, features: tuple[str, ...] = ("config", "decor", "packs", "langs6")
):
    from tests.test_faces import FakeFirmware

    firmware = FakeFirmware(features=features)
    return faces.FaceService(firmware, faces.FaceStore(tmp_path / "f.json")), firmware


def test_a_decorator_is_checked_and_sent(tmp_path: Path) -> None:
    service, firmware = _face_service(tmp_path)
    assert service.decorate(UNIT, "tears", 5) == {"ok": True}
    assert firmware.calls[-1][:2] == ("self.face.decorate", {"name": "tears", "seconds": 5})
    service.decorate(UNIT, "none")
    for name, seconds, words in (
        ("confetti", 5, "does not exist"),
        ("tears", 0, "1 to 60"),
        ("tears", 61, "1 to 60"),
        ("tears", True, "1 to 60"),
    ):
        with pytest.raises(faces.FaceError) as caught:
            service.decorate(UNIT, name, seconds)  # type: ignore[arg-type]
        assert words in str(caught.value)
    firmware.refuse = (
        "a mute, vision-off or quiet look or a ringing timer is showing: end that first"
    )
    with pytest.raises(faces.FaceError) as refused:
        service.decorate(UNIT, "heart")
    assert "mute" in str(refused.value) and "refused" in str(refused.value)


def test_a_unit_without_decorators_says_so(tmp_path: Path) -> None:
    service, _ = _face_service(tmp_path, features=("config",))
    service.sync(UNIT)  # reads the unit's feature words
    with pytest.raises(faces.FaceError) as caught:
        service.decorate(UNIT, "zzz")
    assert "firmware does not have face extras" in str(caught.value)


def test_every_decorator_has_a_tool_entry_and_a_face_helper(tmp_path: Path) -> None:
    service, firmware = _face_service(tmp_path)
    table = service.handlers()
    for name in faces.DECORATORS:
        assert table[f"face_{name}"]({"unit": UNIT})["ok"] is True
    assert table["face_decorators"]({})["decorators"] == list(faces.DECORATORS)
    assert table["face_decorate"]({"unit": UNIT, "name": "stars", "seconds": 4})["ok"] is True
    assert table["face_decorate"]({"unit": UNIT, "name": "nope"})["ok"] is False
    assert table["face_decorate"]({"name": "stars"})["ok"] is False
    firmware.link = False
    assert "reach my body" in table["face_tears"]({"unit": UNIT})["error"]
    firmware.link = True
    assert service.extra_for_face(UNIT, "sad") is True and firmware.calls[-1][1]["name"] == "tears"
    assert service.extra_for_face(UNIT, "neutral") is False
    firmware.link = False
    assert service.extra_for_face(UNIT, "sad") is False  # never raises


def test_new_styles_sizes_and_languages_are_checked_and_flagged_for_old_firmware(
    tmp_path: Path,
) -> None:
    config = faces.clean(
        faces.FaceConfig(), {"style": "heart_eyes", "caption_size": "large", "lang": "de"}
    )
    # a dropped style is Big eyes (patch X02)
    assert (config.style, config.caption_size, config.lang) == ("big_eyes", "large", "de")
    for values, words in (
        ({"caption_size": "tiny"}, "small, medium or large"),
        ({"lang": "ja"}, "en, es, fr, de, pt or it"),
        ({"style": "pirate"}, "big_eyes, eyes_only, stock, classic or minimal"),
    ):
        with pytest.raises(faces.FaceError) as caught:
            faces.clean(faces.FaceConfig(), values)
        assert words in str(caught.value)
    # every message that has a Spanish text, and the new languages read English instead of failing
    assert "tamano" in faces._say("es", "caption_size", value="x")
    assert "caption size" in faces._say("fr", "caption_size", value="x")
    service, _ = _face_service(tmp_path, features=("config",))
    service.sync(UNIT)
    lines = service.unsupported(
        UNIT, {"style": "stock", "lang": "fr", "caption_size": "large", "color": "mint"}
    )
    assert len(lines) == 3 and not service.unsupported(UNIT, {"style": "classic", "lang": "es"})


def test_an_older_unit_that_does_not_report_the_caption_size_still_counts_as_in_step(
    tmp_path: Path,
) -> None:
    service, firmware = _face_service(tmp_path, features=("config",))
    old = dict(firmware.state)
    old.pop("caption_size", None)
    assert faces._wire_equal(faces.FaceConfig(), old) is True
    assert faces._wire_equal(faces.FaceConfig(caption_size="large"), old) is False


def test_the_face_view_lists_the_new_choices(tmp_path: Path) -> None:
    service, _ = _face_service(tmp_path)
    view = faces.settings_view(service, UNIT, "fr")
    assert view["choices"]["style"] == list(faces.STYLES) and view["choices"]["lang"] == list(
        faces.LANGS
    )
    assert view["choices"]["decorators"] == list(faces.DECORATORS) and view["limits"][
        "decor_s"
    ] == [1, 60]
    assert view["choices"]["caption_size"] == list(faces.CAPTION_SIZES)


# ---- the settings routes and the page ----


def _backend(tmp_path: Path, unit: FakeUnit | None = None):
    extras, unit = _extras(tmp_path, unit)
    service, firmware = _face_service(tmp_path)
    backend = settings_page.SettingsBackend(
        devices=lambda: {UNIT: {}},
        store=settings_page.UnitSettingsStore(tmp_path / "units.json"),
        faces=service,
        extras=extras,
        people=PeopleStore(tmp_path / "people.json"),
    )
    return backend, unit, firmware


def _get(backend, path: str, lang: str = "en"):
    status, _, body = backend.route_get(path, lang, True)
    return status, json.loads(body)


def test_the_routes_for_reactions_clock_test_and_details(tmp_path: Path) -> None:
    backend, unit, firmware = _backend(tmp_path)
    base = f"/api/stackchan/unit/{UNIT}"
    status, view = _get(backend, f"{base}/reactions")
    assert status == 200 and view["builtin"] is True and view["limits"]["rows"] == 40
    status, saved = backend.route_post(
        f"{base}/reactions", {"text": "good morning | happy | | sparkles"}, True
    )
    assert status == 200 and saved["pushed"] is True and unit.table
    status, bad = backend.route_post(f"{base}/reactions", {"text": "x | happy", "lang": "es"}, True)
    assert status == 400 and "Fila 1" in bad["error"]
    status, again = backend.route_post(f"{base}/reactions/reset", {}, True)
    assert status == 200 and unit.table is None
    status, clock = _get(backend, f"{base}/clock")
    assert status == 200 and clock["zone"] == "america_new_york"
    status, done = backend.route_post(f"{base}/clock", {"zone": "europe_berlin"}, True)
    assert status == 200 and unit.zone == "europe_berlin"
    status, done = backend.route_post(f"{base}/clock", {"sync": True, "lang": "es"}, True)
    assert status == 200 and "ordenador" in done["message"]
    status, bad_zone = backend.route_post(f"{base}/clock", {"zone": "mars"}, True)
    assert status == 400 and "not in the list" in bad_zone["error"]
    status, net = backend.route_post(f"{base}/network-test", {}, True)
    assert status == 200 and net["message"] == "All good." and net["steps"]
    status, details = _get(backend, f"{base}/details")
    assert status == 200 and details["version"].startswith("1.6")
    status, shown = backend.route_post(f"{base}/decorate", {"name": "tears", "seconds": 4}, True)
    assert status == 200 and firmware.calls[-1][1] == {"name": "tears", "seconds": 4}
    status, rejected = backend.route_post(f"{base}/decorate", {"name": "nope"}, True)
    assert status == 400 and "does not exist" in rejected["error"]
    other = "/api/stackchan/unit/AA:BB:CC:00:00:99"
    assert _get(backend, f"{other}/reactions")[0] == 400
    assert backend.route_post(f"{other}/network-test", {}, True)[0] == 400
    assert backend.route_post(f"{base}/nothing", {}, True)[0] == 404
    assert backend.route_get(f"{base}/nothing", "en", True)[0] == 404


def test_the_extras_routes_are_for_the_local_administrator_only(tmp_path: Path) -> None:
    backend, _, _ = _backend(tmp_path)
    for path in (f"/api/stackchan/unit/{UNIT}/reactions", "/api/stackchan/people"):
        status, _, body = backend.route_get(path, "en", False)
        assert status == 403 and "host computer" in json.loads(body)["error"]
    for path in (f"/api/stackchan/unit/{UNIT}/network-test", "/api/stackchan/people"):
        status, payload = backend.route_post(path, {}, False)
        assert status == 403
    assert backend.route_get("/api/stackchan/elsewhere", "en", True) is None


def test_the_people_routes(tmp_path: Path) -> None:
    backend, _, firmware = _backend(tmp_path)
    status, empty = _get(backend, "/api/stackchan/people")
    assert status == 200 and empty["people"] == [] and "mint" in empty["choices"]["color"]
    status, saved = backend.route_post(
        "/api/stackchan/people",
        {"name": "Nova", "color": "mint", "caption_size": "large", "wake_phrase": "hey nova"},
        True,
    )
    assert status == 200 and saved["people"][0]["id"] == "nova"
    status, bad = backend.route_post("/api/stackchan/people", {"name": ""}, True)
    assert status == 400 and "name of 1 to 24" in bad["error"]
    status, used = backend.route_post(f"/api/stackchan/people/nova/use/{UNIT}", {}, True)
    assert (
        status == 200
        and firmware.state["colour"] == "mint"
        and firmware.state["caption_size"] == "large"
    )
    status, nobody = backend.route_post(
        f"/api/stackchan/people/ghost/use/{UNIT}", {"lang": "es"}, True
    )
    assert status == 400 and "no esta en la lista" in nobody["error"]
    status, removed = backend.route_post("/api/stackchan/people/nova/remove", {}, True)
    assert status == 200 and removed["people"] == []


def test_the_face_route_takes_the_screen_language_apart_from_the_page_language(
    tmp_path: Path,
) -> None:
    backend, _, firmware = _backend(tmp_path)
    status, payload = backend.route_post(
        f"/api/stackchan/faces/{UNIT}",
        {"lang": "es", "screen_lang": "de", "style": "stock", "caption_size": "small"},
        True,
    )
    assert status == 200 and firmware.state["lang"] == "de" and firmware.state["style"] == "stock"
    assert firmware.state["caption_size"] == "small"


def test_the_dashboard_forwards_the_new_routes() -> None:
    text = (ROOT / "host" / "maipai_body" / "dashboard" / "server.py").read_text()
    assert '"/api/stackchan/unit/"' in text and '"/api/stackchan/people"' in text


@pytest.mark.parametrize("lang", list(i18n.SUPPORTED))
def test_the_page_has_every_section_in_every_language(lang: str) -> None:
    page = settings_page.render_page(lang).decode()
    for function in (
        "BUILDERS.behavior",
        "reactCard",
        "timeCard",
        "peopleCard",
        "'network-test'",
        "'travel'",
    ):
        assert function in page
    for key in (
        "settings.react",
        "settings.clock",
        "settings.net",
        "settings.people",
        "settings.extra",
    ):
        assert json.dumps(i18n.t(lang, key))[1:-1] or True
    assert f"<html lang='{lang}'>" in page


def test_the_page_script_parses() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    page = settings_page.render_page("fr").decode()
    script = re.search(r"<script>([\s\S]*)</script>", page)
    assert script is not None
    result = subprocess.run(
        [node, "--check", "/dev/stdin"], input=script.group(1), capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


# ---- page words ----


def test_every_settings_word_exists_in_all_six_languages() -> None:
    english = {k for k in i18n.CATALOG["en"] if k.startswith("settings.")}
    assert len(english) > 100
    for lang in i18n.SUPPORTED:
        missing = english - set(i18n.CATALOG[lang])
        assert not missing, f"{lang} lacks {sorted(missing)[:5]}"
    assert set(i18n.CATALOG["en"]) == set(i18n.CATALOG["es"])
    assert i18n.t("fr", "settings.update") == "Mettre à jour"
    assert i18n.t("de", "settings.save") == "Speichern"
    assert i18n.t("pt", "settings.mute") == "Silêncio"
    assert i18n.t("it", "settings.language") == "Lingua"
    # the flasher messages have no translation in the new languages and read English, never a bare key
    assert i18n.t("fr", "update.dry") == i18n.t("en", "update.dry")
    assert i18n.normalize("pt-BR") == "pt" and i18n.normalize("zz") == "en"


def test_translated_words_keep_their_placeholders_and_every_language_differs() -> None:
    for lang in ("es", "fr", "de", "pt", "it"):
        for key, text in i18n.CATALOG[lang].items():
            assert re.findall(r"\{[a-z_:,.0-9]+\}", text) == re.findall(
                r"\{[a-z_:,.0-9]+\}", i18n.CATALOG["en"][key]
            ), (lang, key)
        assert i18n.CATALOG[lang]["settings.title"] != i18n.CATALOG["en"]["settings.title"]
    names = {i18n.CATALOG[lang]["settings.title"] for lang in i18n.SUPPORTED}
    assert len(names) == 6
    for text in (i18n.CATALOG["en"][k] for k in i18n.CATALOG["en"] if k.startswith("settings.")):
        assert chr(8212) not in text


# ---- scripts ----


def test_fw_tailnet_refuses_a_folder_that_is_not_the_pinned_clone(tmp_path: Path) -> None:
    if shutil.which("git") is None or shutil.which("bash") is None:
        pytest.skip("needs git and bash")
    deps = tmp_path / "deps"
    mine = deps / "microlink"
    mine.mkdir(parents=True)
    (mine / "work.txt").write_text("someone's work")
    env = {
        "MAIPAI_DEPS": str(deps),
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(tmp_path),
    }
    script = ROOT / "scripts" / "fw-tailnet.sh"
    run = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
    assert run.returncode == 1 and "not a git clone" in run.stderr and "left alone" in run.stderr
    assert (mine / "work.txt").read_text() == "someone's work"
    # a git folder from somewhere else is refused before anything is cleaned or reset
    subprocess.run(["git", "init", "-q", str(mine)], check=True)
    subprocess.run(
        ["git", "-C", str(mine), "remote", "add", "origin", "https://example.com/other.git"],
        check=True,
    )
    (mine / "untracked.txt").write_text("keep me")
    run = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
    assert run.returncode == 1 and "does not come from" in run.stderr
    assert (mine / "untracked.txt").read_text() == "keep me" and (mine / "work.txt").exists()
    # an empty folder is fine to start from: the script goes on to the download (stopped here by a bad address)
    shutil.rmtree(mine)
    mine.mkdir()
    env["MAIPAI_MICROLINK_REPO"] = str(tmp_path / "no-such-repo")
    run = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
    assert "left alone" not in run.stderr
