import json
import struct
import zipfile
import zlib

import numpy as np

from maipai_body import character_pack
from maipai_body import picture_faces as pf
from maipai_body.character_pack import build_pack, load_pack, validate_pack


def png_bytes(color=(220, 30, 40)):
    return bytes(color) * 12, _png(color)


def _png(color=(220, 30, 40, 255)):
    def chunk(tag, body):
        payload = tag + body
        return (
            struct.pack(">I", len(body))
            + payload
            + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + bytes(color) * 4 for _ in range(3))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 3, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def test_each_mode_builds_checks_and_loads(tmp_path):
    for mode in pf.MODES:
        source = tmp_path / mode
        source.mkdir()
        (source / "neutral.png").write_bytes(_png())
        if mode == "sequence":
            (source / "neutral_1.png").write_bytes(_png())
        archive = tmp_path / f"{mode}.zip"
        build_pack(source, archive, "Moss", "Example artist", "CC-BY-4.0", mode=mode)
        assert validate_pack(archive) == []
        pictures = load_pack(archive)
        assert pictures.frames["neutral"]
        assert pf.check_set(pictures) is None


def test_rejections_name_problem(tmp_path):
    cases = [
        (
            {
                "format": 1,
                "name": "A",
                "author": "a@example.com",
                "license": "own work",
                "mode": "picture",
                "looks": {"neutral": ["n.png"]},
            },
            "email address",
        ),
        (
            {
                "format": 1,
                "name": "A",
                "author": "",
                "license": "own work",
                "mode": "picture",
                "looks": {"neutral": ["n.png"]},
            },
            "author",
        ),
        (
            {
                "format": 1,
                "name": "A",
                "author": "Art",
                "license": "",
                "mode": "picture",
                "looks": {"neutral": ["n.png"]},
            },
            "license",
        ),
        (
            {
                "format": 1,
                "name": "A",
                "author": "Art",
                "license": "own work",
                "mode": "picture",
                "looks": {},
            },
            "neutral",
        ),
    ]
    for index, (manifest, phrase) in enumerate(cases):
        target = tmp_path / f"bad-{index}.zip"
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("n.png", _png())
        assert any(phrase in problem for problem in validate_pack(target))


def test_personal_data_guard_covers_phone_and_address(tmp_path):
    for index, (author, phrase) in enumerate(
        (("555-123-4567", "phone number"), ("12 Main Street", "street address"))
    ):
        target = tmp_path / f"personal-{index}.zip"
        manifest = {
            "format": 1,
            "name": "A",
            "author": author,
            "license": "own work",
            "mode": "picture",
            "looks": {"neutral": ["n.png"]},
        }
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("n.png", _png())
        assert any(phrase in p for p in validate_pack(target))


def test_rejects_zip_slip(tmp_path):
    target = tmp_path / "slip.zip"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("../outside.png", b"x")
        archive.writestr("manifest.json", "{")
    assert any("escapes" in problem for problem in validate_pack(target))


def test_rejects_invalid_json(tmp_path):
    target = tmp_path / "bad-json.zip"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("manifest.json", "{")
    assert any("valid JSON" in problem for problem in validate_pack(target))


def test_rejects_entry_count_and_expanded_size(tmp_path):
    target = tmp_path / "limits.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", "{}")
        for i in range(64):
            archive.writestr(f"f{i}", b"x" * 270000)
    messages = " ".join(validate_pack(target))
    assert "64 entries" in messages
    assert "16 MB" in messages


def test_rejects_image_size_and_dimensions(tmp_path):
    target = tmp_path / "big.zip"
    data = bytearray(_png())
    data[16:24] = struct.pack(">II", 4001, 3000)
    # The dimensions are rejected from the PNG header before pixel decoding.
    manifest = {
        "format": 1,
        "name": "A",
        "author": "Art",
        "license": "own work",
        "mode": "picture",
        "looks": {"neutral": ["n.png"]},
    }
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("n.png", bytes(data))
    assert any("12,000,000 pixels" in p for p in validate_pack(target))


def test_rejects_image_over_4mb(tmp_path):
    target = tmp_path / "image-too-large.zip"
    manifest = {
        "format": 1,
        "name": "A",
        "author": "Art",
        "license": "own work",
        "mode": "picture",
        "looks": {"neutral": ["n.png"]},
    }
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("n.png", b"x" * (4 * 1024 * 1024 + 1))
    assert any("larger than 4 MB" in p for p in validate_pack(target))


def test_a_jpeg_keeps_its_colors_in_the_pack():
    """decode_jpeg returns BGR; a red JPEG must stay red in the pack frames (a regression test for a channel swap)."""
    import av

    img = np.zeros((240, 320, 3), dtype=np.uint8)
    img[..., 0] = 220  # red in RGB
    codec = av.CodecContext.create("mjpeg", "w")
    codec.width, codec.height, codec.pix_fmt = 320, 240, "yuvj420p"
    codec.options = {"qscale": "2"}
    frame = av.VideoFrame.from_ndarray(img, format="rgb24").reformat(format="yuvj420p")
    packets = codec.encode(frame) + codec.encode(None)
    jpeg = b"".join(bytes(p) for p in packets)
    rgba, w, h = character_pack._decode_png(jpeg)
    px = np.frombuffer(rgba, dtype=np.uint8).reshape(h, w, 4)[120, 160]
    assert px[0] > 150 and px[2] < 80, px


# ---- the settings page route -------------------------------------------------------------------------------


def _pack_bytes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for slot in ("neutral", "happy"):
        (src / f"{slot}.png").write_bytes(_png((200, 40, 40, 255)))
    out = build_pack(src, tmp_path / "pack.zip", "Test", "Me", "own work")
    return out.read_bytes()


def test_the_page_installs_a_valid_pack_and_refuses_a_broken_one_with_every_problem(tmp_path):
    import base64

    from test_picture_faces import UNIT, FakeUnit, _backend

    backend = _backend(tmp_path, FakeUnit())
    base = f"/api/stackchan/unit/{UNIT}/pictures/import-character"
    good = base64.b64encode(_pack_bytes(tmp_path)).decode()
    status, payload = backend.route_post(base, {"b64": good, "lang": "en"}, True)
    assert (
        status == 200
        and payload["ready"] is True
        and payload["message"].startswith("Character pack")
    )
    assert backend.pictures.store.load(UNIT).frames["neutral"]
    bad = base64.b64encode(b"not a zip").decode()
    status, payload = backend.route_post(base, {"b64": bad, "lang": "en"}, True)
    assert status == 400 and payload["problems"] and "ZIP" in payload["error"]
    assert (
        backend.route_post(base, {"b64": good}, False)[0] == 403
    )  # a page that is not signed in installs nothing
    status, payload = backend.route_post(base, {"b64": "!!!"}, True)
    assert status == 400 and "could not be read" in payload["error"]


def test_the_character_words_exist_in_all_six_languages_and_the_script_is_in_the_page():
    from maipai_body import i18n, i18n_character, settings_ui

    keys = set(i18n_character.CATALOGS["en"])
    for code in i18n.SUPPORTED:
        assert set(i18n_character.CATALOGS[code]) == keys
        assert all(
            text.strip() and chr(0x2014) not in text for text in i18n_character.CATALOGS[code].values()
        )
        assert i18n.CATALOG[code]["settings.ui.char.title"].strip()
    assert "import-character" in settings_ui.JS and "char.import" in settings_ui.JS
