# ruff: noqa: E501
"""Every check that rejects a bad update image, run through the unit's own code and compared with the host's (docs/dev/update-checks.md is the table; playground report 17).

The unit side is the firmware's real code compiled for the PC: update_verify.cc (the Ed25519 check over the 56 header bytes, the trusted key, the paired host rule, the slot rule) and
maipai_updatehdr_core.h (magic, reserved bytes, build number against the floor, image length and SHA-256, streamed). The host side is firmware/update_header.py (what the release script
makes and the host serves). Each row builds a package and an image, asks the unit, asks the host, and the two must agree on accept or refuse; the unit's reason is pinned too."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir
from test_unit_update_check import _keypair, _run, _verify, checker  # noqa: F401  (checker is a fixture)

from maipai_body.bodies.stackchan.firmware.update_header import HEADER_LEN, MAGIC, build_header, sign_package, verify_package
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
needs_cc = pytest.mark.skipif(shutil.which("cc") is None or shutil.which("c++") is None, reason="no C compiler on this machine")
OK, SHORT, MAGIC_BAD, RESERVED, BUILD_ZERO, NOT_NEWER, LENGTH, HASH = range(8)   # MUH_* in maipai_updatehdr_core.h
IMAGE = bytes(range(256)) * 20 + b"stackchan image"
SIG_BAD = "signature"


@pytest.fixture(scope="module")
def core_binary(tmp_path_factory):
    binary = tmp_path_factory.mktemp("updatehdr") / "updatehdr"
    built = subprocess.run(["cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", f"-I{cores_dir(tmp_path_factory)}", str(HERE / "firmware" / "updatehdr_core_test.c"), "-o", str(binary)], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    return binary


def _header(build=7, image=IMAGE, length=None, sha=None, magic=MAGIC, reserved=bytes(8)):
    return magic + build.to_bytes(4, "little") + (len(image) if length is None else length).to_bytes(4, "little") + (hashlib.sha256(image).digest() if sha is None else sha) + reserved


def unit_verdict(checker_bin, core_bin, package: bytes, image: bytes, public: bytes, floor: int) -> str | int:
    """What the unit says: the signature stage first (its Ed25519 code), then the header and image stage (its updatehdr core). A string is a signature refusal, a number is a MUH_* code."""
    header, signature = package[:HEADER_LEN], package[HEADER_LEN:]
    if not _verify(checker_bin, header, signature, public):
        return SIG_BAD
    line = f"{package.hex()} {image.hex() or '-'} {floor if floor else -1}\n"
    return int(subprocess.run([str(core_bin)], input=line, capture_output=True, text=True).stdout.split()[0])


def _flip(b: bytes, i: int) -> bytes:
    out = bytearray(b)
    out[i] ^= 1
    return bytes(out)


@needs_cc
def test_every_check_that_rejects_a_bad_image_agrees_between_the_unit_and_the_host(checker, core_binary, tmp_path):
    good_key, good_pub = _keypair(tmp_path, "good")
    other_key, _other_pub = _keypair(tmp_path, "other")
    pub_pem = tmp_path / "good.pub.pem"
    pub_pem.write_bytes(subprocess.run([openssl_cli(), "pkey", "-in", str(good_key), "-pubout"], check=True, capture_output=True).stdout)

    def package(header: bytes, key=good_key) -> bytes:
        return sign_package(header, key)

    valid = package(_header())
    rows = [
        # name, package, image, floor (highest build confirmed or compiled in), expected unit verdict
        ("valid", valid, IMAGE, 0, OK),
        ("header signature altered", _flip(valid, HEADER_LEN + 3), IMAGE, 0, SIG_BAD),
        ("header signature from another key", package(_header(), other_key), IMAGE, 0, SIG_BAD),
        ("header changed after signing", _flip(valid, 8), IMAGE, 0, SIG_BAD),
        ("build number equal to the one installed", valid, IMAGE, 7, NOT_NEWER),
        ("build number below the one installed", valid, IMAGE, 12, NOT_NEWER),
        ("build number below the one compiled into the image", package(_header(build=8)), IMAGE, 9, NOT_NEWER),
        ("build number zero", package(_header(build=0)), IMAGE, 0, BUILD_ZERO),
        ("image longer than the header says", valid, IMAGE + b"x", 0, LENGTH),
        ("image cut short (truncated download)", valid, IMAGE[:-1], 0, LENGTH),
        ("image empty", valid, b"", 0, LENGTH),
        ("same length, one byte changed", valid, _flip(IMAGE, 100), 0, HASH),
        ("header length field wrong", package(_header(length=len(IMAGE) + 5)), IMAGE, 0, LENGTH),
        ("header hash field wrong", package(_header(sha=bytes(32))), IMAGE, 0, HASH),
        ("header magic wrong", package(_header(magic=b"MPUH2\0\0\0")), IMAGE, 0, MAGIC_BAD),
        ("reserved bytes not zero", package(_header(reserved=b"\0\0\0\0\0\0\0\1")), IMAGE, 0, RESERVED),
    ]
    for name, pkg, image, floor, expected in rows:
        unit = unit_verdict(checker, core_binary, pkg, image, good_pub, floor)
        assert unit == expected, f"{name}: the unit said {unit!r}, expected {expected!r}"
        host = verify_package(pkg, image, pub_pem, installed_build=floor if floor else None)
        assert host.ok == (unit == OK), f"{name}: the unit {'accepts' if unit == OK else 'refuses'} it, the host {'accepts' if host.ok else 'refuses'} it ({host.reason})"


@needs_cc
def test_a_package_of_the_wrong_size_is_refused_by_the_host_and_the_unit_fetches_exactly_120_bytes(tmp_path):
    """The unit's fetch_small() refuses a header or signature file that is not 56 and 64 bytes (device code in ota.cc: asserted by reading the patch); the host refuses a package that is not 120."""
    key, _pub = _keypair(tmp_path, "size")
    pub = tmp_path / "size.pub.pem"
    pub.write_bytes(subprocess.run([openssl_cli(), "pkey", "-in", str(key), "-pubout"], check=True, capture_output=True).stdout)
    pkg = sign_package(build_header(7, IMAGE), key)
    for cut in (pkg[:-1], pkg + b"\0", b"", pkg[:HEADER_LEN]):
        assert not verify_package(cut, IMAGE, pub, installed_build=None).ok
    patch = (ROOT / "firmware" / "patches" / "SF25-signed-update-header-and-build-number.patch").read_text()
    assert "GetBodyLength() != want" in patch and "uint8_t hdr_bytes[MUH_HDR_LEN], sig_bytes[MUH_SIG_LEN]" in patch


