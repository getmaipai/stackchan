# ruff: noqa: E501
"""Over-the-air update against a stand-in unit that follows firmware patches 159 and 160.

The stand-in refuses an image address that is not its paired host, refuses an image that leaves less
than 20 percent of its slot free, checks a real Ed25519 signature (openssl) before it switches the boot
slot, and rolls back to the old slot when the new image does not reach the host after its first boot.
The host side is the real one: the release check, the push, and the one-read file route.
"""

import asyncio
import json
import os
import subprocess
from types import SimpleNamespace

os.environ["TMPDIR"] = "/private/tmp"

import pytest
from test_stackchan_updater import make_release

from maipai_body.bodies.stackchan import updater
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer
from maipai_body.live_units import LiveUnits

UNIT = "aa:bb:cc:dd:ee:ff"


def _sign(private, data: bytes, tmp_path) -> bytes:
    message = tmp_path / "msg.bin"
    message.write_bytes(data)
    return subprocess.run(
        [openssl_cli(), "pkeyutl", "-sign", "-inkey", str(private), "-rawin", "-in", str(message)],
        check=True,
        capture_output=True,
    ).stdout


def _signed_release(tmp_path, *, version="1.2.0", app_size=1000):
    folder, public, (private, _pub) = make_release(tmp_path, version=version, app_size=app_size)
    image = folder / "stack-chan-maipai.bin"
    (folder / "stack-chan-maipai.bin.sig").write_bytes(_sign(private, image.read_bytes(), tmp_path))
    return folder, public, private


class StandInUnit:
    """What the firmware does, in the same order, with the same plain messages."""

    def __init__(self, server, public_pem, tmp_path, *, paired_host="192.0.2.1", slot=0x4F0000):
        self.server, self.public, self.tmp = server, public_pem, tmp_path
        self.paired_host, self.slot = paired_host, slot
        self.running, self.running_version = "ota_0", "1.1.0"
        self.pending = False
        self.written: dict[str, bytes] = {}
        self.events: list[str] = []

    def _fetch(self, url: str) -> bytes:
        token = url.rsplit("/", 1)[1]
        request = SimpleNamespace(match_info={"device_id": UNIT, "token": token})
        return asyncio.run(self.server._serve_firmware_file(request)).body

    def _verify(self, image: bytes, signature: bytes) -> bool:
        (self.tmp / "u.img").write_bytes(image)
        (self.tmp / "u.sig").write_bytes(signature)
        done = subprocess.run(
            [openssl_cli(), "pkeyutl", "-verify", "-pubin", "-inkey", str(self.public), "-rawin",
             "-in", str(self.tmp / "u.img"), "-sigfile", str(self.tmp / "u.sig")],
            capture_output=True,
        )  # fmt: skip
        return done.returncode == 0

    def call(self, name, args, **_):
        assert name == "self.firmware.update"
        why = self._start(args)
        return json.dumps({"started": False, "reason": why} if why else {"started": True})

    def _start(self, args) -> str:
        host = args["url"].split("://", 1)[1].split("/", 1)[0].split(":")[0]
        if host != self.paired_host:
            return "Update refused: the image address is not the paired host. Start the update from the host the unit is paired with."
        if args["size"] * 5 > self.slot * 4:
            return "Update refused: the image would leave less than 20 percent of its slot free. Build a smaller image."
        try:
            signature = self._fetch(args["url"] + ".sig")
        except Exception:
            return "Update refused: no valid signature file at the image address plus .sig. Nothing was installed."
        image = self._fetch(args["url"])
        if len(signature) != 64 or not self._verify(image, signature):
            return "Update refused: the signature does not match this image or the update key. Nothing was installed."
        inactive = "ota_1" if self.running == "ota_0" else "ota_0"
        self.written[inactive] = image  # the boot flag moves only after the check above
        self.boot_slot, self.next_version = inactive, args["version"]
        self.pending = True
        return ""

    def reboot(self, *, reaches_host: bool) -> None:
        """First boot of the new image: kept when it reaches the host, otherwise the old slot comes back."""
        if not self.pending:
            return
        self.pending = False
        if reaches_host:
            self.running, self.running_version = self.boot_slot, self.next_version
            self.events.append("firmware_update_validated")
        else:
            self.events.append("rolled_back")


def _rig(tmp_path, *, public, paired_host="192.0.2.1", slot=0x4F0000):
    server = XiaozhiServer(PairingStore(), robot=None)
    server._sessions = {UNIT: object()}
    server.advertised_vision_url = "http://192.0.2.1:8767/vision/x"
    unit = StandInUnit(server, public, tmp_path, paired_host=paired_host, slot=slot)
    server.call_device_tool = unit.call
    return server, unit, LiveUnits(server)


