"""Travel with the private network (firmware patches TN01 to TN06): the pure choices in plain C, the key and address
shapes, the Noise byte order of the ported client, and the rules the patches must keep (no key in any file, every
patch has its header lines, the full ORDER names them in order)."""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware/patches"
C_DIR = HERE / "firmware"
TN = ["TN01-travel-private-network.patch", "TN02-travel-hub-route.patch", "TN03-travel-portal-fields.patch",
      "TN04-travel-memory-freeing.patch", "TN05-memory-gate-line.patch", "TN06-travel-trust-root.patch"]


def cc() -> str:
    found = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if found is None:
        pytest.skip("no C compiler on this machine")
    return found


def added_file(patch: Path, path: str) -> str:
    """One file as a patch adds it (every added line of that new file)."""
    text = patch.read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1]
    body = block.split("\n", 1)[1]
    lines = []
    for line in body.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def build_and_run(tmp_path: Path, source: Path, extra: list[str], name: str) -> subprocess.CompletedProcess[str]:
    binary = tmp_path / name
    build = subprocess.run(
        [cc(), "-std=c99", "-D_DEFAULT_SOURCE", "-Wall", "-Wextra", "-Werror", *extra, str(source), "-o", str(binary)],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    return subprocess.run([str(binary)], capture_output=True, text=True)


def test_the_travel_core_passes_its_c_test(tmp_path: Path):
    (tmp_path / "maipai_tailnet_core.h").write_text(
        added_file(PATCHES / TN[0], "firmware/main/hal/maipai_tailnet_core.h"))
    run = build_and_run(tmp_path, C_DIR / "tailnet_travel_test.c", [f"-I{tmp_path}"], "travel_core_test")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all checks passed" in run.stdout


def chacha_block(key: bytes, counter: int, nonce: bytes) -> bytes:
    def rotl(v: int, n: int) -> int:
        return ((v << n) & 0xFFFFFFFF) | (v >> (32 - n))

    state = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574, *struct.unpack("<8I", key), counter,
             *struct.unpack("<3I", nonce)]
    x = state[:]

    def qr(a: int, b: int, c: int, d: int) -> None:
        x[a] = (x[a] + x[b]) & 0xFFFFFFFF; x[d] = rotl(x[d] ^ x[a], 16)
        x[c] = (x[c] + x[d]) & 0xFFFFFFFF; x[b] = rotl(x[b] ^ x[c], 12)
        x[a] = (x[a] + x[b]) & 0xFFFFFFFF; x[d] = rotl(x[d] ^ x[a], 8)
        x[c] = (x[c] + x[d]) & 0xFFFFFFFF; x[b] = rotl(x[b] ^ x[c], 7)

    for _ in range(10):
        qr(0, 4, 8, 12); qr(1, 5, 9, 13); qr(2, 6, 10, 14); qr(3, 7, 11, 15)
        qr(0, 5, 10, 15); qr(1, 6, 11, 12); qr(2, 7, 8, 13); qr(3, 4, 9, 14)
    return struct.pack("<16I", *[(x[i] + state[i]) & 0xFFFFFFFF for i in range(16)])


def poly1305(key: bytes, msg: bytes) -> bytes:
    r = int.from_bytes(key[:16], "little") & 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF
    s = int.from_bytes(key[16:], "little")
    p = (1 << 130) - 5
    acc = 0
    for i in range(0, len(msg), 16):
        chunk = msg[i:i + 16]
        acc = ((acc + int.from_bytes(chunk + b"\x01", "little")) * r) % p
    return ((acc + s) & ((1 << 128) - 1)).to_bytes(16, "little")


