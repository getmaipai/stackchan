import io
import json
import struct
import zipfile
import zlib

from maipai_body import picture_faces as pf
from maipai_body.character_pack import build_pack, load_pack, validate_pack


def png_bytes(color=(220, 30, 40)):
    return bytes(color) * 12, _png(color)


def _png(color=(220, 30, 40, 255)):
    def chunk(tag, body):
        payload = tag + body
        return struct.pack(">I", len(body)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(color) * 4 for _ in range(3))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 3, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


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
        ({"format": 1, "name": "A", "author": "a@example.com", "license": "own work", "mode": "picture", "looks": {"neutral": ["n.png"]}}, "email address"),
        ({"format": 1, "name": "A", "author": "", "license": "own work", "mode": "picture", "looks": {"neutral": ["n.png"]}}, "author"),
        ({"format": 1, "name": "A", "author": "Art", "license": "", "mode": "picture", "looks": {"neutral": ["n.png"]}}, "license"),
        ({"format": 1, "name": "A", "author": "Art", "license": "own work", "mode": "picture", "looks": {}}, "neutral"),
    ]
    for index, (manifest, phrase) in enumerate(cases):
        target = tmp_path / f"bad-{index}.zip"
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("n.png", _png())
        assert any(phrase in problem for problem in validate_pack(target))


def test_personal_data_guard_covers_phone_and_address(tmp_path):
    for index, (author, phrase) in enumerate((("555-123-4567", "phone number"), ("12 Main Street", "street address"))):
        target = tmp_path / f"personal-{index}.zip"
        manifest = {"format": 1, "name": "A", "author": author, "license": "own work", "mode": "picture", "looks": {"neutral": ["n.png"]}}
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
    manifest = {"format": 1, "name": "A", "author": "Art", "license": "own work", "mode": "picture", "looks": {"neutral": ["n.png"]}}
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("n.png", bytes(data))
    assert any("12,000,000 pixels" in p for p in validate_pack(target))


def test_rejects_image_over_4mb(tmp_path):
    target = tmp_path / "image-too-large.zip"
    manifest = {"format": 1, "name": "A", "author": "Art", "license": "own work", "mode": "picture", "looks": {"neutral": ["n.png"]}}
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("n.png", b"x" * (4 * 1024 * 1024 + 1))
    assert any("larger than 4 MB" in p for p in validate_pack(target))
