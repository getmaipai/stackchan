# ruff: noqa: E501
"""Open items from an independent review. Each test states the behavior the code should have; it fails today and is marked strict xfail
(delete the marker when fixed). One-line owner tags in each docstring."""

from __future__ import annotations

import inspect
import shutil
import subprocess

import pytest
from firmware_order_cores import cores_dir

bug = pytest.mark.xfail(strict=True)
needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")


def _run_c(body: str, tmp_path, tmp_path_factory) -> subprocess.CompletedProcess:
    src = tmp_path / "t.c"
    src.write_text('#include "maipai_lock_core.h"\n#include "maipai_motion_limit_core.h"\n#include <stdlib.h>\nint main(void)\n{\n' + body + "\n}\n")
    out = tmp_path / "t"
    build = subprocess.run(["cc", "-std=gnu99", "-Wall", "-Wextra", f"-I{cores_dir(tmp_path_factory)}", str(src), "-o", str(out), "-lm"], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr[-1500:]
    return subprocess.run([str(out)], capture_output=True, text=True, timeout=60)


@needs_cc
def test_lock_attempt_counter_is_not_reset_by_a_call_that_needs_no_code(tmp_path, tmp_path_factory):
    """owner: firmware (lock tools; the success path of mlk_tool_note)."""
    run = _run_c(
        """
    mlk_t s; mlk_init(&s);
    uint8_t salt[LK_SALT_LEN] = {1};
    if (mlk_set(&s, "1234", "", salt) != MLK_R_OK) return 9;
    uint32_t now = 5000;
    for (int i = 0; i < LK_TOOL_MAX_FAILS - 1; i++) mlk_tool_note(&s, now, mlk_clear(&s, "0000"));
    mlk_tool_note(&s, now, mlk_set_auto_checked(&s, 5, ""));   /* turning the auto lock on takes no code */
    /* one more wrong code must start the lockout */
    mlk_tool_note(&s, now, mlk_clear(&s, "0000"));
    return mlk_tool_open(&s, now + 1) == MLK_R_TOO_MANY ? 0 : 1;
""",
        tmp_path,
        tmp_path_factory,
    )
    assert run.returncode == 0, run.returncode


@needs_cc
def test_keypad_pauses_after_a_run_of_wrong_codes(tmp_path, tmp_path_factory):
    """owner: firmware (lock keypad; docs/user/lock.md says the robot makes you wait after several wrong codes)."""
    run = _run_c(
        """
    mlk_t s; mlk_init(&s);
    uint8_t salt[LK_SALT_LEN] = {1};
    mlk_set(&s, "1234", "", salt);
    uint32_t now = 1000;
    mlk_lock_now(&s, now);
    mlk_screen_touch(&s, now);
    for (int round = 0; round < 12; round++) {
        for (int i = 0; i < 6; i++) { now += 50; mlk_key(&s, '9', now); }
    }
    now += 50;
    return mlk_key(&s, '1', now) == MLK_EV_IGNORED ? 0 : 1;
""",
        tmp_path,
        tmp_path_factory,
    )
    assert run.returncode == 0, run.returncode


@needs_cc
def test_a_tipped_unit_is_noticed_while_the_head_keeps_moving(tmp_path, tmp_path_factory):
    """owner: firmware (SF34 maipai_motion_feed_accel: the hold on pitch motion; a dance or a nod never stops moving the pitch)."""
    run = _run_c(
        """
    mml_t m; mml_init(&m);
    uint32_t now = 10000, moved = 0;
    int pitch10 = 0;
    for (int i = 0; i < 100; i++) { now += 20; mml_orient_feed(&m, now, 0.0f, 9.8f, 0.0f, 0.0f); }   /* upright, still */
    if (mml_orient(&m, now) != MML_O_UPRIGHT) return 9;
    for (int i = 0; i < 400; i++) {                                           /* 8 s on its side, the head nodding every tick */
        now += 20;
        pitch10 = (i & 1) ? 100 : 0;  moved = now;                            /* maipai_motion_note_pitch: the pitch changed just now */
        if (now - moved < 400u && mml_orient_hold(&m, now)) { /* what the glue does: the hold is honored only up to its cap */ }
        else mml_orient_feed(&m, now, 9.8f, 0.0f, 0.0f, pitch10 / 10.0f);
    }
    (void)pitch10;
    return mml_orient(&m, now) == MML_O_SIDE ? 0 : 1;
""",
        tmp_path,
        tmp_path_factory,
    )
    assert run.returncode == 0, run.returncode


def test_forget_of_one_common_word_keeps_notes_that_only_share_it(tmp_path):
    """owner: app (memory_notes/store.py Notes.handle + NotesStore.forget; a spoken "forget it" removes every note that holds the word "it")."""
    from maipai_packages.memory_notes import Notes, NotesStore

    notes = Notes(NotesStore(tmp_path), ["sam"], default_person="sam")
    notes.store.add("sam", "my birthday is in May and I love it")
    notes.store.add("sam", "the garage code lives in the red folder, it is a box")
    notes.store.add("sam", "I take oat milk in my coffee")
    notes.handle("forget it", None)
    assert len(notes.store.read("sam")) >= 2


def test_notes_unlock_state_is_kept_per_unit():
    """owner: app (memory_notes/store.py; one Notes object serves every unit, and handle(text, speaker) has no unit, so a passphrase spoken to one robot opens the notes on every robot)."""
    from maipai_packages.memory_notes import Notes

    params = inspect.signature(Notes.handle).parameters
    assert {"unit", "device_id"} & set(params)


def test_the_settings_page_drops_a_client_that_sends_half_a_request():
    """owner: app (settings_server.py _Handler: no socket timeout, so a stalled client holds a thread for good; the coding companion has one)."""
    from maipai_body.settings_server import _Handler

    assert getattr(_Handler, "timeout", None)


def test_forget_asks_before_removing_more_than_one_note(tmp_path):
    from maipai_packages.memory_notes import Notes, NotesStore

    notes = Notes(NotesStore(tmp_path), ["sam"], default_person="sam")
    notes.store.add("sam", "coffee with oat milk")
    notes.store.add("sam", "coffee beans live in the red tin")
    notes.store.add("sam", "the dentist is on Friday")
    assert "matches 2 notes" in notes.handle("forget coffee", None)
    assert len(notes.store.read("sam")) == 3  # nothing removed yet
    assert notes.handle("no", None) == "Okay, I kept everything."
    assert len(notes.store.read("sam")) == 3
    notes.handle("forget coffee", None)
    assert notes.handle("yes", None).startswith("Done. I forgot 2")
    assert [r[2] for r in notes.store.read("sam")] == ["the dentist is on Friday"]
    assert notes.handle("forget dentist", None).startswith("Done. I forgot 1")  # one match needs no question


def test_forget_with_only_filler_words_is_refused(tmp_path):
    from maipai_packages.memory_notes import Notes, NotesStore

    notes = Notes(NotesStore(tmp_path), ["sam"], default_person="sam")
    notes.store.add("sam", "my birthday is in May")
    for said in ("forget it", "forget that", "forget this one", "forget them"):
        assert "a little more" in notes.handle(said, None), said
    assert len(notes.store.read("sam")) == 1


def test_a_yes_at_another_robot_does_not_confirm_a_forget(tmp_path):
    from maipai_packages.memory_notes import Notes, NotesStore

    notes = Notes(NotesStore(tmp_path), ["sam"], default_person="sam")
    for text in ("coffee one", "coffee two"):
        notes.store.add("sam", text)
    notes.handle("forget coffee", None, unit="a")
    assert notes.handle("yes", None, unit="b") is None  # robot b has nothing waiting: ordinary chat
    assert len(notes.store.read("sam")) == 2


def test_a_passphrase_opens_notes_at_that_robot_only(tmp_path):
    from maipai_packages.memory_notes import Notes, NotesStore

    notes = Notes(NotesStore(tmp_path), ["sam", "lee"], default_person="")
    notes.store.add("sam", "private thing")
    assert notes.passphrases.set("sam", "blue river stone").startswith("Okay")
    assert notes.handle("this is sam, passphrase blue river stone", None, unit="a").startswith("Okay, I will use Sam")
    assert notes.person_for(None, unit="a") == "sam"
    assert notes.person_for(None, unit="b") == ""


def test_notes_rewrite_is_atomic_and_private(tmp_path):
    import os
    import stat

    from maipai_packages.memory_notes import NotesStore

    store = NotesStore(tmp_path)
    store.add("sam", "alpha note here")
    store.add("sam", "beta note here")
    assert store.forget("sam", "alpha") == 1
    path = tmp_path / "sam.md"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert not list(tmp_path.glob("*.tmp"))


def test_passphrase_guesses_at_one_robot_do_not_lock_the_others_and_the_owner_hears(tmp_path):
    from maipai_packages.memory_notes.store import Passphrases

    clock = [0.0]
    p = Passphrases(tmp_path, lambda: clock[0])
    p.set("sam", "blue river stone")
    for _ in range(5):
        assert p.check("sam", "wrong wrong", "kids-room") is False
    assert p.check("sam", "blue river stone", "kids-room") is False  # that robot is locked for ten minutes
    assert p.check("sam", "blue river stone", "kitchen") is True  # the others still work
    assert p.lockouts and p.lockouts[-1]["unit"] == "kids-room" and p.lockouts[-1]["person"] == "sam"
    clock[0] = 601.0
    assert p.check("sam", "blue river stone", "kids-room") is True


def test_token_file_with_open_permissions_is_tightened_on_load(tmp_path):
    import os
    import stat

    from maipai_body.local_guard import SettingsAuth

    path = tmp_path / "token"
    path.write_text("x" * 40 + "\n")
    path.chmod(0o644)
    SettingsAuth(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_a_spray_from_many_addresses_does_not_lock_an_address_that_already_logged_in(tmp_path):
    from maipai_body import local_guard
    from maipai_body.local_guard import SettingsAuth

    auth = SettingsAuth(tmp_path / "token")
    headers = {"Authorization": f"Bearer {auth.token}"}
    assert auth.valid(headers, "", "phone")
    for i in range(local_guard.TOKEN_TRIES_TOTAL + 5):
        auth.valid({"Authorization": "Bearer nope"}, "", f"spray{i}")
    assert auth.valid(headers, "", "phone") is True
    assert auth.valid(headers, "", "stranger") is False  # an address that never logged in is held by the spray lock


def test_the_dashboard_health_tells_the_owner_about_a_passphrase_lockout(tmp_path):
    from maipai_body.health import build_health
    from maipai_packages.memory_notes.store import Passphrases

    p = Passphrases(tmp_path)
    p.set("sam", "blue river stone")
    for _ in range(5):
        p.check("sam", "wrong wrong", "kids-room")
    doc = build_health(None, connected=[], paired={}, started=0.0)
    assert any("Sam" in line and "kids-room" in line for line in doc["advice"])
