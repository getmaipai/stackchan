# ruff: noqa: E501
"""Open bugs found by reading the app and firmware tracks' code as a tester (playground report 4, 2026-11-18).

Each test states the behavior the code should have and fails today. They are marked strict xfail so the suite stays green;
`pytest --runxfail tests/test_cross_review_open_bugs.py` shows every one failing. When an owner fixes a bug, the test turns into
an unexpected pass and fails the run: delete its marker (the test then stays as the regression test). Nothing here fixes code."""

from __future__ import annotations

import shutil
import socket
import subprocess
import threading

import pytest
from firmware_order_cores import cores_dir

from maipai_packages.coding_companion.hook import send as hook_send
from maipai_packages.coding_companion.server import make_presenter
from maipai_packages.coding_companion.state import AgentStatus
from maipai_packages.home_assistant import HomeAssistant
from maipai_packages.memory_notes.admission import AdmissionError, check_note
from maipai_packages.memory_notes.store import NotesStore

bug = pytest.mark.xfail(strict=True)


# ---- memory_notes (app track) -------------------------------------------------------------------------------

@bug
def test_forget_matches_whole_words_not_pieces_of_words(tmp_path):
    """Owner: app track. `forget cat` also removes a note about a "location" because "cat" sits inside it (substring match): silent data loss."""
    store = NotesStore(tmp_path)
    store.add("sam", "the cat is called Mo")
    store.add("sam", "the dentist is at the new location on Main Street")
    assert store.forget("sam", "cat") == 1
    assert [row[2] for row in store.read("sam")] == ["the dentist is at the new location on Main Street"]


@bug
@pytest.mark.parametrize("text", ["the wifi passwords are on the fridge", "my api keys are in the shed", "the tokens are in the drawer"])
def test_plural_credential_words_are_refused_like_the_singular(text):
    """Owner: app track. The refusal pattern ends in \\b after "password", so "passwords", "api keys" and "tokens" are stored."""
    with pytest.raises(AdmissionError):
        check_note(text)


@bug
def test_fullwidth_letters_cannot_hide_a_credential_word():
    """Owner: app track. The coding companion folds fullwidth forms before its checks (clean.py); the notes check does not."""
    with pytest.raises(AdmissionError):
        check_note("my ｐａｓｓｗｏｒｄ is hunter2")


# ---- home_assistant (app track) -----------------------------------------------------------------------------

class _Resp:
    status_code = 200

    def __init__(self, content=b""):
        self.content = content

    def raise_for_status(self):
        return None


class _Session:
    def __init__(self):
        self.gets = []

    def get(self, url, **kw):
        self.gets.append(url)
        return _Resp(b"\xff\xd8\xff" + b"x" * 64)

    def post(self, url, **kw):  # a conversation answer
        r = _Resp()
        r.json = lambda: {"response": {"speech": {"plain": {"speech": "ok"}}}}
        return r


@bug
def test_a_camera_name_inside_another_word_does_not_send_a_picture_to_the_model(monkeypatch):
    """Owner: app track. Camera "door" matches "indoor" and "show" is a trigger word, so a question about the indoor temperature
    takes a camera snapshot and sends it to the configured model. Names must match as whole words."""
    monkeypatch.setenv("STACKCHAN_HA_TOKEN", "test-token-value")
    session, asked = _Session(), []
    ha = HomeAssistant(
        "http://192.0.2.20:8123", cameras={"door": "camera.door"}, session=session, allow_plain_http=True,
        allow_unidentified=True, ask_model=lambda q, jpeg: asked.append(q) or "a hallway",
    )
    ha.handle("Home Assistant, show me the indoor temperature")
    assert not session.gets and not asked


# ---- coding_companion (app track) ---------------------------------------------------------------------------

@bug
def test_a_working_state_that_nobody_updated_for_hours_is_not_still_working():
    """Owner: app track. AgentStatus stores the time of the last message and never reads it: after the agent crashes the robot
    says "Your coding agent is working" until the process restarts."""
    now = [0.0]
    status = AgentStatus(clock=lambda: now[0])
    status.update({"state": "working", "project": "my-app"})
    now[0] += 12 * 3600
    assert "is working" not in status.spoken()


class _Bus:
    def __init__(self):
        self.sent = []

    def send(self, device_id, command):
        self.sent.append((device_id, command.name))


@bug
def test_the_same_waiting_post_twice_plays_the_popup_once():
    """Owner: app track. state.py says changes are coalesced, but every post plays the sound again: a hook that fires in a
    loop makes the robot ping without end."""
    bus, status = _Bus(), AgentStatus()
    present = make_presenter(bus, lambda: ["unit-1"])
    for _ in range(2):
        present(status.update({"state": "waiting", "kind": "permission", "project": "my-app"}))
    assert [name for _, name in bus.sent].count("sound.play") == 1


@bug
def test_the_hook_does_not_send_the_token_through_a_proxy(tmp_path, monkeypatch):
    """Owner: app track. hook.send uses urllib's default opener, which honors http_proxy for 127.0.0.1 unless no_proxy is set,
    so the Bearer token can leave the computer. The hook should bypass proxies for its loopback address."""
    seen = []
    proxy = socket.socket()
    proxy.bind(("127.0.0.1", 0))
    proxy.listen(1)
    proxy.settimeout(3)

    def accept():
        try:
            conn, _ = proxy.accept()
            seen.append(conn.recv(4096))
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("http_proxy", f"http://127.0.0.1:{proxy.getsockname()[1]}")
    token = tmp_path / "token"
    token.write_text("secret-token-value\n")
    hook_send("working", "", "my-app", 9, token)  # port 9: nothing listens, so a direct connection fails quietly
    thread.join(4)
    proxy.close()
    assert not any(b"secret-token-value" in blob for blob in seen)


# ---- lock core (firmware track, patches SF08 and SF13) ------------------------------------------------------

_LOCK_C = r"""
#include <stdio.h>
#include "maipai_lock_core.h"
int main(void)
{
    mlk_t a; memset(&a, 0, sizeof a);
    for (int i = 0; i < LK_TOOL_MAX_FAILS - 1; i++) mlk_tool_note(&a, 1000, MLK_R_WRONG_CURRENT);   /* four wrong codes, no lockout yet */
    mlk_tool_saved_t saved; mlk_tool_save(&a, 1000, &saved);                                         /* what the unit keeps in flash */
    mlk_t b; memset(&b, 0, sizeof b); b.has_code = 1;
    mlk_tool_restore(&b, &saved, 500);                                                               /* the unit restarted */
    mlk_tool_note(&b, 600, MLK_R_WRONG_CURRENT);                                                     /* the fifth wrong code in a row */
    printf("%s\n", mlk_tool_open(&b, 601) == MLK_R_TOO_MANY ? "locked" : "open");
    return 0;
}
"""


@bug
@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_a_restart_does_not_reset_the_count_of_wrong_codes_at_four(tmp_path, tmp_path_factory):
    """Owner: firmware track (SF08, SF13). mlk_tool_save keeps the strikes and the running lockout but not tool_fails, so four wrong
    codes, a restart, four more and so on give unlimited guesses before the first lockout. The count must survive the restart."""
    source = tmp_path / "lock.c"
    source.write_text('#include <string.h>\n' + _LOCK_C)
    binary = tmp_path / "lock"
    build = subprocess.run(["cc", "-std=gnu99", "-Wall", f"-I{cores_dir(tmp_path_factory)}", str(source), "-o", str(binary)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    out = subprocess.run([str(binary)], capture_output=True, text=True).stdout.strip()
    assert out == "locked"
