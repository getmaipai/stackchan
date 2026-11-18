"""The signed update header: version, build number and image hash in 64 bytes, signed with Ed25519; the unit refuses a lower build number."""

import hashlib
import json
from pathlib import Path

import pytest

from maipai_body.bodies.stackchan.firmware import update_header as uh

FIXTURES = Path(__file__).parent / "fixtures"
VECTORS = json.loads((FIXTURES / "update-signature-vectors.json").read_text())
IMAGE = bytes(range(256)) * 8


@pytest.fixture
def pub(tmp_path):
    path = tmp_path / "pub.pem"
    path.write_text(VECTORS["public_key_pem"])
    return path


@pytest.fixture
def key(tmp_path):
    from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli
    import subprocess

    path = tmp_path / "k.pem"
    subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(path)], check=True, capture_output=True)
    pub = subprocess.run([openssl_cli(), "pkey", "-in", str(path), "-pubout"], check=True, capture_output=True).stdout
    (tmp_path / "k.pub").write_bytes(pub)
    return path, tmp_path / "k.pub"


def test_the_header_layout_is_64_bytes_and_fixed():
    header = uh.build_header("1.2.3", 17, IMAGE)
    assert len(header) == 64 and header[:4] == b"MPUH" and header[4] == 1
    assert int.from_bytes(header[8:12], "big") == 17
    assert header[12:28].rstrip(b"\0") == b"1.2.3"
    assert int.from_bytes(header[28:32], "big") == len(IMAGE)
    assert header[32:64] == hashlib.sha256(IMAGE).digest()
    assert uh.parse_header(header) == {"version": "1.2.3", "build_number": 17, "size": len(IMAGE), "sha256": hashlib.sha256(IMAGE).hexdigest()}


def test_bad_inputs_are_refused():
    with pytest.raises(ValueError):
        uh.build_header("x" * 17, 1, IMAGE)
    with pytest.raises(ValueError):
        uh.build_header("1.0", 0, IMAGE)  # build numbers start at 1
    with pytest.raises(ValueError):
        uh.build_header("1.0", 2**32, IMAGE)
    with pytest.raises(ValueError):
        uh.parse_header(b"MPUX" + bytes(60))
    with pytest.raises(ValueError):
        uh.parse_header(bytes(10))


def test_a_signed_package_verifies_and_a_changed_image_or_header_does_not(key):
    private, public = key
    package = uh.sign_package(uh.build_header("1.2.3", 17, IMAGE), private)
    assert len(package) == 128
    assert uh.verify_package(package, IMAGE, public, installed_build=16).ok
    assert not uh.verify_package(package, IMAGE + b"x", public, installed_build=16).ok  # the image changed
    tampered = bytearray(package)
    tampered[9] ^= 1  # the build number changed
    assert not uh.verify_package(bytes(tampered), IMAGE, public, installed_build=1).ok
    assert not uh.verify_package(package[:100], IMAGE, public, installed_build=1).ok


def test_the_unit_refuses_a_build_number_that_is_not_higher():
    """The rollback test: an older release signed with the right key is refused."""
    import subprocess
    import tempfile

    from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

    with tempfile.TemporaryDirectory() as work:
        private, public = Path(work) / "k.pem", Path(work) / "k.pub"
        subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(private)], check=True, capture_output=True)
        public.write_bytes(subprocess.run([openssl_cli(), "pkey", "-in", str(private), "-pubout"], check=True, capture_output=True).stdout)
        old_image = b"old release"
        old = uh.sign_package(uh.build_header("1.0.0", 5, old_image), private)
        assert uh.verify_package(old, old_image, public, installed_build=4).ok
        for installed in (5, 6, 99):
            result = uh.verify_package(old, old_image, public, installed_build=installed)
            assert not result.ok and "older" in result.reason.lower() or "not higher" in result.reason.lower()


def test_the_vectors_for_the_firmware_check_verify_here(pub):
    vectors = json.loads((FIXTURES / "update-header-vectors.json").read_text())
    for v in vectors["vectors"]:
        result = uh.verify_package(bytes.fromhex(v["package_hex"]), bytes.fromhex(v["image_hex"]), pub, installed_build=v["installed_build"])
        assert result.ok is v["valid"], v["name"]


def test_the_hosts_update_path_serves_the_package_and_refuses_a_rollback(tmp_path):
    """The Home-driven path with a signed header: the 128-byte package is served at .mph, a lower build number is refused."""
    import asyncio
    from types import SimpleNamespace

    from maipai_body.app import _UpdateBuilds
    from maipai_body.bodies.stackchan.firmware_update import FirmwareUpdater
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
    from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

    import subprocess

    from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

    private, public = tmp_path / "k.pem", tmp_path / "k.pub"
    subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(private)], check=True, capture_output=True)
    public.write_bytes(subprocess.run([openssl_cli(), "pkey", "-in", str(private), "-pubout"], check=True, capture_output=True).stdout)
    builds = _UpdateBuilds(tmp_path / "builds.json")

    def check(image, signature):
        verdict = uh.verify_package(signature, image, public, installed_build=builds.highest())
        if verdict.ok:
            builds.record(verdict.header["build_number"])
        return verdict.ok

    unit = "aa:bb:cc:dd:ee:07"
    server = XiaozhiServer(PairingStore(), robot=None)
    server._sessions = {unit: object()}
    server.advertised_vision_url = "http://192.0.2.1:8767/vision/x"
    base = {"link_healthy": True, "in_turn": False, "in_call": False, "timer_active": False, "timers_unknown": False, "alarm_active": False, "timer_due_in": None, "muted": False, "full_quiet": False}

    def run(version, build, image):
        package = uh.sign_package(uh.build_header(version, build, image), private)
        served, calls = [], []
        updater = FirmwareUpdater(
            ask_home=lambda: {"available": True, "version": version, "sha256": hashlib.sha256(image).hexdigest(), "size": len(image)},
            download=lambda p: p.write_bytes(image),
            serve_once=lambda p, sig=None: served.append(server.serve_firmware_once(p, unit, sig)) or served[-1],
            call_tool=lambda n, a: calls.append(n), situation=lambda: dict(base), battery=lambda: {"percent": 80, "charging": False},
            unit_version=lambda: "0.9.0", now=lambda: 100_000, download_signature=lambda: package, verify=check,
        )
        updater.tick(100_000)
        return served, calls, updater

    served, calls, _ = run("1.0.0", 10, b"image ten")
    assert calls and served
    token = served[0].rsplit("/", 1)[1]
    got = asyncio.run(server._serve_firmware_file(SimpleNamespace(match_info={"device_id": unit, "token": token + ".mph"})))
    assert len(got.body) == 128  # the unit can fetch the signed header
    served, calls, updater = run("0.9.5", 9, b"older image")  # a validly signed older build
    assert not served and not calls and updater.failure_reason == "image_signature_invalid"
    assert builds.highest() == 10
