"""Shareable illustrated character packs."""

from __future__ import annotations

import io
import json
import re
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Any

import numpy as np

from maipai_body import picture_faces as pf

MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 64


def _personal_field(value: str) -> str | None:
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value):
        return "email address"
    if re.search(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)", value):
        return "phone number"
    if re.search(
        r"\b\d{1,6}\s+[A-Za-z0-9.'-]+\s+(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|drive|dr\.?)\b",
        value,
        re.I,
    ):
        return "street address"
    return None


def _image_info(data: bytes) -> tuple[str, int, int]:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return "PNG", *struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        pos = 2
        while pos + 4 <= len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue
            marker = data[pos + 1]
            pos += 2
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                continue
            if pos + 2 > len(data):
                break
            size = int.from_bytes(data[pos : pos + 2], "big")
            if (
                marker
                in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)
                and size >= 7
            ):
                return (
                    "JPEG",
                    int.from_bytes(data[pos + 5 : pos + 7], "big"),
                    int.from_bytes(data[pos + 3 : pos + 5], "big"),
                )
            pos += size
    raise ValueError("invalid image")


def _decode_png(data: bytes) -> tuple[bytes, int, int]:
    kind, width, height = _image_info(data)
    if kind != "PNG":
        from maipai_body.vision.jpeg import decode_jpeg

        rgb = decode_jpeg(data)
        h, w = rgb.shape[:2]
        # decode_jpeg gives BGR (the detector's order); the pack path wants RGB
        rgba = np.concatenate([rgb[..., 2::-1], np.full((h, w, 1), 255, dtype=np.uint8)], axis=2)
        return rgba.tobytes(), w, h
    pos, compressed, depth, color_type = 8, bytearray(), 0, 0
    while pos + 12 <= len(data):
        length = int.from_bytes(data[pos : pos + 4], "big")
        tag, body = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + length]
        if tag == b"IHDR":
            depth, color_type = body[8], body[9]
        elif tag == b"IDAT":
            compressed.extend(body)
        pos += 12 + length
        if tag == b"IEND":
            break
    channels = {2: 3, 6: 4}.get(color_type)
    if depth != 8 or channels is None:
        raise ValueError("unsupported PNG")
    stride = width * channels
    raw = zlib.decompress(compressed)
    rows = bytearray()
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filt = raw[offset]
        scan = bytearray(raw[offset + 1 : offset + 1 + stride])
        offset += stride + 1
        for i in range(stride):
            left = scan[i - channels] if i >= channels else 0
            up = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if filt == 1:
                scan[i] = (scan[i] + left) & 255
            elif filt == 2:
                scan[i] = (scan[i] + up) & 255
            elif filt == 3:
                scan[i] = (scan[i] + ((left + up) // 2)) & 255
            elif filt == 4:
                p = left + up - upper_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upper_left)
                scan[i] = (
                    scan[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else upper_left)
                ) & 255
            elif filt != 0:
                raise ValueError("bad PNG filter")
        rows.extend(scan)
        previous = scan
    if channels == 4:
        return bytes(rows), width, height
    rgba = bytearray()
    for i in range(0, len(rows), 3):
        rgba.extend(rows[i : i + 3])
        rgba.append(255)
    return bytes(rgba), width, height


def validate_pack(path_or_bytes: str | Path | bytes, lang: str | None = None) -> list[str]:
    problems: list[str] = []
    try:
        raw = (
            path_or_bytes if isinstance(path_or_bytes, bytes) else Path(path_or_bytes).read_bytes()
        )
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except (OSError, zipfile.BadZipFile, TypeError):
        return ["The pack is not a readable ZIP file. Choose a character pack ZIP file."]
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            problems.append(
                "The pack has more than 64 entries. Remove files until it has 64 or fewer."
            )
        if sum(item.file_size for item in infos) > MAX_ARCHIVE_BYTES:
            problems.append(
                "The unzipped pack is larger than 16 MB. Remove files or use smaller images."
            )
        for item in infos:
            name = item.filename
            if (
                name.startswith(("/", "\\"))
                or re.match(r"^[A-Za-z]:", name)
                or ".." in Path(name).parts
            ):
                problems.append(
                    "A pack path escapes its folder. Rename the file to use a safe relative path."
                )
                break
        if "manifest.json" not in archive.namelist():
            return problems + ["The pack has no manifest.json. Add a manifest.json file."]
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except (ValueError, KeyError, OSError, RuntimeError):
            return problems + ["The manifest is not valid JSON. Fix manifest.json and try again."]
        if not isinstance(manifest, dict):
            return problems + [
                "The manifest must be a JSON object. Fix manifest.json and try again."
            ]
        if manifest.get("format") != 1:
            problems.append("The format version is not 1. Set format to 1 in manifest.json.")
        name, author, license_name = (
            manifest.get("name"),
            manifest.get("author"),
            manifest.get("license"),
        )
        if not isinstance(name, str) or not 1 <= len(name) <= 40:
            problems.append(
                "The character name must have 1 to 40 characters. Change the name in the manifest."
            )
        if not isinstance(author, str) or not author.strip() or len(author) > 60:
            problems.append(
                "The author must have 1 to 60 characters. Add an author in the manifest."
            )
        if not isinstance(license_name, str) or not license_name.strip():
            problems.append("The license is missing or empty. Add an SPDX license ID or own work.")
        for field, value in (("name", name), ("author", author)):
            if isinstance(value, str):
                personal = _personal_field(value)
                if personal:
                    problems.append(f"Remove the {personal} from the {field} field.")
        mode = manifest.get("mode")
        if mode not in pf.MODES:
            problems.append("The mode is not supported. Choose picture, overlay or sequence.")
        if mode == "sequence" and (
            isinstance(manifest.get("fps"), bool)
            or not isinstance(manifest.get("fps"), int)
            or not pf.MIN_FPS <= manifest["fps"] <= pf.MAX_FPS
        ):
            problems.append(
                "The sequence frame rate must be from 1 to 12. Set fps to a number in that range."
            )
        if mode == "overlay":
            try:
                pf.check_overlay(manifest.get("overlay", {}))
            except (pf.PictureError, TypeError):
                problems.append(
                    "The overlay places are not valid. Set valid eye and mouth places in the manifest."
                )
        looks = manifest.get("looks")
        if not isinstance(looks, dict):
            problems.append("The manifest has no looks object. Add pictures under looks.neutral.")
            return problems
        if "neutral" not in looks:
            problems.append("The pack has no neutral picture. Add one image under looks.neutral.")
        for slot, paths in looks.items():
            if slot not in pf.SLOTS:
                problems.append(f"The slot {slot} is not known. Use a supported expression name.")
                continue
            paths = [paths] if isinstance(paths, str) else paths
            if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
                problems.append(
                    f"The pictures for {slot} must be a list of image paths. Fix looks.{slot}."
                )
                continue
            expected = 1 if mode in ("picture", "overlay") else 6
            if not paths or (expected == 1 and len(paths) != 1) or len(paths) > expected:
                problems.append(
                    f"The {slot} slot has the wrong number of pictures. Add one picture, or up to 6 for a sequence."
                )
            for image_path in paths:
                if image_path not in archive.namelist():
                    problems.append(
                        f"The image {image_path} is missing from the pack. Add that file to the ZIP."
                    )
                    continue
                info = archive.getinfo(image_path)
                if info.file_size > MAX_IMAGE_BYTES:
                    problems.append(
                        f"The image {image_path} is larger than 4 MB. Use a smaller image."
                    )
                    continue
                try:
                    data = archive.read(image_path)
                    _kind, width, height = _image_info(data)
                    if width < 1 or height < 1:
                        raise ValueError
                    if width * height > pf.MAX_SOURCE_PIXELS:
                        problems.append(
                            f"The image {image_path} has more than 12,000,000 pixels. Resize it."
                        )
                except (OSError, ValueError, RuntimeError, IndexError):
                    problems.append(
                        f"The image {image_path} is not a readable PNG or JPEG. Replace it with a valid image."
                    )
    return problems


def load_pack(path: str | Path) -> pf.PictureSet:
    problems = validate_pack(path)
    if problems:
        raise pf.PictureError(problems[0])
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        pictures = pf.PictureSet(
            mode=manifest["mode"],
            fps=manifest.get("fps", pf.DEFAULT_FPS),
            overlay=pf.check_overlay(manifest.get("overlay", {}))
            if manifest["mode"] == "overlay"
            else dict(pf.DEFAULT_OVERLAY),
        )
        for slot, paths in manifest["looks"].items():
            frames = []
            for image_path in paths:
                rgba, width, height = _decode_png(archive.read(image_path))
                frame = pf.resize_rgba(rgba, width, height)
                frames.append(pf.encode_frame(pf.to_rgb565(frame)))
            pictures.frames[slot] = frames
    return pictures


def build_pack(
    source_dir: str | Path,
    out_zip: str | Path,
    name: str,
    author: str,
    license: str,
    mode: str = "picture",
    fps: int = 6,
    overlay: dict[str, Any] | None = None,
) -> Path:
    source, output = Path(source_dir), Path(out_zip)
    looks: dict[str, list[str]] = {}
    for slot in pf.SLOTS:
        found: list[str] = []
        indexes = range(1, 7) if mode == "sequence" else (None,)
        for index in indexes:
            stem = f"{slot}_{index}" if index is not None else slot
            candidate = next(
                (
                    source / f"{stem}{ext}"
                    for ext in (".png", ".jpg", ".jpeg")
                    if (source / f"{stem}{ext}").is_file()
                ),
                None,
            )
            if candidate:
                found.append(candidate.name)
        if found:
            looks[slot] = found
    manifest: dict[str, Any] = {
        "format": 1,
        "name": name,
        "author": author,
        "license": license,
        "mode": mode,
        "looks": looks,
    }
    if mode == "sequence":
        manifest["fps"] = fps
    if mode == "overlay":
        manifest["overlay"] = overlay if overlay is not None else dict(pf.DEFAULT_OVERLAY)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for paths in looks.values():
            for image_path in paths:
                archive.write(source / image_path, image_path)
    problems = validate_pack(output)
    if problems:
        raise pf.PictureError(problems[0])
    return output
