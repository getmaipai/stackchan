"""The release script dry run, the signed update vectors, and the Home-driven update path (host side)."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from maipai_body.bodies.stackchan.firmware.flash_manifest import verify_detached, verify_manifest

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((Path(__file__).parent / "fixtures" / "update-signature-vectors.json").read_text())


@pytest.fixture
def pubkey(tmp_path):
    path = tmp_path / "pub.pem"
    path.write_text(VECTORS["public_key_pem"])
    return path


@pytest.mark.parametrize("vector", VECTORS["vectors"], ids=lambda v: v["name"])
def test_signed_update_vectors(vector, pubkey):
    assert verify_detached(bytes.fromhex(vector["image_hex"]), bytes.fromhex(vector["signature_hex"]), pubkey) is vector["valid"]


def _fake_build(path: Path) -> Path:
    (path / "bootloader").mkdir(parents=True)
    (path / "partition_table").mkdir()
    (path / "bootloader" / "bootloader.bin").write_bytes(b"B" * 64)
    (path / "partition_table" / "partition-table.bin").write_bytes(b"P" * 32)
    (path / "xiaozhi.bin").write_bytes(b"APP" * 100)
    (path / "flasher_args.json").write_text(json.dumps({
        "flash_settings": {"flash_mode": "dio", "flash_size": "16MB", "flash_freq": "80m"},
        "flash_files": {"0x0": "bootloader/bootloader.bin", "0x8000": "partition_table/partition-table.bin", "0x20000": "xiaozhi.bin"},
        "extra_esptool_args": {"chip": "esp32s3"},
    }))
    return path


def test_the_release_script_dry_run_makes_a_signed_folder_marked_test(tmp_path):
    build, out = _fake_build(tmp_path / "build"), tmp_path / "release"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "release.sh"), "--build-dir", str(build), "--version", "1.0.0-test", "--date", "2026-11-18", "--build-number", "7", "--test-key", "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert (out / "TEST-KEY-NOT-FOR-RELEASE.txt").is_file()
    pub = out / "release-key.pub.pem"
    manifest = json.loads((out / "flash-manifest.json").read_text())
    assert verify_manifest(manifest, pub)
    image = (out / "xiaozhi.bin").read_bytes()
    assert verify_detached(image, (out / "xiaozhi.bin.sig").read_bytes(), pub)
    assert not verify_detached(image + b"x", (out / "xiaozhi.bin.sig").read_bytes(), pub)
    assert hashlib.sha256(image).hexdigest() in json.dumps(manifest)
    from maipai_body.bodies.stackchan.firmware.update_header import verify_package

    package = (out / "xiaozhi.bin.hdr").read_bytes() + (out / "xiaozhi.bin.hdr.sig").read_bytes()
    assert verify_package(package, image, pub, installed_build=6).header["build_number"] == 7
    assert not verify_package(package, image, pub, installed_build=7).ok  # not higher


def test_the_release_script_refuses_without_a_key_or_with_both():
    base = ["bash", str(ROOT / "scripts" / "release.sh"), "--build-dir", "/nowhere", "--version", "1", "--date", "2026-11-18", "--build-number", "1"]
    assert subprocess.run(base, capture_output=True).returncode == 2
    assert subprocess.run([*base, "--test-key", "--signing-key", "k"], capture_output=True).returncode == 2


# ---- the Home-driven update path: hash AND signature are checked, and the signature is served beside the image ----

def _updater(tmp_path, image: bytes, signature: bytes | None, pubkey, answer_sha: str | None = None):
    from maipai_body.bodies.stackchan.firmware_update import FirmwareUpdater

    served, calls = [], []
    answer = {"available": True, "version": "1.1.0", "sha256": answer_sha or hashlib.sha256(image).hexdigest(), "size": len(image)}
    updater = FirmwareUpdater(
        ask_home=lambda: answer,
        download=lambda p: p.write_bytes(image),
        serve_once=lambda p, sig=None: served.append((p.read_bytes(), sig)) or "http://body/x",
        call_tool=lambda n, a: calls.append((n, a)),
        situation=lambda: {"link_healthy": True, "in_turn": False, "in_call": False, "timer_active": False, "timers_unknown": False, "alarm_active": False, "timer_due_in": None, "muted": False, "full_quiet": False},
        battery=lambda: {"percent": 80, "charging": False},
        unit_version=lambda: "1.0.0",
        now=lambda: 100_000,
        download_signature=lambda: signature,
        verify=lambda img, sig: verify_detached(img, sig, pubkey),
    )
    return updater, served, calls


def test_a_real_signature_is_checked_and_served_with_the_image(tmp_path, pubkey):
    vector = next(v for v in VECTORS["vectors"] if v["name"] == "ramp: good")
    image, sig = bytes.fromhex(vector["image_hex"]), bytes.fromhex(vector["signature_hex"])
    updater, served, calls = _updater(tmp_path, image, sig, pubkey)
    updater.tick(100_000)
    assert served == [(image, sig)] and calls[0][0] == "self.firmware.update"


def test_a_good_hash_with_a_bad_signature_is_refused(tmp_path, pubkey):
    vector = next(v for v in VECTORS["vectors"] if v["name"] == "ramp: signature changed by one bit")
    image, bad = bytes.fromhex(vector["image_hex"]), bytes.fromhex(vector["signature_hex"])
    updater, served, calls = _updater(tmp_path, image, bad, pubkey)
    updater.tick(100_000)
    assert not served and not calls and updater.failure_reason == "image_signature_invalid"


def test_a_good_signature_with_a_wrong_hash_is_refused(tmp_path, pubkey):
    vector = next(v for v in VECTORS["vectors"] if v["name"] == "ramp: good")
    image, sig = bytes.fromhex(vector["image_hex"]), bytes.fromhex(vector["signature_hex"])
    updater, served, calls = _updater(tmp_path, image, sig, pubkey, answer_sha="0" * 64)
    updater.tick(100_000)
    assert not served and not calls and updater.failure_reason == "image_hash_mismatch"


def test_the_server_publishes_the_signature_next_to_the_image(tmp_path):
    import asyncio
    from types import SimpleNamespace

    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
    from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

    unit = "aa:bb:cc:dd:ee:07"
    server = XiaozhiServer(PairingStore(), robot=None)
    server._sessions = {unit: object()}
    server.advertised_vision_url = "http://192.0.2.1:8767/vision/x"
    image = tmp_path / "app.bin"
    image.write_bytes(b"image")
    url = server.serve_firmware_once(image, unit, signature=b"S" * 64)
    token = url.rsplit("/", 1)[1]
    got = asyncio.run(server._serve_firmware_file(SimpleNamespace(match_info={"device_id": unit, "token": token})))
    sig = asyncio.run(server._serve_firmware_file(SimpleNamespace(match_info={"device_id": unit, "token": token + ".sig"})))
    assert got.body == b"image" and sig.body == b"S" * 64


def test_a_real_release_must_have_a_higher_build_number_than_the_last(tmp_path):
    build = _fake_build(tmp_path / "build")
    key = tmp_path / "key.pem"
    from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

    subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(key)], check=True, capture_output=True)
    last = tmp_path / "last.txt"
    last.write_text("9\n")

    def run(number, out):
        return subprocess.run(
            ["bash", str(ROOT / "scripts" / "release.sh"), "--build-dir", str(build), "--version", "2.0.0", "--date", "2026-11-18", "--build-number", str(number),
             "--signing-key", str(key), "--output", str(tmp_path / out), "--last-build-file", str(last)],
            capture_output=True, text=True,
        )

    assert run(9, "r1").returncode == 2 and "not higher" in run(9, "r1").stderr
    assert run(5, "r1").returncode == 2
    ok = run(10, "r2")
    assert ok.returncode == 0, ok.stderr + ok.stdout
    assert last.read_text().strip() == "10"
    assert run(10, "r3").returncode == 2  # the same number again is refused
