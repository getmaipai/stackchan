# ruff: noqa: E501
"""The unit's own update checks (firmware patches 155, 159 and 160 with FM01), run as the firmware has them.

Earlier update tests used a Python stand-in for the unit that called openssl. Here the unit's real C++ code (update_verify.cc: the
Ed25519 arithmetic, the paired-host rule, the 20 percent rule, the build key) is compiled for the PC and the same scenarios run
against it with a key generated for the test, over the host's real one-read firmware route, which serves the image and its
.sig next to it."""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_stackchan_ota_unit import UNIT, StandInUnit, _push, _rig, _sign, _signed_release

from maipai_body.bodies.stackchan import updater
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
FILES = (
    "firmware/xiaozhi-esp32/main/update_verify.h",
    "firmware/xiaozhi-esp32/main/update_verify.cc",
)

pytestmark = pytest.mark.skipif(
    shutil.which("cc") is None and shutil.which("c++") is None,
    reason="no C++ compiler on this machine",
)


def _blocks(patch: str) -> dict[str, str]:
    text = (PATCHES / patch).read_text()
    out = {}
    for block in text.split("\ndiff --git ")[1:]:
        path = block.split(" ", 1)[0].removeprefix("a/")
        if path in FILES:
            out[path] = "diff --git " + block.rstrip("\n") + "\n"
    return out


