# ruff: noqa: E501
"""Picture faces (firmware patches H03 and H04) and the fluid face (H02): the C cores, the host module, the page.

Every picture here is made from plain shapes in the test; nothing is a photograph, and nothing real is stored in this
repository.
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import zlib
from pathlib import Path

import numpy as np
import pytest

from maipai_body import picture_faces as pf
from maipai_body.hal.errors import BodyLost

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
EM = chr(0x2014)  # written this way so the hygiene check never sees the character in this file


# ---- the firmware patches and their C cores --------------------------------------------------------------


def _file_from_patch(patch: str, path: str) -> str:
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1]
    body = block.split("\n", 1)[1]  # drop the @@ line
    lines = []
    for line in body.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def _build_and_run(tmp_path: Path, test_name: str, headers: dict[str, str], marker: str) -> None:
    for name, text in headers.items():
        (tmp_path / name).write_text(text)
    binary = tmp_path / test_name
    build = subprocess.run(
        [
            "cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
            f"-I{tmp_path}", str(HERE / "firmware" / f"{test_name}.c"), "-o", str(binary), "-lm",
        ],
        capture_output=True,
        text=True,
    )  # fmt: skip
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert marker in run.stdout


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_fluid_face_core_c_tests_pass(tmp_path: Path) -> None:
    header = _file_from_patch(
        "H02-face-fluid-motion.patch", "firmware/main/hal/maipai_facefx_core.h"
    )
    _build_and_run(
        tmp_path, "facefx_core_test", {"maipai_facefx_core.h": header}, "facefx core: all passed"
    )


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_picture_face_core_c_tests_pass(tmp_path: Path) -> None:
    header = _file_from_patch(
        "H03-picture-face-core.patch", "firmware/main/hal/maipai_picface_core.h"
    )
    _build_and_run(
        tmp_path, "picface_core_test", {"maipai_picface_core.h": header}, "picface core: all passed"
    )


def test_the_h_patches_are_in_order_with_their_header_lines() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    names = [
        "H01-face-bench-tools.patch",
        "H02-face-fluid-motion.patch",
        "H03-picture-face-core.patch",
        "H04-picture-face-unit.patch",
    ]
    positions = [order.index(n) for n in names]
    assert positions == sorted(positions)
    assert positions[-1] == positions[0] + 3, "the four patches replay together"
    for name in names:
        head = (PATCHES / name).read_text().split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:"):
            assert key in head, f"{name} has no '{key}' line"


def test_the_bench_tools_exist_only_behind_the_bench_switch() -> None:
    bench = _file_from_patch("H01-face-bench-tools.patch", "firmware/main/hal/maipai_facebench.cc")
    assert bench.count("#if CONFIG_MAIPAI_FACE_BENCH") == 1
    assert bench.rstrip().endswith("#endif")
    kconfig = (PATCHES / "H01-face-bench-tools.patch").read_text()
    assert "default n" in kconfig.split("config MAIPAI_FACE_BENCH", 1)[1].split("help", 1)[0]
    unit = _file_from_patch("H04-picture-face-unit.patch", "firmware/main/hal/maipai_picface.cc")
    assert '#if CONFIG_MAIPAI_FACE_BENCH\n    mcp.AddTool("self.facepic.bench_force"' in unit
    assert (
        "s_bench_ignore_privacy.load()" in unit and unit.count("#if CONFIG_MAIPAI_FACE_BENCH") >= 2
    )


def test_a_picture_never_covers_a_privacy_look_the_clock_or_a_ringing_timer() -> None:
    unit = _file_from_patch("H04-picture-face-unit.patch", "firmware/main/hal/maipai_picface.cc")
    assert "maipai_privacy_bits() != 0" in unit
    assert "maipai_timers_ringing()" in unit and "maipai_face_clock_visible()" in unit
    assert "set_avatar_parts(true)" in unit  # the drawn face comes back


def test_nothing_is_allocated_until_a_pack_is_sent() -> None:
    unit = _file_from_patch("H04-picture-face-unit.patch", "firmware/main/hal/maipai_picface.cc")
    register = unit.split("void maipai_picface_register_tools()", 1)[1]
    head = register.split("mcp.AddTool", 1)[0]
    assert "heap_caps" not in head and "xTaskCreate" not in head and "lv_" not in head
    assert (
        unit.count("xTaskCreatePinnedToCoreWithCaps") == 1
    )  # one decode task, created on the first commit
    assert (
        "MALLOC_CAP_SPIRAM" in unit and "heap_caps_malloc(PF_FRAME_BYTES, MALLOC_CAP_SPIRAM" in unit
    )


def test_the_audio_tap_is_one_atomic_read_when_nobody_speaks() -> None:
    fx = _file_from_patch("H02-face-fluid-motion.patch", "firmware/main/hal/maipai_facefx.cc")
    tap = fx.split("void maipai_speech_tap", 1)[1].split("\n}\n", 1)[0]
    first = [line.strip() for line in tap.splitlines() if line.strip() and line.strip() != "{"][1]
    assert first.startswith("if (!s_active.load")  # the first thing it does is the one atomic read
    assert "new " not in tap and "malloc" not in tap


# ---- pictures: resize, colour, compression ---------------------------------------------------------------


def _solid(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    return bytes(rgba) * (width * height)


def _gradient(width: int, height: int) -> bytes:
    yy, xx = np.mgrid[0:height, 0:width]
    img = np.zeros((height, width, 4), dtype=np.uint8)
    img[..., 0] = xx * 255 // max(width - 1, 1)
    img[..., 1] = yy * 255 // max(height - 1, 1)
    img[..., 2] = 90
    img[..., 3] = 255
    return img.tobytes()


def test_a_picture_of_any_size_becomes_320_by_240() -> None:
    for width, height in ((640, 480), (1920, 1080), (100, 100), (320, 240), (4000, 3000)):
        out = pf.resize_rgba(_gradient(width, height), width, height)
        assert out.shape == (240, 320, 4) and out.dtype == np.uint8


def test_cover_fills_the_screen_and_contain_keeps_the_whole_picture() -> None:
    red = _solid(100, 100, (255, 0, 0, 255))
    cover = pf.resize_rgba(red, 100, 100, "cover")
    assert (cover[..., 0] == 255).all() and (cover[..., 3] == 255).all()
    contain = pf.resize_rgba(red, 100, 100, "contain")
    assert contain[120, 160, 0] == 255 and contain[120, 5, 0] == 0  # bars at the sides
    assert contain[120, 5, 3] == 255  # the bars are opaque black


def test_a_picture_that_is_not_what_it_says_is_refused_in_plain_words() -> None:
    with pytest.raises(pf.PictureError) as bad:
        pf.resize_rgba(b"\x00" * 10, 4, 4)
    assert "could not be read" in str(bad.value)
    with pytest.raises(pf.PictureError):
        pf.resize_rgba(b"", 0, 0)
    with pytest.raises(pf.PictureError) as huge:
        pf.resize_rgba(
            b"\x00" * 16, 10_000, 10_000
        )  # length does not match either; the size rule is checked next
    assert huge.value.code in {"bad_picture", "picture_huge"}


def test_rgb565_is_little_endian_and_round_trips_within_a_step() -> None:
    img = np.zeros((240, 320, 4), dtype=np.uint8)
    img[..., 3] = 255
    img[0, 0] = (255, 0, 0, 255)
    img[0, 1] = (0, 255, 0, 255)
    img[0, 2] = (0, 0, 255, 255)
    img[0, 3] = (255, 255, 255, 255)
    raw = pf.to_rgb565(img)
    assert len(raw) == pf.FRAME_BYTES
    assert raw[0:2] == bytes([0x00, 0xF8])  # red 0xF800, low byte first
    assert raw[2:4] == bytes([0xE0, 0x07])
    assert raw[4:6] == bytes([0x1F, 0x00])
    assert raw[6:8] == bytes([0xFF, 0xFF])
    back = pf.from_rgb565(raw)
    assert tuple(back[0, 3]) == (255, 255, 255) and tuple(back[0, 0]) == (255, 0, 0)
    ramp = pf.resize_rgba(_gradient(320, 240), 320, 240)
    err = np.abs(pf.from_rgb565(pf.to_rgb565(ramp)).astype(int) - ramp[..., :3].astype(int)).max()
    assert err <= 8


def test_a_transparent_pixel_counts_as_black() -> None:
    img = np.zeros((240, 320, 4), dtype=np.uint8)
    img[..., :3] = 255
    assert pf.to_rgb565(img) == b"\x00" * pf.FRAME_BYTES


def test_flat_pictures_are_compressed_and_noise_is_kept_raw() -> None:
    flat = pf.encode_frame(
        pf.to_rgb565(pf.resize_rgba(_solid(320, 240, (30, 60, 90, 255)), 320, 240))
    )
    assert not flat.raw and flat.size < 2000
    assert pf.decode_frame(flat) == pf.to_rgb565(
        pf.resize_rgba(_solid(320, 240, (30, 60, 90, 255)), 320, 240)
    )
    noise = np.random.default_rng(1).integers(0, 256, pf.FRAME_BYTES, dtype=np.uint8).tobytes()
    kept = pf.encode_frame(noise)
    assert kept.raw and kept.size == pf.FRAME_BYTES and pf.decode_frame(kept) == noise
    assert flat.crc == zlib.crc32(flat.payload) & 0xFFFFFFFF
    with pytest.raises(pf.PictureError):
        pf.encode_frame(b"short")


def test_thumbnails_are_small_png_data_uris() -> None:
    uri = pf.thumbnail(pf.to_rgb565(pf.resize_rgba(_gradient(320, 240), 320, 240)))
    assert uri.startswith("data:image/png;base64,")
    png = base64.b64decode(uri.split(",", 1)[1])
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) < 12000


# ---- the pack rules (the same numbers as the firmware core test) ------------------------------------------


def _frame(size: int) -> pf.Encoded:
    return pf.Encoded(b"\x00" * size, False, 0)


def test_the_pack_limits_are_the_firmwares() -> None:
    core = _file_from_patch(
        "H03-picture-face-core.patch", "firmware/main/hal/maipai_picface_core.h"
    )
    for name, value in (
        ("PF_MAX_STORE_BYTES", "1000000u"), ("PF_MAX_FRAMES_PER_SLOT", "6"), ("PF_MAX_FRAMES", "14"),
        ("PF_MIN_FPS", "1"), ("PF_MAX_FPS", "12"),
    ):  # fmt: skip
        assert f"#define {name} {value}" in core
    assert (pf.MAX_STORE_BYTES, pf.MAX_FRAMES_PER_SLOT, pf.MAX_FRAMES, pf.MIN_FPS, pf.MAX_FPS) == (
        1_000_000,
        6,
        14,
        1,
        12,
    )
    for slot in pf.SLOTS:
        assert f'"{slot}"' in core


def test_check_set_names_the_first_problem() -> None:
    ok = pf.PictureSet(
        "picture", 6, dict(pf.DEFAULT_OVERLAY), {"neutral": [_frame(1000)], "happy": [_frame(1000)]}
    )
    assert pf.check_set(ok) is None
    assert pf.check_set(pf.PictureSet("picture", 6, {}, {"happy": [_frame(10)]})) == "no_neutral"
    assert pf.check_set(pf.PictureSet("film", 6, {}, {"neutral": [_frame(10)]})) == "mode"
    assert pf.check_set(pf.PictureSet("sequence", 13, {}, {"neutral": [_frame(10)]})) == "fps"
    assert pf.check_set(pf.PictureSet("picture", 6, {}, {"neutral": [_frame(10)] * 2})) == "index"
    assert pf.check_set(pf.PictureSet("sequence", 6, {}, {"neutral": [_frame(10)] * 7})) == "index"
    assert (
        pf.check_set(
            pf.PictureSet("picture", 6, {}, {"bogus": [_frame(10)], "neutral": [_frame(10)]})
        )
        == "slot"
    )
    seven_big = {s: [_frame(pf.FRAME_BYTES)] for s in pf.SLOTS}
    assert pf.check_set(pf.PictureSet("picture", 6, {}, seven_big)) == "too_big"
    many = {s: [_frame(100)] * 6 for s in pf.SLOTS[:3]}
    assert pf.check_set(pf.PictureSet("sequence", 6, {}, many)) == "too_many_frames"
    assert (
        pf.check_set(pf.PictureSet("picture", 6, {}, {"neutral": [_frame(pf.FRAME_BYTES + 1)]}))
        == "frame_size"
    )


def test_the_overlay_places_follow_the_firmware_rules() -> None:
    assert pf.check_overlay({})["lx"] == 112
    clean = pf.check_overlay({"lx": 100, "color": "#FF8800"})
    assert clean["lx"] == 100 and clean["color"] == "#ff8800"
    for bad in (
        {"eye_w": 3},
        {"lx": 320},
        {"my": -1},
        {"mouth_h": 121},
        {"color": "red"},
        {"color": "#12345g"},
        {"lx": "9"},
        {"lx": True},
    ):
        with pytest.raises(pf.PictureError) as error:
            pf.check_overlay(bad)
        assert error.value.code == "overlay"


def test_every_refusal_has_english_and_spanish_words_that_say_what_to_do() -> None:
    core = _file_from_patch(
        "H03-picture-face-core.patch", "firmware/main/hal/maipai_picface_core.h"
    )
    for code in pf._SAY:
        en, es = pf._SAY[code]
        assert en != es and len(en) > 10 and len(es) > 10
        assert pf.say("es", code) == es and pf.say("en", code) == en and pf.say("fr", code) == en
        assert EM not in en and EM not in es
    firmware_codes = [c for c in pf._SAY if c in core]
    assert {
        "too_big",
        "too_many_frames",
        "no_neutral",
        "crc",
        "memory",
        "decode",
        "overlay",
    } <= set(firmware_codes)


# ---- the store ---------------------------------------------------------------------------------------------


def test_the_store_keeps_pictures_outside_the_repository_and_private(tmp_path: Path) -> None:
    store = pf.PictureStore(tmp_path / "pictures")
    flat = pf.encode_frame(
        pf.to_rgb565(pf.resize_rgba(_solid(64, 48, (200, 100, 50, 255)), 64, 48))
    )
    store.save(
        "aa:bb:cc:dd:ee:01",
        pf.PictureSet("overlay", 4, pf.check_overlay({"lx": 99}), {"neutral": [flat]}),
    )
    loaded = store.load("aa:bb:cc:dd:ee:01")
    assert loaded.mode == "overlay" and loaded.fps == 4 and loaded.overlay["lx"] == 99
    assert pf.decode_frame(loaded.frames["neutral"][0]) == pf.decode_frame(flat)
    folder = next((tmp_path / "pictures").iterdir())
    assert oct(folder.stat().st_mode & 0o777) == "0o700"
    assert all(oct(p.stat().st_mode & 0o777) == "0o600" for p in folder.iterdir())
    assert pf.default_root() == Path.home() / ".config" / "maipai" / "stackchan-pictures"
    assert not str(pf.default_root()).startswith(str(ROOT))
    store.clear("aa:bb:cc:dd:ee:01")
    assert store.load("aa:bb:cc:dd:ee:01").frames == {}


def test_a_unit_id_cannot_leave_its_folder(tmp_path: Path) -> None:
    store = pf.PictureStore(tmp_path / "p")
    for bad in ("../../evil", "", ".hidden"):
        with pytest.raises(pf.PictureError):
            store.save(
                bad, pf.PictureSet(frames={"neutral": [pf.encode_frame(b"\x00" * pf.FRAME_BYTES)]})
            )
    store.save(
        "a/b:c", pf.PictureSet(frames={"neutral": [pf.encode_frame(b"\x00" * pf.FRAME_BYTES)]})
    )
    assert all(str(p).startswith(str(tmp_path / "p")) for p in (tmp_path / "p").rglob("*"))
    assert not (tmp_path / "evil").exists()


# ---- the service, against a unit that follows the firmware's protocol --------------------------------------


class FakeUnit:
    """The unit's side of self.facepic.*: the same admission rules and the same CRC and reassembly checks."""

    def __init__(self) -> None:
        self.link = True
        self.has_tools = True
        self.calls: list[str] = []
        self.held: dict[str, object] | None = None
        self.mem_ok = True
        self.pack: dict | None = None
        self.shown = False

    def __call__(self, name: str, arguments: dict, *, device_id: str, timeout: float) -> object:
        if not self.link:
            raise BodyLost("no link")
        self.calls.append(name)
        if not self.has_tools:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        method = getattr(self, name.replace("self.facepic.", "t_"))
        return method(**arguments)

    def _err(self, code: str) -> dict:
        en, es = pf._SAY[code]
        return {"ok": False, "code": code, "error": en, "error_es": es}

    def t_begin(self, mode: str, fps: int, overlay: str = "") -> dict:
        if mode not in pf.MODES:
            return self._err("mode")
        self.pack = {"mode": mode, "fps": fps, "overlay": overlay, "frames": {}, "bytes": 0}
        self.shown = False
        return {"ok": True}

    def t_frame(self, slot: str, index: int, bytes: int, crc: str, raw: bool) -> dict:  # noqa: A002
        if self.pack is None:
            return self._err("not_started")
        if not self.mem_ok:
            return self._err("memory")
        if self.pack["bytes"] + bytes > pf.MAX_STORE_BYTES:
            return self._err("too_big")
        self.pack["frames"][(slot, index)] = {
            "size": bytes,
            "crc": int(crc, 16),
            "raw": raw,
            "data": b"",
        }
        self.pack["bytes"] += bytes
        return {"ok": True}

    def t_data(self, slot: str, index: int, at: int, b64: str) -> dict:
        frame = self.pack["frames"][(slot, index)]
        if at != len(frame["data"]):
            return self._err("order")
        frame["data"] += base64.b64decode(b64)
        if (
            len(frame["data"]) == frame["size"]
            and zlib.crc32(frame["data"]) & 0xFFFFFFFF != frame["crc"]
        ):
            return self._err("crc")
        return {"ok": True, "got": len(frame["data"]), "done": len(frame["data"]) == frame["size"]}

    def t_commit(self) -> dict:
        if self.pack is None:
            return self._err("not_started")
        if ("neutral", 0) not in self.pack["frames"]:
            return self._err("no_neutral")
        for frame in self.pack["frames"].values():
            if len(frame["data"]) != frame["size"]:
                return self._err("missing")
            raw = frame["data"] if frame["raw"] else zlib.decompress(frame["data"])
            if len(raw) != pf.FRAME_BYTES:
                return self._err("decode")
        self.shown = True
        return {"ok": True, "frames": len(self.pack["frames"]), "bytes": self.pack["bytes"]}

    def t_clear(self) -> dict:
        self.pack = None
        self.shown = False
        return {"ok": True}

    def t_status(self) -> dict:
        if self.pack is None:
            return {"ok": True, "held": False, "showing": False}
        return {
            "ok": True, "held": True, "mode": self.pack["mode"], "bytes": self.pack["bytes"],
            "frames": len(self.pack["frames"]), "showing": self.shown,
        }  # fmt: skip


