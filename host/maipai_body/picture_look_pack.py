"""A picture-face set as a shared-loader look pack (firmware patch TB02).

The payload is a zip with ``look.json`` and one STORED file per frame (the unit reads the frames in place; they are already
zlib streams or raw RGB565)::

    {"kind": "picture", "mode": "picture|overlay|sequence", "fps": 6, "overlay": {...},
     "frames": [{"slot": "neutral", "index": 0, "file": "neutral_0.bin", "raw": false, "crc": "1a2b3c4d"}]}

The CRC is the CRC-32 of the stored file, as in the older ``self.facepic`` tools.
"""

from __future__ import annotations

import io
import json
import zipfile

from maipai_body import packs as packs_mod
from maipai_body.picture_faces import PictureSet


def look_payload(pictures: PictureSet) -> bytes:
    frames = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as archive:
        for slot, items in pictures.frames.items():
            for index, frame in enumerate(items):
                name = f"{slot}_{index}.bin"
                archive.writestr(name, frame.payload)
                frames.append({"slot": slot, "index": index, "file": name, "raw": frame.raw, "crc": f"{frame.crc:08x}"})
        look = {"kind": "picture", "mode": pictures.mode, "fps": pictures.fps, "frames": frames}
        if pictures.mode == "overlay":
            look["overlay"] = pictures.overlay
        archive.writestr("look.json", json.dumps(look, separators=(",", ":")))
    return buf.getvalue()


def look_pack(pictures: PictureSet, name: str = "Pictures", version: int = 1) -> packs_mod.Pack:
    return packs_mod.make_pack("look", name, look_payload(pictures), version=version)
