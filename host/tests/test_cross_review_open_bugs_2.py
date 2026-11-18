# ruff: noqa: E501
"""Open bugs found by cross-review round 2 (playground report 15, 2026-11-18): a tester's read of the SF19 to SF31 patches, the host key exchange and update header, the
packages (memory notes, Home Assistant, coding companion), the web flasher and the release script, plus what the hostile peer run showed.

Each test states the behavior the code should have and fails today; it is marked strict xfail so the suite stays green. `pytest --runxfail tests/test_cross_review_open_bugs_2.py`
shows every one failing. The first line of each docstring names the owner. When an owner fixes a bug the test turns into an unexpected pass and fails the run: delete its
marker and the test stays as the regression test. Nothing here fixes code."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import threading
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir
from test_release_and_update_vectors import _fake_build

from maipai_packages.coding_companion.clean import clean_project, clean_text
from maipai_packages.home_assistant import HomeAssistant
from maipai_packages.memory_notes.admission import AdmissionError, check_note

ROOT = Path(__file__).resolve().parents[2]
bug = pytest.mark.xfail(strict=True)
needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="no node on this machine")


def _node(script: str) -> str:
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, cwd=ROOT / "flasher", timeout=30)
    assert done.returncode == 0, done.stderr[-400:]
    return done.stdout.strip()


# ---- release script and web flasher (owner: app) ------------------------------------------------------------------

def _release(tmp_path, last_text=None, number=2, out="r", stale=None):
    build = _fake_build(tmp_path / "build") if not (tmp_path / "build").exists() else tmp_path / "build"
    key = tmp_path / "key.pem"
    if not key.exists():
        from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

        subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(key)], check=True, capture_output=True)
    last = tmp_path / "last.txt"
    if last_text is not None:
        last.write_text(last_text)
    if stale:
        (tmp_path / out).mkdir(exist_ok=True)
        (tmp_path / out / stale).write_bytes(b"stale")
    return subprocess.run(["bash", str(ROOT / "scripts" / "release.sh"), "--build-dir", str(build), "--version", "2.0.0", "--date", "2026-11-18", "--build-number", str(number),
                           "--signing-key", str(key), "--output", str(tmp_path / out), "--last-build-file", str(last)], capture_output=True, text=True)


@bug
def test_a_damaged_last_build_file_stops_a_real_release_instead_of_switching_the_rollback_check_off(tmp_path):
    """owner: app (scripts/release.sh). A last-build file that holds no number ("oops", or empty) makes `[ "$NUMBER" -le "" ]` fail with 'integer expression expected', the test counts as false, and the release goes ahead and then overwrites the file with its own number: the monotonic build number is silently reset."""
    result = _release(tmp_path, last_text="oops\n", number=1)
    assert result.returncode == 2, (result.returncode, result.stderr[-200:])


@bug
def test_a_release_folder_that_already_holds_files_is_refused_or_emptied(tmp_path):
    """owner: app (scripts/release.sh). `mkdir -p "$OUT"` reuses an existing folder, so a leftover signature or header from an earlier release stays beside the new files and can be published with them."""
    result = _release(tmp_path, last_text="1\n", number=2, stale="old-release.sig")
    leftover = (tmp_path / "r" / "old-release.sig").exists()
    assert result.returncode != 0 or not leftover


@bug
@needs_node
def test_the_flasher_page_does_not_flash_a_release_list_from_another_site():
    """owner: app (flasher/flasher.js). `?manifest=` is read from the page address and fetched as it is: a link to the real page with `?manifest=https://other.example/flash-manifest.json` flashes that site's images (their own list names their own hashes). The core must resolve the list against the page and refuse another origin."""
    out = _node("""
import * as core from './flasher-core.js';
if (typeof core.resolveManifestUrl !== 'function') { console.log('missing'); process.exit(0); }
try { core.resolveManifestUrl('https://other.example/flash-manifest.json', 'https://flasher.example/flasher/'); console.log('accepted'); } catch (e) { console.log('refused'); }
""")
    assert out == "refused", out


@bug
@needs_node
def test_the_flasher_checks_the_release_list_signature_before_it_writes_anything():
    """owner: app (flasher/flasher-core.js). parseManifest only reports `signed: Boolean(manifest.signature)`; nothing verifies the Ed25519 signature, so whoever serves the page can serve a list and images that agree with each other and are flashed."""
    out = _node("""
import * as core from './flasher-core.js';
console.log(typeof core.verifyManifestSignature);
""")
    assert out == "function", out