@pytest.fixture(scope="session")
def checker(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("verify")
    for number, patch in enumerate(
        (
            "155-host-url-tools-removed-and-signed-updates.patch",
            "159-wireless-update-from-paired-host.patch",
        )
    ):
        pick = root / f"p{number}.diff"
        pick.write_text("".join(_blocks(patch).values()))
        applied = subprocess.run(
            ["git", "apply", str(pick)], cwd=root, capture_output=True, text=True
        )
        assert applied.returncode == 0, applied.stderr
    src = root / "firmware/xiaozhi-esp32/main"
    binary = root / "check"
    built = subprocess.run(
        ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", f"-I{src}", str(HERE / "firmware/update_verify_check.cc"), str(src / "update_verify.cc"), "-o", str(binary)],
        capture_output=True, text=True,
    )  # fmt: skip
    assert built.returncode == 0, built.stderr
    return binary


def _run(binary: Path, *args: str) -> str:
    return subprocess.run(
        [str(binary), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _raw_public(private: Path) -> bytes:
    der = subprocess.run(
        [openssl_cli(), "pkey", "-in", str(private), "-pubout", "-outform", "DER"],
        capture_output=True,
        check=True,
    ).stdout
    return der[-32:]


def _verify(binary: Path, image: bytes, signature: bytes, public: bytes) -> bool:
    """What the firmware's streaming verifier does: hash R, the key and the image with SHA-512, then check with Ed25519VerifyDigest."""
    if len(signature) != 64 or len(public) != 32:
        return False
    digest = hashlib.sha512(signature[:32] + public + image).digest()
    return _run(binary, "verify", signature.hex(), public.hex(), digest.hex()) == "valid"


def _keypair(tmp_path: Path, name: str) -> tuple[Path, bytes]:
    private = tmp_path / f"{name}.pem"
    subprocess.run(
        [openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(private)],
        check=True,
        capture_output=True,
    )
    return private, _raw_public(private)


ORDER_L = 2**252 + 27742317777372353535851937790883648493


def test_a_signature_made_with_a_fresh_key_is_accepted_and_every_change_is_refused(
    checker, tmp_path
) -> None:
    private, public = _keypair(tmp_path, "good")
    image = bytes(range(256)) * 40 + b"stackchan"
    signature = _sign(private, image, tmp_path)
    assert len(signature) == 64
    assert _verify(checker, image, signature, public) is True
    other_private, other_public = _keypair(tmp_path, "other")
    assert _verify(checker, image, signature, other_public) is False  # another key
    assert (
        _verify(checker, image, _sign(other_private, image, tmp_path), public) is False
    )  # signed by another key
    for position in (0, 5, len(image) // 2, len(image) - 1):
        altered = bytearray(image)
        altered[position] ^= 0x01
        assert _verify(checker, bytes(altered), signature, public) is False, (
            position
        )  # the image changed after signing
    assert _verify(checker, image + b"\0", signature, public) is False  # a longer image
    assert _verify(checker, image[:-1], signature, public) is False  # a cut image
    for bit in list(range(0, 64 * 8, 29)):  # one flipped bit anywhere in R or S
        broken = bytearray(signature)
        broken[bit // 8] ^= 1 << (bit % 8)
        assert _verify(checker, image, bytes(broken), public) is False, bit


def test_a_second_encoding_of_a_valid_signature_is_refused(checker, tmp_path) -> None:
    """S + L verifies in a lax checker; the firmware's check refuses any S that is not below the group order."""
    private, public = _keypair(tmp_path, "malleable")
    image = b"image bytes " * 100
    signature = _sign(private, image, tmp_path)
    s = int.from_bytes(signature[32:], "little")
    assert s < ORDER_L
    twin = signature[:32] + (s + ORDER_L).to_bytes(32, "little")
    assert _verify(checker, image, signature, public) is True
    assert _verify(checker, image, twin, public) is False


def test_empty_zero_and_wrong_sized_inputs_are_refused(checker, tmp_path) -> None:
    private, public = _keypair(tmp_path, "sizes")
    image = b"x" * 64
    signature = _sign(private, image, tmp_path)
    assert _verify(checker, image, b"", public) is False
    assert _verify(checker, image, signature[:63], public) is False
    assert _verify(checker, image, bytes(64), public) is False  # an all-zero signature
    assert _verify(checker, image, signature, bytes(32)) is False  # an all-zero key
    assert _run(checker, "verify", "zz", public.hex(), "00" * 64) == "invalid"  # not hex


def test_the_build_key_is_read_from_the_option_or_there_is_none(checker, tmp_path) -> None:
    assert _run(checker, "key") == "none"  # no key built in: no update is accepted
    src = checker.parent / "firmware/xiaozhi-esp32/main"
    for value, expected in (
        ("ab" * 32, "ab" * 32),
        ("AB" * 32, "ab" * 32),
        ("ab" * 31, "none"),
        ("zz" * 32, "none"),
        ("", "none"),
    ):
        binary = tmp_path / f"keyed_{abs(hash(value))}"
        built = subprocess.run(
            ["c++", "-std=c++17", f"-DCONFIG_STACKCHAN_UPDATE_PUBKEY=\"{value}\"", f"-I{src}", str(HERE / "firmware/update_verify_check.cc"), str(src / "update_verify.cc"), "-o", str(binary)],
            capture_output=True, text=True,
        )  # fmt: skip
        assert built.returncode == 0, built.stderr
        assert _run(binary, "key") == expected, value


def test_the_paired_host_rule_and_the_slot_rule(checker) -> None:
    paired = "ws://192.0.2.1:8000/xiaozhi/v1/"
    for url, expected in (
        ("http://192.0.2.1:8767/firmware/aa/tok", "1"),
        ("https://192.0.2.1/firmware/aa/tok", "1"),
        ("http://192.0.2.2:8767/firmware/aa/tok", "0"),  # another host
        ("http://evil@192.0.2.1/x", "0"),  # user info is never accepted
        ("ftp://192.0.2.1/x", "0"),  # only http and https
        ("192.0.2.1/x", "0"),  # no scheme
        ("http://192.0.2.1.example.com/x", "0"),  # a longer name that starts the same
    ):
        assert _run(checker, "paired", url, paired) == expected, url
    assert _run(checker, "host", "http://[2001:db8::1]:80/x") == "[2001:db8::1]"
    slot = 0x4F0000
    assert _run(checker, "fits", str(slot - slot // 5), str(slot)) == "1"  # exactly 80 percent
    assert _run(checker, "fits", str(slot - slot // 5 + 1), str(slot)) == "0"
    assert _run(checker, "fits", "0", str(slot)) == "0"


# ---- the same scenarios as test_stackchan_ota_unit.py, with the firmware's own code as the unit's checker ----------------


class RealCodeUnit(StandInUnit):
    """The stand-in unit with its three checks replaced by the firmware's compiled code."""

    binary: Path

    def _verify(self, image: bytes, signature: bytes) -> bool:
        return _verify(self.binary, image, signature, self.public_raw)

    def _start(self, args) -> str:
        if _run(self.binary, "paired", args["url"], "ws://192.0.2.1:8000/xiaozhi/v1/") != "1":
            return "Update refused: the image address is not the paired host. Start the update from the host the unit is paired with."
        if _run(self.binary, "fits", str(args["size"]), str(self.slot)) != "1":
            return "Update refused: the image would leave less than 20 percent of its slot free. Build a smaller image."
        return self._after_checks(args)

    def _after_checks(self, args) -> str:
        try:
            signature = self._fetch(args["url"] + ".sig")
        except Exception:
            return "Update refused: no valid signature file at the image address plus .sig. Nothing was installed."
        image = self._fetch(args["url"])
        if not self._verify(image, signature):
            return "Update refused: the signature does not match this image or the update key. Nothing was installed."
        inactive = "ota_1" if self.running == "ota_0" else "ota_0"
        self.written[inactive] = image
        self.boot_slot, self.next_version = inactive, args["version"]
        self.pending = True
        return ""


def _real_rig(checker, tmp_path, public_pem, private):
    server, unit, live = _rig(tmp_path, public=public_pem)
    real = RealCodeUnit(server, public_pem, tmp_path)
    real.binary = checker
    real.public_raw = _raw_public(private)
    server.call_device_tool = real.call
    return server, real, live


def test_the_host_serves_the_image_and_its_signature_once_each_and_the_real_check_accepts_them(
    checker, tmp_path
) -> None:
    folder, public, private = _signed_release(tmp_path)
    server, unit, live = _real_rig(checker, tmp_path, public, private)
    release = updater.load_release(folder, public_key=public)
    _push(live, release)
    assert (
        unit.pending is True
        and unit.written["ota_1"] == (folder / "stack-chan-maipai.bin").read_bytes()
    )
    unit.reboot(reaches_host=True)
    assert unit.running_version == "1.2.0" and unit.events == ["firmware_update_validated"]
    # one read each: the same addresses are gone after the unit fetched them
    assert not server._firmware_files


def test_a_tampered_image_a_wrong_key_and_a_missing_signature_install_nothing(
    checker, tmp_path
) -> None:
    folder, public, private = _signed_release(tmp_path)
    release = updater.load_release(folder, public_key=public)
    image_path = folder / "stack-chan-maipai.bin"
    # a signature file that does not belong to this image
    (folder / "stack-chan-maipai.bin.sig").write_bytes(_sign(private, b"another image", tmp_path))
    server, unit, live = _real_rig(checker, tmp_path, public, private)
    with pytest.raises(updater.UpdateRefused, match="signature does not match"):
        _push(live, release)
    assert unit.written == {} and unit.pending is False
    # a signature from another key
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    _f, _p, other_private = _signed_release(other_dir)
    (folder / "stack-chan-maipai.bin.sig").write_bytes(
        _sign(other_private, image_path.read_bytes(), tmp_path)
    )
    with pytest.raises(updater.UpdateRefused, match="signature does not match"):
        _push(live, release)
    assert unit.written == {}
    # the host serves the image with no .sig at all: the unit gets a 404 for it and installs nothing
    (folder / "stack-chan-maipai.bin.sig").unlink()
    token_url = server.serve_firmware_once(image_path, UNIT)
    request = SimpleNamespace(
        match_info={"device_id": UNIT, "token": token_url.rsplit("/", 1)[1] + ".sig"}
    )
    with pytest.raises(Exception) as missing:
        asyncio.run(server._serve_firmware_file(request))
    assert "404" in str(missing.value) or "Not Found" in str(missing.value)
    assert unit.written == {} and unit.pending is False


def test_the_unit_refuses_an_address_that_is_not_its_host_and_an_image_over_80_percent_of_the_slot(
    checker, tmp_path
) -> None:
    folder, public, private = _signed_release(tmp_path)
    release = updater.load_release(folder, public_key=public)
    server, unit, live = _real_rig(checker, tmp_path, public, private)
    server.advertised_vision_url = "http://192.0.2.9:8767/vision/x"  # the host serves from an address the unit is not paired with
    with pytest.raises(updater.UpdateRefused, match="not the paired host"):
        _push(live, release)
    assert unit.written == {}