def _service(tmp_path: Path, unit: FakeUnit, **kwargs) -> pf.PictureService:
    return pf.PictureService(unit, pf.PictureStore(tmp_path / "pics"), chunk=700, **kwargs)


UNIT = "aa:bb:cc:dd:ee:01"


def _add(service: pf.PictureService, slot: str, index: int = 0, seed: int = 0) -> dict:
    return service.add_picture(
        UNIT, slot, index, 640, 480, _gradient(640, 480)[: 640 * 480 * 4], "en"
    )


def test_the_pack_goes_to_the_unit_in_pieces_and_arrives_whole(tmp_path: Path) -> None:
    unit, progress = FakeUnit(), []
    service = _service(tmp_path, unit, progress=lambda *_: progress.append(1))
    for slot in pf.SLOTS:
        _add(service, slot)
    sent = service.send(UNIT, "en")
    assert sent["sent"] is True and sent["frames"] == 7 and unit.shown
    assert unit.calls[0] == "self.facepic.begin" and unit.calls[-1] == "self.facepic.commit"
    assert (
        unit.calls.count("self.facepic.frame") == 7
        and unit.calls.count("self.facepic.data") > 7
        and progress
    )
    stored = service.store.load(UNIT).frames["neutral"][0]
    assert unit.pack["frames"][("neutral", 0)]["data"] == stored.payload  # byte for byte


