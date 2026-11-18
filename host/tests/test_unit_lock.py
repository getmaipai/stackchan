# ruff: noqa: E501
"""The passcode lock, host side: the settings page forwards to the unit and never keeps the code (maipai_body/unit_lock.py)."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import i18n, i18n_lock, settings_ui, unit_lock
from maipai_body.settings_sim import DEN, KITCHEN, build

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
UNIT_URL = "/api/stackchan/unit/{}/{}"
CODE = "590173"
OTHER = "4827"


def get(backend, unit, what, lang="en"):
    status, _, body = backend.route_get(UNIT_URL.format(unit, what), lang, True)
    return status, json.loads(body)


def post(backend, unit, what, body, lang="en"):
    status, payload = backend.route_post(UNIT_URL.format(unit, what), {"lang": lang, **body}, True)
    return status, payload


def lock_calls(unit, tool=None):
    return [
        c for c in unit.calls if c[0].startswith("self.lock.") and (tool is None or c[0] == tool)
    ]


@pytest.fixture
def rig(tmp_path: Path):
    backend, units = build(tmp_path, next_unit=True)
    return backend, units, tmp_path


@pytest.fixture
def old(tmp_path: Path):
    return build(tmp_path)


# ---- the round trip -------------------------------------------------------------------------------------------------


def test_a_new_robot_has_no_code_and_the_status_never_holds_a_code(rig):
    backend, units, _ = rig
    status, view = get(backend, KITCHEN, "lock")
    assert status == 200
    assert view["status"] == "none" and view["has_code"] is False and view["locked"] is False
    assert view["unit_ready"] is True and view["reachable"] is True and view["auto_minutes"] == 0
    assert view["auto_options"] == [0, 1, 15] and view["limits"] == {"min": 4, "max": 6}
    assert not {"code", "hash", "salt", "current"} & set(view)


def test_set_a_code_then_change_needs_the_current_one(rig):
    backend, units, _ = rig
    status, out = post(backend, KITCHEN, "lock", {"code": CODE, "confirm_code": CODE})
    assert status == 200 and out["ok"] is True and "saved" in out["message"]
    assert units[KITCHEN].lock_code == CODE
    assert get(backend, KITCHEN, "lock")[1]["status"] == "unlocked"
    # no current code: the unit says it is needed, the host turns that into a plain sentence
    status, out = post(backend, KITCHEN, "lock", {"code": OTHER, "confirm_code": OTHER})
    assert status == 400 and out["reason"] == "current_needed" and "current code" in out["error"]
    assert units[KITCHEN].lock_code == CODE
    # the wrong current code
    status, out = post(
        backend, KITCHEN, "lock", {"code": OTHER, "confirm_code": OTHER, "current": "111111"}
    )
    assert status == 400 and out["reason"] == "wrong_current" and "not right" in out["error"]
    assert units[KITCHEN].lock_code == CODE
    # the right one
    status, out = post(
        backend, KITCHEN, "lock", {"code": OTHER, "confirm_code": OTHER, "current": CODE}
    )
    assert status == 200 and units[KITCHEN].lock_code == OTHER


def test_remove_the_code_needs_the_current_code(rig):
    backend, units, _ = rig
    post(backend, KITCHEN, "lock", {"code": CODE, "confirm_code": CODE})
    status, out = post(backend, KITCHEN, "lock/clear", {})
    assert (
        status == 400
        and out["reason"] == "current_needed"
        and not lock_calls(units[KITCHEN], "self.lock.clear")
    )
    status, out = post(backend, KITCHEN, "lock/clear", {"current": "222222"})
    assert status == 400 and out["reason"] == "wrong_current" and units[KITCHEN].lock_code == CODE
    status, out = post(backend, KITCHEN, "lock/clear", {"current": CODE})
    assert status == 200 and units[KITCHEN].lock_code is None
    assert get(backend, KITCHEN, "lock")[1]["status"] == "none"
    status, out = post(backend, KITCHEN, "lock/clear", {"current": CODE})
    assert status == 400 and out["reason"] == "no_code" and "no code" in out["error"]


def test_lock_now_needs_a_code_and_then_the_page_shows_locked(rig):
    backend, units, _ = rig
    status, out = post(backend, KITCHEN, "lock/now", {})
    assert status == 400 and out["reason"] == "no_code" and "Set a code first" in out["error"]
    post(backend, KITCHEN, "lock", {"code": CODE, "confirm_code": CODE})
    status, out = post(backend, KITCHEN, "lock/now", {})
    assert status == 200 and units[KITCHEN].locked is True
    view = get(backend, KITCHEN, "lock")[1]
    assert view["status"] == "locked" and view["locked"] is True and view["has_code"] is True


@pytest.mark.parametrize("minutes", [0, 1, 15])
def test_every_auto_lock_choice_reaches_the_unit_and_is_read_back_from_it(rig, minutes):
    backend, units, tmp_path = rig
    status, out = post(backend, KITCHEN, "lock/auto", {"auto_minutes": minutes})
    assert status == 200 and out["auto_minutes"] == minutes
    assert units[KITCHEN].lock_auto == minutes
    assert get(backend, KITCHEN, "lock")[1]["auto_minutes"] == minutes
    assert (
        "lock" not in (tmp_path / "units.json").read_text()
    )  # the host keeps no copy: the unit is the authority


@pytest.mark.parametrize("minutes", [2, -1, 61, "5", True, None, 5.5])
def test_a_choice_outside_the_list_is_refused_before_any_unit_call(rig, minutes):
    backend, units, _ = rig
    status, out = post(backend, KITCHEN, "lock/auto", {"auto_minutes": minutes})
    assert status == 400 and "1, 5, 15, 30 or 60" in out["error"]
    assert not lock_calls(units[KITCHEN], "self.lock.config")


# ---- bad inputs never reach the unit ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "123",
        "1234567",
        "12a4",
        "",
        "   ",
        " 1234",
        "1234 ",
        "12 34",
        "１２３４",
        "12-34",
        1234,
        None,
        ["1234"],
    ],
)
def test_a_bad_code_is_refused_before_any_unit_call(rig, code):
    backend, units, _ = rig
    status, out = post(backend, KITCHEN, "lock", {"code": code, "confirm_code": code})
    assert status == 400 and out["reason"] == "bad_code" and "4 to 6 digits" in out["error"]
    assert not lock_calls(units[KITCHEN], "self.lock.set") and units[KITCHEN].lock_code is None


def test_every_good_length_passes_and_two_different_codes_are_refused(rig):
    backend, units, _ = rig
    for code in ("1234", "12345", "123456"):
        units[KITCHEN].lock_code = None
        assert post(backend, KITCHEN, "lock", {"code": code, "confirm_code": code})[0] == 200
    units[KITCHEN].lock_code = None
    before = len(lock_calls(units[KITCHEN], "self.lock.set"))
    status, out = post(backend, KITCHEN, "lock", {"code": "1234", "confirm_code": "1235"})
    assert status == 400 and "not the same" in out["error"]
    assert len(lock_calls(units[KITCHEN], "self.lock.set")) == before


def test_a_malformed_current_code_is_refused_before_any_unit_call(rig):
    backend, units, _ = rig
    post(backend, KITCHEN, "lock", {"code": CODE, "confirm_code": CODE})
    before = len(lock_calls(units[KITCHEN]))
    assert (
        post(backend, KITCHEN, "lock", {"code": OTHER, "confirm_code": OTHER, "current": "12"})[0]
        == 400
    )
    assert post(backend, KITCHEN, "lock/clear", {"current": "abcd"})[0] == 400
    assert len(lock_calls(units[KITCHEN])) == before


# ---- a locked unit, an absent unit, an old unit -----------------------------------------------------------------------------


def test_a_locked_unit_refuses_set_clear_and_config_and_the_page_says_so(rig):
    backend, units, _ = rig
    post(backend, KITCHEN, "lock", {"code": CODE, "confirm_code": CODE})
    post(backend, KITCHEN, "lock/now", {})
    for what, body in (
        ("lock", {"code": OTHER, "confirm_code": OTHER, "current": CODE}),
        ("lock/clear", {"current": CODE}),
        ("lock/auto", {"auto_minutes": 15}),
    ):
        status, out = post(backend, KITCHEN, what, body)
        assert (
            status == 400
            and out["reason"] == "locked"
            and "robot is locked" in out["error"]
            and "keypad" in out["error"]
        ), what
    assert (
        units[KITCHEN].lock_code == CODE
        and units[KITCHEN].locked is True
        and units[KITCHEN].lock_auto == 0
    )
    assert post(backend, KITCHEN, "lock/now", {})[0] == 200  # locking again is allowed


def test_a_robot_that_is_off_is_reported_and_nothing_is_invented(rig):
    backend, _, _ = rig
    view = get(backend, DEN, "lock")[1]
    assert (
        view["reachable"] is False
        and view["unit_ready"] is False
        and view["has_code"] is None
        and view["locked"] is None
    )
    assert view["status"] == "unknown" and "not connected" in view["message"]
    status, out = post(backend, DEN, "lock", {"code": CODE, "confirm_code": CODE})
    assert status == 400 and out["offline"] is True and "not connected" in out["error"]


def test_a_unit_without_the_lock_tools_says_it_is_coming(old):
    backend, units = old
    view = get(backend, KITCHEN, "lock")[1]
    assert (
        view["unit_ready"] is False
        and view["reachable"] is True
        and "next unit update" in view["message"]
    )
    status, out = post(backend, KITCHEN, "lock", {"code": CODE, "confirm_code": CODE})
    assert status == 400 and out["pending"] is True and "next unit update" in out["error"]


def test_the_unit_tool_call_shapes(rig):
    backend, units, _ = rig
    post(backend, KITCHEN, "lock", {"code": CODE, "confirm_code": CODE})
    post(backend, KITCHEN, "lock", {"code": OTHER, "confirm_code": OTHER, "current": CODE})
    post(backend, KITCHEN, "lock/auto", {"auto_minutes": 15})
    post(backend, KITCHEN, "lock/now", {})
    seen = {name: args for name, args in lock_calls(units[KITCHEN])}
    assert ("self.lock.set", {"code": CODE}) in lock_calls(units[KITCHEN])
    assert ("self.lock.set", {"code": OTHER, "current": CODE}) in lock_calls(units[KITCHEN])
    assert seen["self.lock.config"] == {"auto_minutes": 15} and seen["self.lock.now"] == {}
    assert seen["self.lock.status"] == {}


# ---- the code is never kept ---------------------------------------------------------------------------------------------------


def test_the_code_is_in_no_log_no_response_no_file_and_no_event(rig, caplog):
    backend, units, tmp_path = rig
    caplog.set_level(logging.DEBUG)
    seen: list[str] = []

    def keep(out):
        seen.append(json.dumps(out))
        return out

    keep(post(backend, KITCHEN, "lock", {"code": CODE, "confirm_code": CODE})[1])
    keep(
        post(backend, KITCHEN, "lock", {"code": OTHER, "confirm_code": OTHER})[1]
    )  # refused: current needed
    keep(
        post(backend, KITCHEN, "lock", {"code": OTHER, "confirm_code": OTHER, "current": "111111"})[
            1
        ]
    )  # refused: wrong current
    keep(
        post(backend, KITCHEN, "lock", {"code": "12", "confirm_code": "12"})[1]
    )  # refused: bad code
    keep(
        post(backend, KITCHEN, "lock", {"code": OTHER, "confirm_code": CODE})[1]
    )  # refused: mismatch
    keep(get(backend, KITCHEN, "lock")[1])
    keep(post(backend, KITCHEN, "lock/auto", {"auto_minutes": 15})[1])
    keep(post(backend, KITCHEN, "lock/now", {})[1])
    keep(post(backend, KITCHEN, "lock/clear", {"current": CODE})[1])  # refused: locked
    for lang in ("en", "es"):
        keep(get(backend, KITCHEN, "lock", lang)[1])
        keep(
            post(
                backend,
                KITCHEN,
                "lock",
                {"code": OTHER, "confirm_code": OTHER, "current": CODE},
                lang,
            )[1]
        )
    blob = " ".join(seen) + caplog.text
    for secret in (CODE, OTHER, "111111"):
        assert secret not in blob, secret
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert (
                CODE.encode() not in path.read_bytes() and OTHER.encode() not in path.read_bytes()
            ), path
    assert units[KITCHEN].lock_code == CODE  # only the unit holds it


def test_a_failing_unit_call_never_puts_the_code_in_a_message_or_a_log(tmp_path, caplog):
    from maipai_body.unit_tools import ToolProbe

    def call(name, arguments, *, device_id=None, timeout=5.0):
        if name == "self.lock.status":
            return {"ok": True, "has_code": True, "locked": False, "auto_minutes": 0}
        raise RuntimeError(
            f"link failed while sending {arguments}"
        )  # an exception that carries its arguments

    caplog.set_level(logging.DEBUG)
    service = unit_lock.LockService(ToolProbe(call, tool_list=lambda _d: {"self.lock.status"}))
    out = service.set_code("kitchen", CODE, CODE, "111111", "en")
    out2 = service.clear_code("kitchen", CODE, "es")
    blob = json.dumps([out, out2]) + caplog.text
    assert CODE not in blob and "111111" not in blob
    assert out["ok"] is False and "not connected" in out["error"]


def test_no_sentence_is_built_from_what_was_typed_or_from_the_unit_text(tmp_path):
    from maipai_body.unit_tools import ToolProbe

    def call(name, arguments, *, device_id=None, timeout=5.0):
        if name == "self.lock.status":
            return {"ok": True, "has_code": True, "locked": False, "auto_minutes": 0}
        return {
            "ok": False,
            "reason": f"echo {arguments.get('code')}",
            "error": f"bad {arguments.get('code')}",
        }

    service = unit_lock.LockService(ToolProbe(call, tool_list=lambda _d: {"self.lock.status"}))
    out = service.set_code("kitchen", CODE, CODE, None, "en")
    assert CODE not in json.dumps(out) and out["error"] == unit_lock.SAY["refused"][0]


# ---- the words ------------------------------------------------------------------------------------------------------------------


def test_every_sentence_has_english_and_spanish_and_they_differ():
    for table in (unit_lock.REASONS, unit_lock.SAY):
        for key, (en, es) in table.items():
            assert en and es and en != es, key
            assert chr(8212) not in en + es, key
    for key in unit_lock.REASONS:
        assert unit_lock.reason_text("en", key) == unit_lock.REASONS[key][0]
        assert unit_lock.reason_text("es-MX", key) == unit_lock.REASONS[key][1]
    assert unit_lock.reason_text("en", "an unknown word") == unit_lock.SAY["refused"][0]


def test_the_spanish_page_words_cover_every_english_key():
    assert set(i18n_lock.EN) == set(i18n_lock.ES)
    js = settings_ui.JS
    keys = set(re.findall(r"T\('(lk\.[a-z_.]+)'\)", js)) | set(
        re.findall(r"lkNum\('(lk\.[a-z_.]+)'", js)
    )
    keys |= {f"lk.status.{s}" for s in ("none", "unlocked", "locked", "unknown")}
    assert keys <= set(i18n_lock.EN)
    for code in ("en", "es"):
        for key in sorted(i18n_lock.EN):
            assert i18n.CATALOG[code].get("settings.ui." + key), (code, key)
    for key in i18n_lock.EN:
        if key not in {"lk.minutes"}:
            assert i18n_lock.EN[key] != i18n_lock.ES[key], key
    text = " ".join(list(i18n_lock.EN.values()) + list(i18n_lock.ES.values()))
    assert chr(8212) not in text
    assert not re.search(r"\b(col" r"our|cen" r"tre|behav" r"iour)\w*", text, re.I)


# ---- the page script ------------------------------------------------------------------------------------------------------------------


def test_the_security_section_is_in_the_page_and_the_code_stays_out_of_urls_storage_and_the_console():
    js = settings_ui.JS
    assert "BUILDERS.security" in js and "'security'" in js and "lockCard" in js
    mine = js[js.index("security: the passcode lock") :]
    assert (
        "type:'password'" in mine
        and "inputmode:'numeric'" in mine
        and "maxlength:6" in mine
        and "autocomplete:'off'" in mine
    )
    for banned in (
        "console.",
        "localStorage",
        "sessionStorage",
        "lsSet",
        "location",
        "history.",
        "document.cookie",
        "?code",
        "+a.value",
        "+cur.value",
    ):
        assert banned not in mine, banned
    assert (
        mine.count("f.value=''") == 1 and "finally" in mine
    )  # every field is cleared after every request, whatever the answer
    assert (
        "unitPath(id,'lock')" in mine
        and "send('lock/now'" in mine
        and "send('lock/clear'" in mine
        and "send('lock/auto'" in mine
    )


def test_the_page_script_parses():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    out = HERE / ".unit_lock_script.js"
    out.write_text(settings_ui.JS)
    try:
        run = subprocess.run([node, "--check", str(out)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
    finally:
        out.unlink(missing_ok=True)


# ---- the parity tables ------------------------------------------------------------------------------------------------------------------


def test_the_parity_table_is_what_the_unit_is_told_to_answer():
    assert unit_lock.TABLE == {
        "code_min": 4,
        "code_max": 6,
        "auto_minutes": [0, 1, 15],
        "reasons": [
            "bad_code",
            "bad_minutes",
            "current_needed",
            "locked",
            "no_code",
            "wrong_current",
        ],
        "tools": [
            "self.lock.status",
            "self.lock.set",
            "self.lock.clear",
            "self.lock.now",
            "self.lock.config",
        ],
    }
    assert unit_lock.AUTO_MINUTES == (0, 1, 15)


def test_the_unit_firmware_agrees_when_its_lock_core_is_in_the_tree():
    """The firmware core is written by another change: when its files exist they must carry the same tools, reasons and limits."""
    texts = [
        p.read_text(errors="ignore")
        for p in (ROOT / "firmware").rglob("*")
        if p.is_file() and p.suffix in {".h", ".c", ".cc", ".cpp", ".patch"}
    ]
    texts = [t for t in texts if "self.lock." in t or "MLK_REASONS" in t]  # the tools are in the unit patch, the reasons in the core patch
    if not texts:
        pytest.skip("the unit's lock core is not in the tree yet")
    text = "\n".join(texts)
    for tool in unit_lock.TABLE["tools"]:
        assert tool in text, tool
    for reason in unit_lock.TABLE["reasons"]:
        assert reason in text, reason
    for minutes in unit_lock.AUTO_MINUTES:
        assert re.search(rf"\b{minutes}\b", text), minutes