@needs_cc
def test_the_unit_refuses_an_update_with_no_trusted_key_and_one_from_a_host_that_is_not_its_paired_host(checker):
    assert _run(checker, "key") == "none"   # no key built in: nothing verifies, so nothing installs
    paired = "ws://192.0.2.1:8000/xiaozhi/v1/"
    assert _run(checker, "paired", "http://192.0.2.1:8767/firmware/aa/tok", paired) == "1"
    assert _run(checker, "paired", "http://192.0.2.99:8767/firmware/aa/tok", paired) == "0"   # an address that is not the paired host
    assert _run(checker, "paired", "http://192.0.2.1.example.com/x", paired) == "0"   # a look-alike host name
    assert _run(checker, "paired", "http://evil@192.0.2.1/x", paired) == "0"   # credentials in the address


@needs_cc
def test_the_unit_refuses_an_image_that_does_not_fit_its_slot(checker):
    slot = 0x4F0000
    assert _run(checker, "fits", str(slot - slot // 5), str(slot)) == "1"
    assert _run(checker, "fits", str(slot - slot // 5 + 1), str(slot)) == "0"
    assert _run(checker, "fits", "0", str(slot)) == "0"


@needs_cc
def test_the_unit_refuses_a_build_number_of_2_to_the_31_or_more(checker, core_binary, tmp_path):
    key, pub = _keypair(tmp_path, "big")
    pkg = sign_package(_header(build=2**31), key)
    assert unit_verdict(checker, core_binary, pkg, IMAGE, pub, 0) == BUILD_ZERO