def test_a_pack_that_does_not_fit_is_refused_before_anything_is_sent(tmp_path: Path) -> None:
    unit = FakeUnit()
    service = _service(tmp_path, unit)
    service.set_options(UNIT, mode="sequence", fps=8)
    noise = np.random.default_rng(3).integers(0, 256, (240, 320, 4), dtype=np.uint8)
    noise[..., 3] = 255
    with pytest.raises(pf.PictureError) as error:
        for index in range(6):
            for slot in ("neutral", "happy"):
                service.add_picture(UNIT, slot, index, 320, 240, noise.tobytes(), "en")
    assert error.value.code in {"too_big", "too_many_frames"}
    assert "send again" in str(error.value)
    assert unit.calls == []
    with pytest.raises(pf.PictureError) as es:
        service.add_picture(UNIT, "bogus", 0, 4, 4, b"\x00" * 64, "es")
    assert "expresión" in str(es.value)


def test_the_spanish_page_gets_spanish_refusals(tmp_path: Path) -> None:
    service = _service(tmp_path, FakeUnit())
    with pytest.raises(pf.PictureError) as error:
        service.send(UNIT, "es")
    assert "imágenes" in str(error.value) and error.value.code == "nothing"


def test_the_units_own_refusal_reaches_the_person_in_their_language(tmp_path: Path) -> None:
    unit = FakeUnit()
    unit.mem_ok = False
    service = _service(tmp_path, unit)
    _add(service, "neutral")
    with pytest.raises(pf.PictureError) as error:
        service.send(UNIT, "es")
    assert error.value.code == "memory" and "no tiene espacio" in str(error.value)
    with pytest.raises(pf.PictureError) as english:
        service.send(UNIT, "en")
    assert "no room" in str(english.value)


