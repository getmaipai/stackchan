"""An image from Home is served to the unit only when its detached signature verifies."""

import hashlib

from maipai_body.bodies.stackchan.firmware_update import FirmwareUpdater

IMAGE = b"verified firmware image"
BASE = {
    "link_healthy": True, "in_turn": False, "in_call": False, "timer_active": False,
    "timers_unknown": False, "alarm_active": False, "timer_due_in": None, "muted": False,
    "full_quiet": False,
}  # fmt: skip


def _updater(*, signature=b"sig", verify=lambda image, sig: True, with_signature=True):
    answer = {
        "available": True, "version": "1.1.0",
        "sha256": hashlib.sha256(IMAGE).hexdigest(), "size": len(IMAGE),
    }  # fmt: skip
    served, calls = [], []
    kwargs = {}
    if with_signature:
        kwargs = {"download_signature": lambda: signature, "verify": verify}
    updater = FirmwareUpdater(
        ask_home=lambda: answer,
        download=lambda path: path.write_bytes(IMAGE),
        serve_once=lambda path, signature=None: served.append((path.read_bytes(), signature)) or "http://body/x",
        call_tool=lambda name, args: calls.append((name, args)),
        situation=lambda: BASE.copy(),
        battery=lambda: {"percent": 80, "charging": False},
        unit_version=lambda: "1.0.0",
        now=lambda: 100_000,
        **kwargs,
    )
    return updater, served, calls


def test_a_valid_signature_is_served_with_the_image():
    updater, served, calls = _updater()
    updater.tick(100_000)
    assert served == [(IMAGE, b"sig")] and calls


def test_a_bad_signature_is_refused_and_nothing_is_served():
    updater, served, calls = _updater(verify=lambda image, sig: False)
    updater.tick(100_000)
    assert not served and not calls
    assert updater.failure_reason == "image_signature_invalid"


def test_a_missing_signature_is_refused():
    updater, served, calls = _updater(signature=None)
    updater.tick(100_000)
    assert not served and not calls and updater.failure_reason == "image_signature_invalid"


def test_no_trusted_key_means_no_update_from_home():
    updater, served, calls = _updater(with_signature=False)
    updater.tick(100_000)
    assert not served and not calls and updater.failure_reason == "update_key_missing"
