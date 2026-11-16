import hashlib
import json
import os
import struct
import subprocess

os.environ["TMPDIR"] = "/private/tmp"

import pytest

from maipai_body.bodies.stackchan import updater
from maipai_body.bodies.stackchan.firmware import flash_manifest
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

SLOT = 0x500000


def _entry(kind, subtype, offset, size, label):
    return struct.pack("<2sBBII16sI", b"\xaa\x50", kind, subtype, offset, size, label.encode(), 0)


def _table(slot_size=SLOT, second=SLOT):
    rows = [
        _entry(1, 2, 0x9000, 0x4000, "nvs"),
        _entry(1, 0, 0xD000, 0x2000, "otadata"),
        _entry(0, 0x10, 0x20000, slot_size, "ota_0"),
        _entry(0, 0x11, 0x20000 + SLOT, second, "ota_1"),
    ]
    return b"".join(rows) + b"\xff" * 64


def _keys(tmp_path):
    private, public = tmp_path / "k.pem", tmp_path / "k.pub"
    subprocess.run(
        [openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(private)],
        check=True,
        capture_output=True,
    )
    public.write_bytes(
        subprocess.run(
            [openssl_cli(), "pkey", "-in", str(private), "-pubout"], check=True, capture_output=True
        ).stdout
    )
    return private, public