def test_a_unit_without_picture_faces_is_named_in_plain_words(tmp_path: Path) -> None:
    unit = FakeUnit()
    unit.has_tools = False
    service = _service(tmp_path, unit)
    _add(service, "neutral")
    with pytest.raises(pf.PictureError) as error:
        service.send(UNIT, "en")
    assert error.value.code == "old_firmware" and "Update the unit" in str(error.value)


def test_a_unit_that_is_away_gets_the_pictures_when_it_connects(tmp_path: Path) -> None:
    unit = FakeUnit()
    service = _service(tmp_path, unit)
    _add(service, "neutral")
    unit.link = False
    offline = service.send(UNIT, "en")
    assert offline["sent"] is False and "when it connects" in offline["message"]
    assert service.view(UNIT)["pending"] is True
    unit.link = True
    pf.sync_on_connect(service, UNIT)
    assert unit.shown and service.view(UNIT)["pending"] is False


def test_sync_does_not_send_again_when_the_unit_already_holds_the_pack(tmp_path: Path) -> None:
    unit = FakeUnit()
    service = _service(tmp_path, unit)
    _add(service, "neutral")
    service.send(UNIT, "en")
    unit.calls.clear()
    service.sync(UNIT)
    assert unit.calls == ["self.facepic.status"]
    unit.pack = None
    service.sync(UNIT)
    assert "self.facepic.begin" in unit.calls


