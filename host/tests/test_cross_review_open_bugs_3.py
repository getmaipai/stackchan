# ruff: noqa: E501
"""Open bugs found by the red team of the fixed code (playground report 17, 2026-11-18). Same rules as test_cross_review_open_bugs_2.py: each test states the behavior the code should have and
fails today (strict xfail); the first docstring line names the owner; delete the marker when it is fixed."""

from __future__ import annotations

import pytest

from maipai_body.bodies.stackchan.firmware.update_header import build_header
from maipai_packages.memory_notes.admission import AdmissionError, check_note

bug = pytest.mark.xfail(strict=True)


@pytest.mark.parametrize("text", ["the pass word is plum", "p a s s w o r d is plum", "my secret word is plum", "the wi-fi key is abcd1234efgh"])
def test_a_note_that_spells_a_credential_word_apart_or_with_another_everyday_word_is_refused(text):
    """owner: app (memory_notes/admission.py; red team of the fixed credential words). The refused words match whole words: "pass word", spaced letters, "secret word" and "wi-fi key" slip through. A word list can never be complete; the lasting fix is to refuse a note that holds a short secret-looking value after any of these everyday cue words, or to keep notes to a small set of kinds."""
    with pytest.raises(AdmissionError):
        check_note(text)


@pytest.mark.parametrize("text", ["passw0rd is plum", "pa55word is plum"])
def test_a_note_with_a_digit_for_a_letter_in_the_word_password_is_refused(text):
    """owner: app (memory_notes/admission.py; red team). The fold handles accents and look-alike letters but not digits used as letters (0 for o, 5 for s, 3 for e, 1 for l)."""
    with pytest.raises(AdmissionError):
        check_note(text)


def test_a_note_with_a_driver_license_or_vault_code_number_is_refused():
    """owner: app (memory_notes/admission.py; red team). Government ids are caught as social security and passport numbers; a driver license number and a vault or safe code are not."""
    for text in ("my driver license number is D1234567", "the vault code is 482913"):
        with pytest.raises(AdmissionError):
            check_note(text)


def test_the_host_does_not_make_or_offer_a_header_with_a_build_number_the_unit_refuses():
    """owner: app (firmware/update_header.py; update path review, report 17). The unit refuses a build number of 2^31 or more (SF37: it would be stored as a negative number); build_header() allows up to 2^32 - 1 and verify_package() accepts it, so the release script can make, and the host serve, an update every unit refuses."""
    with pytest.raises(ValueError):
        build_header(2**31, b'image bytes' * 20)


def test_the_release_script_refuses_a_build_number_the_unit_refuses(tmp_path):
    from test_cross_review_open_bugs_2 import _release

    result = _release(tmp_path, last_text="1\n", number=2**31)
    assert result.returncode == 2, (result.returncode, result.stderr[-200:])