@bug
@needs_node
def test_a_release_list_with_two_parts_at_the_same_flash_address_is_refused():
    """owner: app (flasher/flasher-core.js). parseManifest checks each part alone; two parts at one offset (or one inside another) are accepted and the second overwrites the first."""
    out = _node("""
import { parseManifest } from './flasher-core.js';
const h = 'a'.repeat(64);
try { parseManifest({ builds: [{ chipFamily: 'ESP32-S3', parts: [{ path: 'a.bin', offset: 0, sha256: h }, { path: 'b.bin', offset: 0, sha256: h }] }] }); console.log('accepted'); } catch (e) { console.log('refused'); }
""")
    assert out == "refused", out


# ---- key exchange and update header, host side (owner: app) -----------------------------------------------------

@bug
def test_the_hosts_update_check_refuses_build_number_zero_like_the_unit_does(tmp_path):
    """owner: app (firmware/update_header.py). The unit core refuses a header with build 0 (MUH_BUILD_ZERO); verify_package with no installed build accepts it, so the host can offer an update the unit then rejects."""
    from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli
    from maipai_body.bodies.stackchan.firmware.update_header import MAGIC, sign_package, verify_package
    import hashlib

    key, pub = tmp_path / "k.pem", tmp_path / "k.pub"
    subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(key)], check=True, capture_output=True)
    pub.write_bytes(subprocess.run([openssl_cli(), "pkey", "-in", str(key), "-pubout"], check=True, capture_output=True).stdout)
    image = b"image-bytes" * 10
    header = MAGIC + (0).to_bytes(4, "little") + len(image).to_bytes(4, "little") + hashlib.sha256(image).digest() + bytes(8)
    assert not verify_package(sign_package(header, key), image, pub, installed_build=None).ok


@bug
def test_a_pairing_exchange_nobody_finished_stops_showing_as_waiting():
    """owner: app (xiaozhi/link_exchange.py). pending_devices() lists every exchange that reached its six digits, and the only expiry is checked when someone types a code: a unit that dropped (or a hostile peer making up units) stays on the owner's pairing card for good."""
    from maipai_body.bodies.stackchan.xiaozhi.link_exchange import EXCHANGE_TTL_S, ExchangeRegistry

    now = [0.0]
    registry = ExchangeRegistry(clock=lambda: now[0])
    registry.begin("02:00:00:00:00:01", bytes([7]) * 32)
    registry.reveal("02:00:00:00:00:01", bytes([9]) * 16)
    assert registry.pending_devices() == ["02:00:00:00:00:01"]
    now[0] += EXCHANGE_TTL_S + 60
    assert registry.pending_devices() == []


@bug
def test_a_second_pairing_exchange_for_the_same_unit_does_not_replace_the_one_waiting_for_its_digits():
    """owner: app (xiaozhi/link_exchange.py). begin() overwrites the live exchange of a device id, so any peer that knows the id (it is printed on the unit) can start its own exchange while the owner reads the digits; the owner's correct digits then fail, count as a wrong code, and three of them lock the unit's pairing for ten minutes."""
    from maipai_body.bodies.stackchan.xiaozhi.link_exchange import ExchangeError, ExchangeRegistry, sas

    registry = ExchangeRegistry()
    dev = "02:00:00:00:00:02"
    pk_u, n_u = bytes([1]) * 32, bytes([2]) * 16
    first = registry.begin(dev, pk_u)
    n_h = registry.reveal(dev, n_u)["n_h"]
    owners_digits = sas(pk_u, first.start_reply["pk_h"], n_u, n_h)
    try:
        registry.begin(dev, bytes([5]) * 32)   # the other peer
        registry.reveal(dev, bytes([6]) * 16)
    except ExchangeError:
        pass   # refusing the second start is the right answer
    registry.approve(dev, owners_digits)   # the owner's digits must still work


# ---- packages (owner: app) ----------------------------------------------------------------------------------------

@bug
@pytest.mark.parametrize("text", ["my pw is hunter2", "the wifi passwd is blue42"])
def test_a_note_with_a_short_word_for_password_is_refused(text):
    """owner: app (memory_notes/admission.py). The refused words list password, passcode, pin and token but not the everyday short forms pw and passwd."""
    with pytest.raises(AdmissionError):
        check_note(text)


@bug
@pytest.mark.parametrize("text", ["my social security number is 123 45 6789", "ssn 123456789", "my passport number is X12345678"])
def test_a_note_with_a_government_id_that_is_not_written_with_dashes_is_refused(text):
    """owner: app (memory_notes/admission.py). Only the dashed nine digit form is caught; spaces, no separators and a passport number are stored."""
    with pytest.raises(AdmissionError):
        check_note(text)