def make_release(
    tmp_path,
    *,
    version="1.2.0",
    preset="core",
    app_size=1000,
    slot_size=SLOT,
    second=SLOT,
    key=None,
    sign=True,
):
    folder = tmp_path / f"rel-{version}-{preset}"
    folder.mkdir()
    files = {
        "bootloader.bin": (0x0, b"B" * 64),
        "partition-table.bin": (0x8000, _table(slot_size, second)),
        "ota_data_initial.bin": (0xD000, b"O" * 32),
        "stack-chan-maipai.bin": (0x20000, b"A" * app_size),
    }
    parts = []
    for name, (offset, data) in files.items():
        (folder / name).write_bytes(data)
        parts.append(
            {
                "path": name,
                "offset": offset,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = flash_manifest.build_manifest(
        parts, version=version, flash_size="16MB",
        created_at="2026-11-15T00:00:00Z", hlc="1794000000000:0:stackchan01",
    )  # fmt: skip
    manifest["id"] = f"stackchan-esp32s3-{preset}-{version}"
    private, public = key or _keys(tmp_path)
    if sign:
        manifest = flash_manifest.sign_manifest(manifest, private)
    (folder / "flash-manifest.json").write_text(json.dumps(manifest))
    (folder / "stack-chan-maipai.bin.sig").write_bytes(b"S" * 64)  # a stand-in; ota tests sign for real
    return folder, public, (private, public)


def test_good_release_passes_and_reports_free_slot(tmp_path):
    folder, public, _ = make_release(tmp_path)
    release = updater.load_release(folder, public_key=public, preset="core")
    assert release.version == "1.2.0" and release.preset == "core"
    assert release.slot.free_percent > 99
    assert "percent free (rule: at least 20 percent)" in release.slot.line()


def test_unsigned_release_is_refused_with_plain_message(tmp_path):
    folder, public, _ = make_release(tmp_path, sign=False)
    with pytest.raises(updater.UpdateRefused, match="not signed.*Download the release again"):
        updater.load_release(folder, public_key=public)


def test_missing_trusted_key_names_the_path(tmp_path):
    folder, _, _ = make_release(tmp_path)
    with pytest.raises(updater.UpdateRefused, match="No trusted release key.*nokey.pem"):
        updater.load_release(folder, public_key=tmp_path / "nokey.pem")


def test_other_signing_key_is_refused(tmp_path):
    folder, _, _ = make_release(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    _, other_public = _keys(other)
    with pytest.raises(updater.UpdateRefused, match="signature does not match"):
        updater.load_release(folder, public_key=other_public)


def test_altered_part_is_refused(tmp_path):
    folder, public, _ = make_release(tmp_path)
    (folder / "stack-chan-maipai.bin").write_bytes(b"X" * 1000)
    with pytest.raises(updater.UpdateRefused, match="stack-chan-maipai.bin does not match"):
        updater.load_release(folder, public_key=public)


def test_missing_part_is_refused(tmp_path):
    folder, public, _ = make_release(tmp_path)
    (folder / "bootloader.bin").unlink()
    with pytest.raises(updater.UpdateRefused, match="bootloader.bin is missing"):
        updater.load_release(folder, public_key=public)


def test_altered_manifest_fails_signature(tmp_path):
    folder, public, _ = make_release(tmp_path)
    path = folder / "flash-manifest.json"
    data = json.loads(path.read_text())
    data["version"] = "9.9.9"
    path.write_text(json.dumps(data))
    with pytest.raises(updater.UpdateRefused, match="signature does not match"):
        updater.load_release(folder, public_key=public)


def test_preset_mismatch_is_refused(tmp_path):
    folder, public, _ = make_release(tmp_path, preset="home")
    assert updater.load_release(folder, public_key=public, preset="home").preset == "home"
    with pytest.raises(updater.UpdateRefused, match="home preset but you asked for core"):
        updater.load_release(folder, public_key=public, preset="core")


def test_free_slot_rule_boundary(tmp_path):
    # 20 percent of the slot must stay free: exactly 80 percent used passes, one byte more fails.
    ok, public, _ = make_release(tmp_path, app_size=int(SLOT * 0.8))
    assert updater.load_release(ok, public_key=public).slot.free_percent == pytest.approx(
        20.0, abs=0.01
    )
    sub = tmp_path / "b"
    sub.mkdir()
    bad, public2, _ = make_release(sub, app_size=int(SLOT * 0.8) + 1000)
    with pytest.raises(updater.UpdateRefused, match="below the 20 percent rule"):
        updater.load_release(bad, public_key=public2)


def test_smallest_slot_is_the_one_measured(tmp_path):
    folder, public, _ = make_release(tmp_path, app_size=3000, slot_size=SLOT, second=3500)
    with pytest.raises(updater.UpdateRefused, match="20 percent rule"):
        updater.load_release(folder, public_key=public)


def test_flash_dry_run_builds_command_and_runs_nothing(tmp_path):
    folder, public, _ = make_release(tmp_path)
    release = updater.load_release(folder, public_key=public)
    calls = []
    result = updater.flash(release, port="/dev/cu.test", dry_run=True, runner=calls.append)
    assert calls == [] and not result.flashed
    assert result.command[:6] == ["--chip", "esp32s3", "--port", "/dev/cu.test", "--baud", "460800"]
    assert result.command.count("write_flash") == 1
    assert "0x20000" in result.command and str(folder / "stack-chan-maipai.bin") in result.command


def test_flash_needs_a_port_even_for_dry_run(tmp_path):
    folder, public, _ = make_release(tmp_path)
    release = updater.load_release(folder, public_key=public)
    with pytest.raises(updater.UpdateRefused, match="Say which serial port"):
        updater.flash(release, port=None, dry_run=True)


def test_flash_real_path_uses_runner_and_reports_failure(tmp_path):
    folder, public, _ = make_release(tmp_path)
    release = updater.load_release(folder, public_key=public)
    seen = []
    ok = updater.flash(
        release, port="/dev/x", dry_run=False, runner=lambda c: seen.append(list(c)) or 0
    )
    assert ok.flashed and seen[0][0] == "esptool"
    with pytest.raises(updater.UpdateRefused, match="esptool stopped with code 2.*download mode"):
        updater.flash(release, port="/dev/x", dry_run=False, runner=lambda c: 2)


def test_ota_pushes_app_image_only_and_only_when_newer(tmp_path):
    folder, public, _ = make_release(tmp_path, version="1.2.0")
    release = updater.load_release(folder, public_key=public)
    pushed = []
    push = lambda *a: pushed.append(a)  # noqa: E731
    msg = updater.update_over_air(
        release, device_id="aa:bb:cc:dd:ee:ff", unit_version="1.1.0", push=push, dry_run=False
    )
    assert "Update started" in msg
    device, path, sha, size, version = pushed[0]
    assert path.name == "stack-chan-maipai.bin" and size == 1000 and version == "1.2.0"
    assert sha == hashlib.sha256(b"A" * 1000).hexdigest()
    with pytest.raises(updater.UpdateRefused, match="nothing to update"):
        updater.update_over_air(
            release, device_id="x", unit_version="1.2.0", push=push, dry_run=False
        )
    updater.update_over_air(release, device_id="x", unit_version="1.0", push=push, dry_run=True)
    assert len(pushed) == 1


def test_spanish_refusal_message(tmp_path):
    folder, public, _ = make_release(tmp_path, sign=False)
    with pytest.raises(updater.UpdateRefused, match="no esta firmado"):
        updater.load_release(folder, public_key=public, lang="es")


def test_is_newer():
    assert updater.is_newer("1.10.0", "1.9.9") and not updater.is_newer("1.0", "1.0.0")
    assert updater.is_newer("0.0.1", None)


def test_cli_dry_run_flash_and_refusals(tmp_path, monkeypatch, capsys):
    from maipai_body import cli

    folder, public, _ = make_release(tmp_path)
    cfg = tmp_path / "robot.toml"
    cfg.write_text("")
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: __import__("maipai_body.config", fromlist=["x"]).load_config(cfg),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "stackchan",
            "flash",
            "--source",
            str(folder),
            "--public-key",
            str(public),
            "--port",
            "/dev/x",
            "--dry-run",
        ],
    )
    assert cli.main() == 0
    out = capsys.readouterr().out
    assert (
        "passed every check" in out and "esptool --chip esp32s3" in out and "flashed nothing" in out
    )
    monkeypatch.setattr(
        "sys.argv",
        ["stackchan", "flash", "--source", str(folder), "--public-key", str(public), "--dry-run"],
    )
    assert cli.main() == 2
    assert "Say which serial port" in capsys.readouterr().err
    (folder / "flash-manifest.json").write_text(
        json.dumps({**json.loads((folder / "flash-manifest.json").read_text()), "signature": None})
    )
    monkeypatch.setattr(
        "sys.argv",
        ["stackchan", "update", "--source", str(folder), "--public-key", str(public), "--dry-run"],
    )
    assert cli.main() == 2