def _push(live, release, version="1.2.0"):
    return updater.update_over_air(
        release, device_id=UNIT, unit_version="1.1.0", push=live.push, dry_run=False
    )


def test_good_image_is_checked_written_and_kept(tmp_path):
    folder, public, _ = _signed_release(tmp_path)
    _server, unit, live = _rig(tmp_path, public=public)
    release = updater.load_release(folder, public_key=public)
    assert "Update started" in _push(live, release)
    assert unit.written["ota_1"] == (folder / "stack-chan-maipai.bin").read_bytes()
    unit.reboot(reaches_host=True)
    assert unit.running == "ota_1" and unit.running_version == "1.2.0"
    assert unit.events == ["firmware_update_validated"]


def test_bad_signature_is_refused_and_nothing_is_written(tmp_path):
    folder, public, _ = _signed_release(tmp_path)
    image = folder / "stack-chan-maipai.bin"
    tampered = bytearray(image.read_bytes())
    tampered[10] ^= 1  # the image changes after it was signed
    image.write_bytes(bytes(tampered))
    _server, unit, live = _rig(tmp_path, public=public)
    release = SimpleNamespace(
        folder=folder,
        version="1.2.0",
        app_part=lambda: {"path": image.name, "sha256": "", "size": 1000},
    )
    with pytest.raises(updater.UpdateRefused, match="signature does not match"):
        _push(live, release)
    assert unit.written == {} and not unit.pending


def test_signature_from_another_key_is_refused(tmp_path):
    folder, public, _ = _signed_release(tmp_path)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    _f, _p, other_private = _signed_release(other_dir)
    image = folder / "stack-chan-maipai.bin"
    (folder / "stack-chan-maipai.bin.sig").write_bytes(
        _sign(other_private, image.read_bytes(), tmp_path)
    )
    _server, unit, live = _rig(tmp_path, public=public)
    release = updater.load_release(folder, public_key=public)
    with pytest.raises(updater.UpdateRefused, match="Nothing was installed"):
        _push(live, release)
    assert unit.written == {}


def test_failed_first_boot_rolls_back_to_the_old_slot(tmp_path):
    folder, public, _ = _signed_release(tmp_path)
    _server, unit, live = _rig(tmp_path, public=public)
    _push(live, updater.load_release(folder, public_key=public))
    unit.reboot(reaches_host=False)
    assert unit.running == "ota_0" and unit.running_version == "1.1.0"
    assert unit.events == ["rolled_back"]


def test_image_from_a_host_that_is_not_paired_is_refused(tmp_path):
    folder, public, _ = _signed_release(tmp_path)
    _server, unit, live = _rig(tmp_path, public=public, paired_host="198.51.100.7")
    with pytest.raises(updater.UpdateRefused, match="not the paired host"):
        _push(live, updater.load_release(folder, public_key=public))
    assert unit.written == {}


def test_unit_refuses_an_image_that_leaves_less_than_twenty_percent_free(tmp_path):
    folder, public, _ = _signed_release(tmp_path, app_size=900)
    _server, unit, live = _rig(tmp_path, public=public, slot=1000)  # 900 of 1000 is 90 percent full
    release = SimpleNamespace(
        folder=folder,
        version="1.2.0",
        app_part=lambda: {"path": "stack-chan-maipai.bin", "sha256": "", "size": 900},
    )
    with pytest.raises(updater.UpdateRefused, match="20 percent"):
        updater.update_over_air(
            release, device_id=UNIT, unit_version="1.1.0", push=live.push, dry_run=False
        )
    assert unit.written == {}


def test_missing_signature_file_stops_the_host_before_anything_is_sent(tmp_path):
    folder, public, _ = _signed_release(tmp_path)
    (folder / "stack-chan-maipai.bin.sig").unlink()
    server, _unit, live = _rig(tmp_path, public=public)
    release = updater.load_release(folder, public_key=public)
    with pytest.raises(updater.UpdateRefused, match="signature file"):
        _push(live, release)
    assert server._firmware_files == {}


def test_dry_run_is_the_default_and_pushes_nothing(tmp_path):
    folder, public, _ = _signed_release(tmp_path)
    server, unit, live = _rig(tmp_path, public=public)
    release = updater.load_release(folder, public_key=public)
    text = updater.update_over_air(
        release, device_id=UNIT, unit_version="1.1.0", push=live.push, dry_run=True
    )
    assert "Dry run" in text and unit.written == {} and server._firmware_files == {}