@bug
@pytest.mark.parametrize("text", ["key is AKIAIOSFODNN7EXAMPLE", "bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijk"])
def test_a_note_with_a_cloud_key_id_or_a_signed_token_is_refused(text):
    """owner: app (memory_notes/admission.py). Only sk-, ghp-, tskey- and xox prefixes are recognized; an AWS access key id and a JWT are stored and later read into the model's prompt."""
    with pytest.raises(AdmissionError):
        check_note(text)


@bug
def test_a_spoken_this_is_adult_does_not_open_that_adults_notes_to_a_voice_nobody_recognized():
    """owner: app, needs a decision from Jesse (memory_notes/store.py Notes.handle). "this is Sam" from an unidentified speaker holds Sam's notes open for 30 minutes, so a child can say it and then ask what the robot remembers; the notes' own record says a child never has notes and nobody else's notes are read."""
    from maipai_packages.memory_notes.store import Notes, NotesStore

    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        notes = Notes(NotesStore(Path(folder)), ["sam", "robin"], default_person="robin")
        notes.store.add("sam", "the surprise party is on Friday")
        notes.handle("this is sam")   # said by a voice the robot cannot tell from anyone
        reply = notes.handle("what do you remember") or ""
        assert "surprise" not in reply


@bug
def test_the_home_assistant_trigger_must_be_a_whole_word():
    """owner: app (home_assistant/client.py). handle() tests `startswith(trigger)`, so "home assistants are great" is taken as a request ("s are great") and posted to Home Assistant."""
    posted = []

    class Session:
        def post(self, url, **kw):
            posted.append(url)
            raise AssertionError("a sentence that merely starts with the trigger letters must not be sent")

    ha = HomeAssistant("http://127.0.0.1:8123", session=Session())
    assert ha.handle("home assistants are great", speaker="sam") is None


@bug
def test_a_camera_picture_is_read_with_a_size_cap_not_whole_into_memory():
    """owner: app (home_assistant/client.py). snapshot() calls get() without stream=True and reads `.content` before it compares with the 3 MB limit, so a camera (or anything answering at that address) that sends gigabytes is read in full first."""
    seen = {}

    class Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        @property
        def content(self):
            seen["read_whole_body"] = True
            return b"\xff\xd8" + b"x" * 10

        def iter_content(self, n):
            yield b"\xff\xd8" + b"x" * 10

    class Session:
        def get(self, url, **kw):
            seen["stream"] = kw.get("stream")
            return Resp()

    ha = HomeAssistant("http://127.0.0.1:8123", cameras={"door": "camera.door"}, session=Session())
    ha.snapshot("camera.door")
    assert seen.get("stream") is True and not seen.get("read_whole_body")


@bug
def test_a_project_name_that_is_a_relative_path_is_not_shown():
    """owner: app (coding_companion/clean.py). The path check needs a letter or digit before the first slash segment and a non-dot before it, so "../../etc" passes as a project name."""
    assert clean_project("../../etc") == ""


@bug
def test_a_short_cloud_key_id_in_the_request_text_is_not_shown():
    """owner: app (coding_companion/clean.py). The long-token rule starts at 32 characters; an AWS access key id has 20 and is shown on the robot's screen."""
    assert clean_text("rotate AKIAIOSFODNN7EXAMPLE now") is None


@bug
def test_the_coding_companion_endpoint_drops_a_client_that_sends_nothing():
    """owner: app (coding_companion/server.py). _Handler has no socket timeout, so a local client that opens a connection and sends half a request holds a thread for good (and `rfile.read(length)` waits for a body that never comes)."""
    from maipai_packages.coding_companion.server import _Handler

    assert _Handler.timeout is not None


# ---- firmware cores (owner: firmware) ------------------------------------------------------------------------------

@bug
@needs_cc
def test_the_servo_clock_holds_the_command_when_the_speed_ceiling_is_zero(tmp_path, tmp_path_factory):
    """owner: firmware (SF28 maipai_servo_clock_core.h). msc_limit_step() raises a zero step to 1, so with the limiter's scale at 0 (carried) the command still creeps toward the target by one tenth of a degree every step, about 5 degrees a second."""
    src = tmp_path / "t.c"
    src.write_text('#include <stdio.h>\n#include "maipai_servo_clock_core.h"\nint main(void){ printf("%d\\n", msc_limit_step(0, 1000, msc_vmax_tenth_dps(0), 0.02f)); return 0; }\n')
    exe = tmp_path / "t"
    built = subprocess.run(["cc", "-std=gnu99", f"-I{cores_dir(tmp_path_factory)}", str(src), "-o", str(exe)], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    assert subprocess.run([str(exe)], capture_output=True, text=True).stdout.strip() == "0"