def aead_seal(key: bytes, nonce12: bytes, ad: bytes, pt: bytes) -> bytes:
    """RFC 8439 section 2.8, written independently of the C code."""
    otk = chacha_block(key, 0, nonce12)[:32]
    ct = b""
    for i in range(0, len(pt), 64):
        block = chacha_block(key, 1 + i // 64, nonce12)
        ct += bytes(a ^ b for a, b in zip(pt[i:i + 64], block))

    def pad16(b: bytes) -> bytes:
        return b + b"\x00" * (-len(b) % 16)

    mac = poly1305(otk, pad16(ad) + pad16(ct) + struct.pack("<QQ", len(ad), len(ct)))
    return ct + mac


def test_the_reference_matches_the_rfc_vector():
    key = bytes(range(0x80, 0xA0))
    nonce = bytes.fromhex("070000004041424344454647")
    ad = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
    pt = (b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, "
          b"sunscreen would be it.")
    out = aead_seal(key, nonce, ad, pt)
    assert out[:4].hex() == "d31a8d34"
    assert out[-16:].hex() == "1ae10b594f09e26a7e902ecbd0600691"


def microlink_dir() -> Path | None:
    env = os.environ.get("MAIPAI_MICROLINK_DIR")
    candidates = [Path(env)] if env else []
    candidates.append(Path.home() / "esp/maipai-deps/microlink")
    for c in candidates:
        if (c / "components/microlink/components/wireguard_lwip/src/crypto/refc/chacha20poly1305.c").exists():
            return c
    return None


def test_the_noise_handshake_keeps_its_counter_byte_order(tmp_path: Path):
    ml = microlink_dir()
    if ml is None:
        pytest.skip("the private-network client is not downloaded (bash scripts/fw-tailnet.sh)")
    wg = ml / "components/microlink/components/wireguard_lwip/src"
    refc = wg / "crypto/refc"
    run = build_and_run(
        tmp_path, C_DIR / "noise_aead_test.c",
        ["-Wno-sign-compare", "-Wno-unused-parameter", f"-I{refc}", f"-I{wg}", str(refc / "chacha20poly1305.c"), str(refc / "chacha20.c"), str(refc / "poly1305-donna.c")],
        "noise_aead_test",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    lines = [ln for ln in run.stdout.splitlines() if ln.strip()]
    assert len(lines) == 16
    for ln in lines:
        key_h, counter, ad_h, pt_h, ct_h = (ln.split(" ") + [""])[:5] if ln.count(" ") == 4 else (None,) * 5
        assert key_h is not None, ln
        # Tailscale's Noise nonce: four zero bytes then the counter, big endian.
        nonce12 = b"\x00" * 4 + int(counter).to_bytes(8, "big")
        want = aead_seal(bytes.fromhex(key_h), nonce12, bytes.fromhex(ad_h), bytes.fromhex(pt_h))
        assert ct_h == want.hex(), ln


def test_the_library_patch_keeps_the_swap():
    text = (ROOT / "firmware/tailnet/microlink.patch").read_text(errors="replace")
    assert text.count("__builtin_bswap64(nonce)") == 2
    assert text.splitlines()[0].startswith("# Intent:")


def patch_headers(path: Path) -> dict[str, str]:
    heads: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("diff --git"):
            break
        m = re.match(r"# (Intent|Placement|Upstream|Check after a flash|Kconfig): (.*)", line)
        if m:
            heads[m.group(1)] = m.group(2)
    return heads


def test_every_travel_patch_has_its_header_and_is_in_order():
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(name) for name in TN]
    assert positions == sorted(positions)
    for name in TN:
        heads = patch_headers(PATCHES / name)
        for need in ("Intent", "Placement", "Upstream"):
            assert heads.get(need), f"{name} has no # {need}: line"


def test_no_key_or_address_is_in_any_travel_file():
    files = [PATCHES / n for n in TN] + [ROOT / "firmware/tailnet/PIN", ROOT / "firmware/tailnet/microlink.patch",
                                         ROOT / "scripts/fw-tailnet.sh"]
    for f in files:
        text = f.read_text(errors="replace")
        # A pairing key is "tskey-" followed by a long run of letters and digits; the code only names the prefix.
        assert re.search(r"tskey-[A-Za-z0-9_-]{10,}", text) is None, f"{f.name}: a key"
        # No real private-network address: only the range itself and the documented example may appear.
        found = set(re.findall(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b", text))
        assert found <= {"100.64.0.0", "100.64.0.7", "100.127.255.255", "100.64.0.1", "100.64.0.9"}, f"{f.name}: {found}"


def test_the_core_header_names_no_default_key_or_hub_address():
    defaults = added_file(PATCHES / TN[0], "firmware/sdkconfig.tailnet.defaults")
    kconfig = (PATCHES / TN[0]).read_text()
    assert "AUTHKEY" not in defaults and "PEER_IP" not in defaults
    assert "STACKCHAN_TAILNET_AUTHKEY" not in kconfig and "STACKCHAN_TAILNET_PEER_IP" not in kconfig
    assert "tskey-" not in defaults


def portal_files(tmp_path: Path) -> Path:
    """The two portal files as the patches P01 to P05 and TN03 leave them (git apply, only those two files)."""
    work = tmp_path / "portal"
    work.mkdir()
    for name in ["P01-portal-page.patch", "P02-portal-routes.patch", "P03-portal-protect.patch",
                 "P04-portal-language.patch", "P05-portal-wire.patch", TN[2]]:
        done = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "--include=firmware/portal/maipai_portal_core.h",
             "--include=firmware/portal/maipai_portal_page.h", str(PATCHES / name)],
            cwd=work, capture_output=True, text=True,
        )
        assert done.returncode == 0, f"{name}: {done.stderr}"
    return work / "firmware/portal"


PORTAL_C = r"""
#include <stdio.h>
#include "maipai_portal_core.h"
#include "maipai_portal_page.h"
int main(void) {
    printf("%d %d\n", (int)MP_S_COUNT, (int)sizeof(mp_page));
    for (int l = 0; l < 2; l++) { char buf[2048]; size_t n = mp_table_json(l, buf, sizeof(buf)); printf("%d %zu\n", l, n); }
    printf("%s | %s | %s\n", mp_str(0, MP_S_TKEY), mp_str(0, MP_S_TPEER), mp_str(1, MP_S_BADTKEY));
    return 0;
}
"""


def test_the_setup_page_has_the_two_travel_fields_within_its_budget(tmp_path: Path):
    d = portal_files(tmp_path)
    (tmp_path / "t.cc").write_text(PORTAL_C)
    cxx = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
    if cxx is None:
        pytest.skip("no C++ compiler on this machine")
    built = subprocess.run([cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", f"-I{d}", str(tmp_path / "t.cc"), "-o",
                            str(tmp_path / "probe")], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(tmp_path / "probe")], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    first, *rest = run.stdout.splitlines()
    count, page = map(int, first.split())
    assert count == 18
    for line in rest[:2]:
        lang, n = map(int, line.split())
        assert 0 < n < 2048, line
        assert page + n <= 5 * 1024, f"language {lang}: page and table are {page + n} bytes"
    assert "Travel key" in rest[2] and "Clave de viaje" not in rest[2]
    text = (d / "maipai_portal_page.h").read_text()
    assert 'id=k type=password' in text  # the key is typed hidden
    assert "tkey" in text and "tpeer" in text


def test_the_setup_page_never_logs_or_echoes_the_key():
    text = (PATCHES / TN[2]).read_text()
    added = "\n".join(line for line in text.splitlines() if line.startswith("+"))
    assert "ESP_LOG" not in added or "travel_key" not in "".join(
        line for line in added.splitlines() if "ESP_LOG" in line)
    assert "std::fill(travel_key" in added  # the copy of the key is zeroed after saving
