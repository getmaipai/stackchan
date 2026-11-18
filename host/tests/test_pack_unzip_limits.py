"""A pack that unpacks to far more than its size is refused before it fills memory."""

import io
import zipfile

import pytest

from maipai_body import packs


def _zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buf.getvalue()


def test_normal_payload_unzips():
    assert packs.unzip_payload(_zip({"a.txt": b"hello"})) == {"a.txt": b"hello"}


def test_expanded_size_over_the_cap_is_refused(monkeypatch):
    monkeypatch.setattr(packs, "MAX_UNZIPPED_BYTES", 1000)
    bomb = _zip({"zeros.bin": bytes(5000)})
    assert len(bomb) < 200  # tiny on the wire, big when opened
    with pytest.raises(packs.PackError, match="unpacks to more than"):
        packs.unzip_payload(bomb)


def test_too_many_files_is_refused(monkeypatch):
    monkeypatch.setattr(packs, "MAX_UNZIPPED_FILES", 3)
    with pytest.raises(packs.PackError, match="more than 3 files"):
        packs.unzip_payload(_zip({f"{n}.txt": b"x" for n in range(4)}))


def test_unsafe_names_are_refused():
    for name in ("../evil.txt", "/abs.txt"):
        with pytest.raises(packs.PackError, match="unsafe"):
            packs.unzip_payload(_zip({name: b"x"}))
