"""The renderer is rebuilt when its inputs changed: a stale binary draws old words and fails the goldens for no reason in the code."""

from __future__ import annotations

from pathlib import Path

from tests import conftest


def test_the_inputs_stamp_changes_with_a_face_patch(monkeypatch, tmp_path):
    before = conftest._inputs_stamp()
    assert before == conftest._inputs_stamp()  # stable
    real = Path.read_bytes
    patch = next(p for p in (conftest._REPO / "firmware" / "patches").glob("UX09-*.patch"))

    def read_bytes(self):
        data = real(self)
        return data + b"\n# changed" if self == patch else data

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    assert conftest._inputs_stamp() != before


def test_no_actual_pictures_are_tracked_and_they_are_ignored():
    import subprocess

    tracked = subprocess.run(["git", "ls-files", "*.actual.png"], cwd=conftest._REPO, capture_output=True, text=True).stdout.split()
    assert tracked == []
    assert "*.actual.png" in (conftest._REPO / ".gitignore").read_text()
