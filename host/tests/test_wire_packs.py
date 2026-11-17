# ruff: noqa: E501
"""The pack and picture paths against the firmware's own cores (patch FM06 tests; review risk 5, "tests that never ran").

The host's real push code (PackService, PictureService) talks to ``pack_wire_driver.c``: a program that runs the unit's own C cores
(maipai_pack_core.h, maipai_picface_core.h) behind the same tool names and rules. So fragments of every size, a dropped link
(before a piece arrives, and after it arrives with the reply lost), a reboot and a reconnect are exercised end to end, not
against a Python stand-in. Only the zlib probe and the screen are not covered here (they need the unit)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import zlib
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pytest

from firmware_order_cores import cores_dir
from maipai_body import packs
from maipai_body import picture_faces as pf
from maipai_body.hal.errors import BodyLost
from maipai_body.unit_tools import ToolProbe

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
UNIT = "aa:bb:cc:00:20:01"

pytestmark = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")


def _added(patch: str, path: str) -> str:
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


@pytest.fixture(scope="session")
def driver(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("wire")
    for name in ("maipai_pack_core.h", "maipai_lang_core.h", "maipai_phrasepack_core.h", "maipai_sounds_core.h"):  # as ORDER leaves them (K10 to K12)
        (root / name).write_text((cores_dir(tmp_path_factory) / name).read_text())
    (root / "maipai_picface_core.h").write_text(
        _added("H03-picture-face-core.patch", "firmware/main/hal/maipai_picface_core.h")
    )
    binary = root / "driver"
    built = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{root}", str(HERE / "firmware" / "pack_wire_driver.c"), "-o", str(binary), "-lz"],
        capture_output=True, text=True,
    )  # fmt: skip
    assert built.returncode == 0, built.stderr
    return binary


class WireUnit:
    """The unit as the host sees it: a callable like call_device_tool, answered by the firmware cores in a child process.

    ``plan`` maps the 1-based number of a call (counting every call made through this object) to what the link does to it:
    "drop_before" (the call never reaches the unit) or "drop_after" (it is done, the reply is lost). Both raise BodyLost."""

    def __init__(self, binary: Path) -> None:
        self.proc = subprocess.Popen(
            [str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1
        )
        self.count = 0
        self.plan: dict[int, str] = {}
        self.tamper: dict[
            int, bytes
        ] = {}  # call number -> bytes to put in place of the piece (a damaged frame)
        self.log: list[tuple[str, dict]] = []

    def raw(self, name: str, args: dict) -> dict:
        parts = [name]
        for key, value in args.items():
            parts.append(
                f"{key}={quote(str(value if not isinstance(value, bool) else str(value).lower()), safe='')}"
            )
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(" ".join(parts) + "\n")
        return json.loads(self.proc.stdout.readline())

    def __call__(
        self, name: str, args: dict, *, device_id: str | None = None, timeout: float = 4.0
    ) -> object:
        self.count += 1
        fate = self.plan.get(self.count)
        if fate == "drop_before":
            raise BodyLost("the link dropped")
        sent = dict(args)
        if self.count in self.tamper:
            sent["b64"] = base64.b64encode(self.tamper[self.count]).decode()
        self.log.append((name, args))
        reply = self.raw(name, sent)
        if fate == "drop_after":
            raise BodyLost("the link dropped before the reply")
        return reply

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        self.proc.wait(timeout=5)


@pytest.fixture
def unit(driver):
    wire = WireUnit(driver)
    yield wire
    wire.close()


def _service(tmp_path: Path, wire: WireUnit, chunk: int) -> packs.PackService:
    library = packs.PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")
    return packs.PackService(
        ToolProbe(wire), library, packs.ActiveStore(tmp_path / "active.json"), chunk=chunk
    )


def _add(
    service: packs.PackService, size: int, name: str = "Pixel", kind: str = "look"
) -> packs.Pack:
    pack = packs.make_pack(kind, name, os.urandom(size))
    service.library.add(pack)
    return pack


def _held(wire: WireUnit) -> dict:
    return wire.raw("self.pack.status", {"type": "look"})


# ---- packs ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("chunk", [1, 7, 400, 1023, 4096])
def test_a_pack_arrives_whole_whatever_the_piece_size(tmp_path, unit, chunk) -> None:
    service = _service(tmp_path, unit, chunk)
    pack = _add(service, 2000 + chunk % 13)  # sizes that are not a multiple of the piece
    reply = service.activate(UNIT, "look", service.library.list("look")[0]["id"])
    assert reply["pushed"] is True, reply
    held = _held(unit)
    assert held["held"] is True and held["sha256"] == pack.sha256 and held["size"] == pack.size
    pieces = [a for n, a in unit.log if n == "self.pack.data"]
    assert [p["at"] for p in pieces] == list(
        range(0, pack.size, chunk)
    )  # in order, nothing skipped or repeated


@pytest.mark.parametrize("lost", ["drop_before", "drop_after"])
def test_a_link_that_drops_mid_pack_leaves_nothing_held_and_the_reconnect_sends_it_whole(
    tmp_path, unit, lost
) -> None:
    service = _service(tmp_path, unit, 400)
    pack = _add(service, 3000)
    pid = service.library.list("look")[0]["id"]
    service.active.set(UNIT, "look", pid)
    # calls: 1 probe (status), 2 begin, 3.. data; the link fails on the 5th (the third piece)
    unit.plan = {5: lost}
    with pytest.raises(BodyLost):
        service.activate(UNIT, "look", pid)
    assert _held(unit)["held"] is False  # a half pack is never held
    unit.plan = {}
    service.sync(UNIT)  # the unit connects again
    held = _held(unit)
    assert held["held"] is True and held["sha256"] == pack.sha256
    # the second push began again from zero: no piece was refused as out of order, and the pieces ran 0, 400, 800 ...
    last = [a["at"] for n, a in unit.log if n == "self.pack.data"][-8:]
    assert last == list(range(0, 3000, 400))


def test_a_reboot_between_two_syncs_is_healed_by_the_next_sync_and_a_held_pack_is_not_sent_twice(
    tmp_path, unit
) -> None:
    service = _service(tmp_path, unit, 700)
    pack = _add(service, 2500)
    pid = service.library.list("look")[0]["id"]
    service.activate(UNIT, "look", pid)
    sent = sum(1 for n, _ in unit.log if n == "self.pack.begin")
    service.sync(UNIT)
    assert (
        sum(1 for n, _ in unit.log if n == "self.pack.begin") == sent
    )  # it already holds the same pack
    assert (
        unit.raw("reboot", {})["ok"] is True
    )  # a restart: RAM is gone (the flash cache is the unit's own, tested in packcache_core_test.c)
    service.sync(UNIT)
    assert _held(unit)["sha256"] == pack.sha256
    assert sum(1 for n, _ in unit.log if n == "self.pack.begin") == sent + 1


def test_the_cores_refuse_a_piece_that_repeats_arrives_early_or_runs_past_the_end(unit) -> None:
    payload = os.urandom(900)
    sha = hashlib.sha256(payload).hexdigest()
    b64 = lambda part: base64.b64encode(part).decode()  # noqa: E731
    assert (
        unit.raw(
            "self.pack.begin",
            {"type": "look", "name": "X", "version": 1, "size": 900, "sha256": sha},
        )["ok"]
        is True
    )
    assert unit.raw("self.pack.data", {"at": 0, "b64": b64(payload[:300])})["ok"] is True
    again = unit.raw(
        "self.pack.data", {"at": 0, "b64": b64(payload[:300])}
    )  # the reply was lost and the piece is sent again
    assert again["ok"] is False and again["code"] == "order"
    early = unit.raw("self.pack.data", {"at": 600, "b64": b64(payload[600:])})
    assert early["ok"] is False and early["code"] == "order"
    assert unit.raw("self.pack.commit", {})["code"] == "short"  # not everything arrived
    assert (
        unit.raw(
            "self.pack.begin",
            {"type": "look", "name": "X", "version": 1, "size": 900, "sha256": sha},
        )["ok"]
        is True
    )
    assert unit.raw("self.pack.data", {"at": 0, "b64": b64(payload[:300])})["ok"] is True
    assert (
        unit.raw("self.pack.data", {"at": 300, "b64": b64(payload[300:] + b"extra")})["code"]
        == "range"
    )  # runs past the end
    assert unit.raw("self.pack.data", {"at": 300, "b64": b64(payload[300:])})["ok"] is True
    assert unit.raw("self.pack.commit", {})["ok"] is True
    assert _held(unit)["sha256"] == sha


def test_a_damaged_pack_is_refused_at_commit_and_never_held(unit) -> None:
    payload = os.urandom(500)
    sha = hashlib.sha256(payload).hexdigest()
    unit.raw(
        "self.pack.begin", {"type": "filler", "name": "Y", "version": 1, "size": 500, "sha256": sha}
    )
    bad = bytearray(payload)
    bad[250] ^= 0xFF
    unit.raw("self.pack.data", {"at": 0, "b64": base64.b64encode(bytes(bad)).decode()})
    refused = unit.raw("self.pack.commit", {})
    assert (
        refused["ok"] is False and refused["code"] == "mismatch" and "damaged" in refused["error"]
    )
    assert _held(unit)["held"] is False


def test_the_host_and_the_unit_agree_on_every_size_gate(unit) -> None:
    for kind, limit in packs.MAX_BYTES.items():
        ok = unit.raw(
            "self.pack.begin",
            {"type": kind, "name": "Z", "version": 1, "size": limit, "sha256": "0" * 64},
        )
        over = unit.raw(
            "self.pack.begin",
            {"type": kind, "name": "Z", "version": 1, "size": limit + 1, "sha256": "0" * 64},
        )
        assert ok["ok"] is True, kind
        assert over["ok"] is False and over["code"] == "size", kind


# ---- picture faces ----------------------------------------------------------------------------------------


def _gradient(width: int, height: int, seed: int = 0) -> bytes:
    yy, xx = np.mgrid[0:height, 0:width]
    img = np.zeros((height, width, 4), dtype=np.uint8)
    img[..., 0] = (xx * 255 // max(width - 1, 1) + seed) % 256
    img[..., 1] = yy * 255 // max(height - 1, 1)
    img[..., 2] = 90
    img[..., 3] = 255
    return img.tobytes()


def _pictures(
    tmp_path: Path, wire: WireUnit, chunk: int, slots=("neutral", "happy")
) -> pf.PictureService:
    service = pf.PictureService(wire, pf.PictureStore(tmp_path / "pics"), chunk=chunk)
    for number, slot in enumerate(slots):
        service.add_picture(UNIT, slot, 0, 640, 480, _gradient(640, 480, number * 40), "en")
    return service


@pytest.mark.parametrize("chunk", [333, 700, 4096])
def test_a_picture_pack_arrives_byte_for_byte_in_pieces_of_any_size(tmp_path, unit, chunk) -> None:
    service = _pictures(tmp_path, unit, chunk)
    sent = service.send(UNIT, "en")
    assert sent["sent"] is True and sent["frames"] == 2
    status = unit.raw("self.facepic.status", {})
    assert status["held"] is True and status["frames"] == 2 and status["bytes"] == sent["bytes"]
    stored = service.store.load(UNIT)
    for slot in ("neutral", "happy"):
        frame = stored.frames[slot][0]
        held = unit.raw("self.facepic.frame_crc", {"slot": slot, "index": 0})
        assert (
            held["done"] is True and held["crc"] == f"{zlib.crc32(frame.payload) & 0xFFFFFFFF:08x}"
        )
    data = [a for n, a in unit.log if n == "self.facepic.data" and a["slot"] == "neutral"]
    assert [d["at"] for d in data] == list(range(0, stored.frames["neutral"][0].size, chunk))


@pytest.mark.parametrize("lost", ["drop_before", "drop_after"])
def test_a_picture_push_cut_in_the_middle_is_not_held_and_goes_out_whole_when_the_unit_reconnects(
    tmp_path, unit, lost
) -> None:
    service = _pictures(tmp_path, unit, 700)
    unit.plan = {9: lost}  # begin, frame, then data pieces: the link fails inside the first frame
    first = service.send(UNIT, "en")
    assert first["sent"] is False  # the host remembers it is owed
    assert unit.raw("self.facepic.status", {})["held"] is False
    unit.plan = {}
    service.sync(UNIT)
    status = unit.raw("self.facepic.status", {})
    assert status["held"] is True and status["frames"] == 2


def test_a_reboot_loses_the_ram_copy_and_the_next_connect_sends_it_again(tmp_path, unit) -> None:
    service = _pictures(tmp_path, unit, 4096)
    service.send(UNIT, "en")
    begins = sum(1 for n, _ in unit.log if n == "self.facepic.begin")
    service.sync(UNIT)
    assert (
        sum(1 for n, _ in unit.log if n == "self.facepic.begin") == begins
    )  # held and the same: nothing sent
    unit.raw("reboot", {})
    service.sync(UNIT)
    assert sum(1 for n, _ in unit.log if n == "self.facepic.begin") == begins + 1
    assert unit.raw("self.facepic.status", {})["held"] is True


def test_a_piece_damaged_on_the_way_is_caught_by_the_unit_and_the_resend_works(
    tmp_path, unit
) -> None:
    service = _pictures(tmp_path, unit, 700)
    # call numbers: 1 begin, 2 frame, 3 first data piece of the neutral frame, ...; damage one byte of the third piece
    third = 5
    stored = service.store.load(UNIT).frames["neutral"][0]
    piece = bytearray(stored.payload[1400:2100])
    piece[10] ^= 0x55
    unit.tamper = {third: bytes(piece)}
    with pytest.raises(pf.PictureError):
        service.send(UNIT, "en")  # the unit's CRC check refuses the finished frame
    assert unit.raw("self.facepic.status", {})["held"] is False
    unit.tamper = {}
    assert service.send(UNIT, "en")["sent"] is True
    assert unit.raw("self.facepic.status", {})["held"] is True


def test_the_unit_refuses_a_pack_with_no_neutral_picture_in_its_own_words(tmp_path, unit) -> None:
    service = pf.PictureService(unit, pf.PictureStore(tmp_path / "pics"), chunk=700)
    service.add_picture(UNIT, "happy", 0, 640, 480, _gradient(640, 480), "en")
    with pytest.raises(pf.PictureError) as error:
        service.send(UNIT, "en")
    assert "neutral" in str(error.value).lower()
    assert unit.raw("self.facepic.status", {})["held"] is False
