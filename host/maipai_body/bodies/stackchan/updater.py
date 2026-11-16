"""Flasher and updater: check a signed release, then flash it or push it over the air.

Nothing here touches a unit unless the caller passes ``dry_run=False`` and a real runner.
Every refusal is an ``UpdateRefused`` whose text says what went wrong and what to do.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from maipai_body.i18n import t

PRESETS = ("core", "home")
FREE_SLOT_PERCENT = 20
PARTITION_TABLE_OFFSET = 0x8000
DEFAULT_KEY_PATH = Path.home() / ".config" / "maipai" / "stackchan-release.pub.pem"
APP_NAME = "stack-chan-maipai.bin"


class UpdateRefused(Exception):
    """A release or request was refused; ``str(error)`` is the plain message."""


@dataclass(frozen=True)
class SlotReport:
    app_path: str
    app_size: int
    slot_size: int
    free_percent: float

    def line(self, lang: str | None = None) -> str:
        return t(
            lang,
            "update.slot_ok",
            size=self.app_size,
            slot=self.slot_size,
            free=self.free_percent,
            need=FREE_SLOT_PERCENT,
        )


@dataclass(frozen=True)
class VerifiedRelease:
    folder: Path
    manifest: dict[str, Any]
    preset: str
    version: str
    parts: tuple[dict[str, Any], ...]
    slot: SlotReport

    def app_part(self) -> dict[str, Any]:
        return next(part for part in self.parts if part["path"] == self.slot.app_path)


def preset_of(manifest: dict[str, Any]) -> str:
    """The preset lives in the manifest id: stackchan-esp32s3-<preset>-<version>.

    The pinned manifest schema has no preset field and refuses extra ones, so the id carries it
    until the spec adds one. An id with no preset word is the core preset.
    """
    ident = str(manifest.get("id", ""))
    for preset in PRESETS:
        if f"-{preset}-" in ident:
            return preset
    return "core"


def ota_slots(table: bytes) -> list[tuple[int, int]]:
    """Return (offset, size) of every OTA app slot in an ESP32 partition table image."""
    slots: list[tuple[int, int]] = []
    for index in range(0, len(table) - 31, 32):
        magic, kind, subtype, offset, size, _label, _flags = struct.unpack(
            "<2sBBII16sI", table[index : index + 32]
        )
        if magic != b"\xaa\x50":
            break
        if kind == 0 and 0x10 <= subtype <= 0x1F:
            slots.append((offset, size))
    return slots


def check_slot_rule(parts: Sequence[dict[str, Any]], folder: Path, lang: str | None) -> SlotReport:
    """The 20 percent rule: the app image must leave 20 percent of the smallest OTA slot free."""
    table_part = next((p for p in parts if p["offset"] == PARTITION_TABLE_OFFSET), None)
    if table_part is None:
        raise UpdateRefused(t(lang, "update.no_table"))
    slots = ota_slots((folder / table_part["path"]).read_bytes())
    if not slots:
        raise UpdateRefused(t(lang, "update.no_table"))
    first_offset = min(offset for offset, _ in slots)
    app = next((p for p in parts if p["offset"] == first_offset), None)
    if app is None:
        raise UpdateRefused(t(lang, "update.no_table"))
    smallest = min(size for _, size in slots)
    free = 100.0 * (smallest - app["size"]) / smallest
    report = SlotReport(app["path"], app["size"], smallest, free)
    if free < FREE_SLOT_PERCENT:
        raise UpdateRefused(
            t(lang, "update.slot_rule", free=max(free, 0.0), need=FREE_SLOT_PERCENT)
        )
    return report


def _verify_signature(manifest: dict[str, Any], key: Path, lang: str | None) -> None:
    from maipai_body.bodies.stackchan.firmware import flash_manifest

    if "signature" not in manifest:
        raise UpdateRefused(t(lang, "update.unsigned"))
    if not key.is_file():
        raise UpdateRefused(t(lang, "update.no_key", path=key))
    try:
        flash_manifest.validate_manifest(manifest)
    except ValueError as error:
        raise UpdateRefused(t(lang, "update.bad_manifest", why=str(error)[:200])) from error
    if not flash_manifest.verify_manifest(manifest, key):
        raise UpdateRefused(t(lang, "update.bad_signature"))


def load_release(
    folder: str | Path,
    *,
    public_key: str | Path | None = None,
    preset: str | None = None,
    lang: str | None = None,
) -> VerifiedRelease:
    """Read a release folder and refuse anything unsigned, altered or mismatched."""
    folder = Path(folder)
    manifest_path = folder / "flash-manifest.json"
    if not manifest_path.is_file():
        raise UpdateRefused(
            t(lang, "update.bad_manifest", why=f"no flash-manifest.json in {folder}")
        )
    try:
        manifest = json.loads(manifest_path.read_text())
        if not isinstance(manifest, dict):
            raise ValueError("not an object")
    except ValueError as error:
        raise UpdateRefused(t(lang, "update.bad_manifest", why=str(error))) from error
    _verify_signature(manifest, Path(public_key) if public_key else DEFAULT_KEY_PATH, lang)
    found = preset_of(manifest)
    if preset is not None and preset != found:
        raise UpdateRefused(t(lang, "update.wrong_preset", found=found, wanted=preset))
    chips = {build.get("chipFamily") for build in manifest["builds"]}
    if chips != {"ESP32-S3"}:
        raise UpdateRefused(t(lang, "update.wrong_chip", found=", ".join(sorted(map(str, chips)))))
    parts = tuple(
        sorted((p for b in manifest["builds"] for p in b["parts"]), key=lambda p: p["offset"])
    )
    for part in parts:
        path = folder / part["path"]
        if not path.is_file():
            raise UpdateRefused(t(lang, "update.part_missing", name=part["path"], folder=folder))
        data = path.read_bytes()
        if len(data) != part["size"] or hashlib.sha256(data).hexdigest() != part["sha256"]:
            raise UpdateRefused(t(lang, "update.part_mismatch", name=part["path"]))
    slot = check_slot_rule(parts, folder, lang)
    return VerifiedRelease(folder, manifest, found, str(manifest["version"]), parts, slot)


def _version(value: str) -> tuple[int, ...]:
    out: list[int] = []
    for piece in value.lstrip("vV").split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def is_newer(release: str, unit: str | None) -> bool:
    if not unit:
        return True
    width = max(len(_version(release)), len(_version(unit)))
    pad = lambda v: v + (0,) * (width - len(v))  # noqa: E731
    return pad(_version(release)) > pad(_version(unit))


Runner = Callable[[Sequence[str]], int]


def esptool_command(release: VerifiedRelease, port: str, baud: int = 460800) -> list[str]:
    flash_size = str(release.manifest["flash_size"])
    command = [
        "--chip", "esp32s3", "--port", port, "--baud", str(baud),
        "write_flash", "--flash_size", flash_size,
    ]  # fmt: skip
    for part in release.parts:
        command += [hex(part["offset"]), str(release.folder / part["path"])]
    return command


def _find_esptool() -> list[str] | None:
    direct = shutil.which("esptool") or shutil.which("esptool.py")
    if direct:
        return [direct]
    try:
        import esptool  # noqa: F401
    except ImportError:
        return None
    return [sys.executable, "-m", "esptool"]


def _run_subprocess(command: Sequence[str]) -> int:
    return subprocess.run(list(command), check=False).returncode


@dataclass
class FlashResult:
    release: VerifiedRelease
    command: list[str]
    dry_run: bool
    flashed: bool = False
    notes: list[str] = field(default_factory=list)


def flash(
    release: VerifiedRelease,
    *,
    port: str | None,
    dry_run: bool,
    baud: int = 460800,
    runner: Runner | None = None,
    lang: str | None = None,
) -> FlashResult:
    """Write every manifest part with esptool. A dry run builds the command and stops."""
    if not port:
        raise UpdateRefused(t(lang, "update.needs_port"))
    command = esptool_command(release, port, baud)
    result = FlashResult(release, command, dry_run)
    if dry_run:
        result.notes.append(t(lang, "update.dry"))
        return result
    tool = _find_esptool() if runner is None else ["esptool"]
    if tool is None:
        raise UpdateRefused(t(lang, "update.no_esptool"))
    code = (runner or _run_subprocess)(tool + command)
    if code != 0:
        raise UpdateRefused(t(lang, "update.esptool_failed", code=code))
    result.flashed = True
    return result


OtaPush = Callable[[str, Path, str, int, str], object]


def update_over_air(
    release: VerifiedRelease,
    *,
    device_id: str,
    unit_version: str | None,
    push: OtaPush | None,
    dry_run: bool,
    lang: str | None = None,
) -> str:
    """Push only the app image to a running unit. ``push`` calls the unit's update tool."""
    if not is_newer(release.version, unit_version):
        raise UpdateRefused(t(lang, "update.not_newer", unit=unit_version, release=release.version))
    app = release.app_part()
    if dry_run:
        return t(lang, "update.dry")
    if push is None:
        raise UpdateRefused(t(lang, "update.no_host", url="the host"))
    push(device_id, release.folder / app["path"], app["sha256"], app["size"], release.version)
    return t(lang, "settings.update.started")


def read_source(source: str | Path | None) -> Path | None:
    """Resolve update_source to a local release folder; None means no source is set."""
    if not source:
        return None
    return Path(str(source)).expanduser()