def test_sync_never_raises_and_does_nothing_without_pictures(tmp_path: Path) -> None:
    unit = FakeUnit()
    service = _service(tmp_path, unit)
    pf.sync_on_connect(service, UNIT)
    assert unit.calls == []
    _add(service, "neutral")
    unit.link = False
    pf.sync_on_connect(service, UNIT)


def test_clearing_removes_the_pictures_here_and_on_the_unit(tmp_path: Path) -> None:
    unit = FakeUnit()
    service = _service(tmp_path, unit)
    _add(service, "neutral")
    service.send(UNIT, "en")
    done = service.clear_all(UNIT, "en")
    assert done["frames"] == 0 and "drawn face is back" in done["message"] and unit.pack is None
    assert service.store.load(UNIT).frames == {}


def test_switching_to_a_one_picture_mode_keeps_the_first_frame_of_each_expression(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path, FakeUnit())
    service.set_options(UNIT, mode="sequence", fps=5)
    for index in range(3):
        service.add_picture(UNIT, "neutral", index, 64, 48, _gradient(64, 48), "en")
    assert service.view(UNIT)["slots"][0]["frames"] == 3
    view = service.set_options(UNIT, mode="picture")
    assert view["slots"][0]["frames"] == 1 and view["limits"]["per_slot"] == 1


