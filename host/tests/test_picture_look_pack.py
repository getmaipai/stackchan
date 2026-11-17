"""The picture look pack (firmware patch TB02): stored files, a look.json the unit reads, within the look size gate."""

import json
import zipfile
import io

from maipai_body import packs
from maipai_body.picture_faces import PictureSet, encode_frame
from maipai_body.picture_look_pack import look_pack


def _set() -> PictureSet:
    raw = bytes(range(256)) * 600  # 153,600 bytes
    return PictureSet(mode="sequence", fps=4, frames={"neutral": [encode_frame(raw)], "happy": [encode_frame(raw[::-1]), encode_frame(raw)]})


def test_look_pack_is_a_stored_zip_with_look_json_and_passes_the_gate():
    pack = look_pack(_set(), "Mine")
    assert pack.type == "look" and pack.size <= packs.MAX_BYTES["look"]
    z = zipfile.ZipFile(io.BytesIO(pack.payload))
    assert all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist())
    look = json.loads(z.read("look.json"))
    assert look["kind"] == "picture" and look["mode"] == "sequence" and look["fps"] == 4 and len(look["frames"]) == 3
    for f in look["frames"]:
        assert f["file"] in z.namelist() and len(f["crc"]) == 8
    assert packs.decode(packs.encode(pack)).sha256 == pack.sha256
