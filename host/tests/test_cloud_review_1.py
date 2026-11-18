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
@bug
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
@bug
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
        if (now - moved < 400u) mml_orient_hold(&m, now);                    /* what the glue does */
        else mml_orient_feed(&m, now, 9.8f, 0.0f, 0.0f, pitch10 / 10.0f);
    }
    (void)pitch10;
    return mml_orient(&m, now) == MML_O_SIDE ? 0 : 1;
""",
        tmp_path,
        tmp_path_factory,
    )
    assert run.returncode == 0, run.returncode


@bug
def test_forget_of_one_common_word_keeps_notes_that_only_share_it(tmp_path):
    """owner: app (memory_notes/store.py Notes.handle + NotesStore.forget; a spoken "forget it" removes every note that holds the word "it")."""
    from maipai_packages.memory_notes import Notes, NotesStore

    notes = Notes(NotesStore(tmp_path), ["sam"], default_person="sam")
    notes.store.add("sam", "my birthday is in May and I love it")
    notes.store.add("sam", "the garage code lives in the red folder, it is a box")
    notes.store.add("sam", "I take oat milk in my coffee")
    notes.handle("forget it", None)
    assert len(notes.store.read("sam")) >= 2


@bug
def test_notes_unlock_state_is_kept_per_unit():
    """owner: app (memory_notes/store.py; one Notes object serves every unit, and handle(text, speaker) has no unit, so a passphrase spoken to one robot opens the notes on every robot)."""
    from maipai_packages.memory_notes import Notes

    params = inspect.signature(Notes.handle).parameters
    assert {"unit", "device_id"} & set(params)


@bug
def test_the_settings_page_drops_a_client_that_sends_half_a_request():
    """owner: app (settings_server.py _Handler: no socket timeout, so a stalled client holds a thread for good; the coding companion has one)."""
    from maipai_body.settings_server import _Handler

    assert getattr(_Handler, "timeout", None)