def test_the_view_says_when_the_pack_is_ready(tmp_path: Path) -> None:
    service = _service(tmp_path, FakeUnit())
    assert service.view(UNIT)["ready"] is False
    view = _add(service, "happy")
    assert view["ready"] is False  # no neutral picture yet
    assert _add(service, "neutral")["ready"] is True
    assert [s["slot"] for s in view["slots"]] == list(pf.SLOTS)


# ---- the settings page ----------------------------------------------------------------------------------


def _backend(tmp_path: Path, unit: FakeUnit):
    from maipai_body import settings_page

    return settings_page.SettingsBackend(
        devices=lambda: {UNIT: {}},
        store=settings_page.UnitSettingsStore(tmp_path / "units.json"),
        pictures=_service(tmp_path, unit),
    )


def test_the_page_routes_add_list_send_and_remove(tmp_path: Path) -> None:
    unit = FakeUnit()
    backend = _backend(tmp_path, unit)
    base = f"/api/stackchan/unit/{UNIT}/pictures"
    rgba = base64.b64encode(_gradient(640, 480)).decode()
    status, payload = backend.route_post(
        base + "/add",
        {
            "slot": "neutral",
            "index": 0,
            "width": 640,
            "height": 480,
            "rgba_b64": rgba,
            "lang": "en",
        },
        True,
    )
    assert status == 200 and payload["slots"][0]["frames"] == 1
    status, _, body = backend.route_get(base, "en", True)
    assert status == 200 and json.loads(body)["ready"] is True
    status, payload = backend.route_post(
        base + "/options", {"mode": "overlay", "fps": 6, "overlay": {"lx": 90}, "lang": "en"}, True
    )
    assert status == 200 and payload["mode"] == "overlay" and payload["overlay"]["lx"] == 90
    status, payload = backend.route_post(base + "/send", {"lang": "en"}, True)
    assert status == 200 and payload["sent"] is True and unit.shown
    assert unit.pack["mode"] == "overlay" and json.loads(unit.pack["overlay"])["lx"] == 90
    status, payload = backend.route_post(base + "/remove", {"slot": "neutral", "lang": "en"}, True)
    assert status == 200 and payload["frames"] == 0
    status, payload = backend.route_post(base + "/clear", {"lang": "es"}, True)
    assert status == 200 and "cara dibujada" in payload["message"]


def test_the_page_routes_refuse_in_plain_words(tmp_path: Path) -> None:
    backend = _backend(tmp_path, FakeUnit())
    base = f"/api/stackchan/unit/{UNIT}/pictures"
    assert (
        backend.route_post(
            base + "/add", {"slot": "neutral", "rgba_b64": "!!!", "width": 1, "height": 1}, False
        )[0]
        == 403
    )
    status, payload = backend.route_post(
        base + "/add",
        {"slot": "neutral", "rgba_b64": "!!!", "width": 1, "height": 1, "lang": "en"},
        True,
    )
    assert status == 400 and "could not be read" in payload["error"]
    status, payload = backend.route_post(base + "/options", {"mode": "film", "lang": "en"}, True)
    assert status == 400 and "Choose picture" in payload["error"]
    status, payload = backend.route_post(base + "/send", {"lang": "en"}, True)
    assert status == 400 and "Add a neutral picture" in payload["error"]
    assert backend.route_post(base + "/nope", {"lang": "en"}, True)[0] == 404
    other = "/api/stackchan/unit/aa:bb:cc:00:00:99/pictures"
    assert backend.route_post(other + "/send", {"lang": "en"}, True)[0] == 400
    assert backend.route_get(other, "en", True)[0] == 400
    assert backend.route_get(base, "en", False)[0] == 403


def test_the_page_has_the_section_and_every_word_in_all_six_languages() -> None:
    from maipai_body.i18n import CATALOG
    from maipai_body.i18n_pictures import KEYS
    from maipai_body.settings_page import render_page

    for code in ("en", "es", "fr", "de", "pt", "it"):
        for key in KEYS:
            assert CATALOG[code][key].strip(), (code, key)
            assert EM not in CATALOG[code][key]
        page = render_page(code).decode()
        assert "function picSection" in page and "picSection(u.device_id)" in page
        assert f"lang:'{code}'" in page
    assert (
        "x.drawImage" in render_page("en").decode()
    )  # the page resizes before sending: nothing leaves this computer
    assert CATALOG["es"]["settings.pics.slot.sleepy"] != CATALOG["en"]["settings.pics.slot.sleepy"]


def test_the_host_is_wired_to_send_the_pictures_on_connect() -> None:
    source = (ROOT / "host" / "maipai_body" / "app.py").read_text()
    assert (
        "pictures_sync" in source
        and "pictures=pictures" in source
        and "_picture_service(voice)" in source
    )


def test_no_picture_ships_with_the_repository() -> None:
    suspects = []
    for path in ROOT.rglob("*"):
        if (
            ".git" in path.parts
            or ".venv" in path.parts
            or "node_modules" in path.parts
            or not path.is_file()
        ):
            continue
        if path.suffix.lower() in {".jpg", ".jpeg", ".heic", ".webp"}:
            suspects.append(path)
    assert suspects == [], f"photographs in the repository: {suspects}"
    assert not (
        ROOT / "host" / "maipai_body" / "bodies" / "stackchan" / "firmware" / "assets" / "pictures"
    ).exists()
