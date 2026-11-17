#!/usr/bin/env python3
"""Read the flash core dump of a StackChan unit and decode it with the ELF of the build (patch FM02).

Intent: after a panic or a watchdog reset the unit keeps registers and task stacks in its coredump partition
(0xFF0000, 64 KB). This script reads that partition (over the serial port with esptool, or from a file read earlier),
checks that it holds a whole dump, and decodes it with `esp-coredump` and the ELF the unit runs. It never writes
to the unit except with --erase, which clears only the coredump partition.
Placement: host tooling for the developer (the unit and its ELF are the inputs; nothing runs on the robot).
Upstream: the esp-coredump tool of ESP-IDF (Apache-2.0), run as a command.

Usage:
  python3 scripts/fw-coredump.py --port /dev/cu.usbmodem1101 --elf firmware/build/stackchan.elf
  python3 scripts/fw-coredump.py --file dump.bin --elf firmware/build/stackchan.elf
  python3 scripts/fw-coredump.py --port PORT --save dump.bin      (read and keep the raw partition, no ELF needed)

The USB lock: while ~/stackchan-models/usb-switch.lock exists, the port belongs to another session and this script
refuses to open it. Pass --lock-held only when this session took that lock itself.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

PARTITION_OFFSET = 0xFF0000
PARTITION_SIZE = 0x10000
LOCK = Path.home() / "stackchan-models" / "usb-switch.lock"
HEADER = struct.Struct("<III")  # total length (header, data and checksum), version, chip revision
CHECKSUM_LEN = 32  # SHA-256 at the end of the data (CRC-32 would be 4); the length check below accepts both


class DumpError(Exception):
    """A problem with the partition contents; the text says what to do next."""


def inspect(blob: bytes) -> tuple[str, int]:
    """Classify the partition bytes: ("empty", 0), ("whole", length) or raise DumpError for a damaged or cut dump."""
    if len(blob) < HEADER.size:
        raise DumpError("The file is shorter than the 12 byte core dump header. Read the whole 64 KB partition again.")
    if blob[: HEADER.size] == b"\xff" * HEADER.size or blob[:4] == b"\x00\x00\x00\x00":
        return "empty", 0
    total, version, _chip = HEADER.unpack_from(blob)
    if version == 0 or total < HEADER.size + CHECKSUM_LEN:
        raise DumpError(
            f"The header does not look like a core dump (length {total}, version {version}). "
            "Read the partition again; if it repeats, erase it with --erase."
        )
    if total > len(blob):
        raise DumpError(
            f"The dump is {total} bytes but the partition holds {len(blob)}: it was cut short and cannot be decoded. "
            "Lower CONFIG_ESP_COREDUMP_MAX_TASKS_NUM in firmware/sdkconfig.core.defaults, rebuild and reproduce the crash."
        )
    return "whole", total


def port_is_free() -> None:
    if LOCK.exists():
        raise DumpError(
            f"{LOCK} exists: another session holds the unit's USB port. Wait for it to end, "
            "or read a dump file you already have with --file."
        )


def read_partition(port: str, lock_held: bool) -> bytes:
    if not lock_held:
        port_is_free()
    tool = shutil.which("esptool.py") or shutil.which("esptool")
    if tool is None:
        raise DumpError("esptool is not on the path. Run: source scripts/fw-env.sh")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "coredump.bin"
        cmd = [tool, "--port", port, "read_flash", hex(PARTITION_OFFSET), hex(PARTITION_SIZE), str(out)]
        done = subprocess.run(cmd, capture_output=True, text=True)
        if done.returncode != 0:
            raise DumpError(
                f"esptool could not read the unit ({done.stderr.strip() or done.stdout.strip()}). "
                "Check the cable and that no other program has the port open."
            )
        return out.read_bytes()


def decode(blob: bytes, elf: Path, gdb: bool) -> int:
    tool = shutil.which("esp-coredump")
    if tool is None:
        raise DumpError("esp-coredump is not on the path. Run: source scripts/fw-env.sh")
    if not elf.is_file():
        raise DumpError(f"The ELF {elf} is missing. Use the .elf of the exact build the unit ran (firmware/build/*.elf).")
    status, total = inspect(blob)
    if status == "empty":
        print("no core dump: the partition is empty.")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        core = Path(tmp) / "core.bin"
        core.write_bytes(blob[:total])
        verb = "dbg_corefile" if gdb else "info_corefile"
        cmd = [tool, verb, "--core-format", "raw", "--core", str(core), str(elf)]
        return subprocess.run(cmd).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--port", help="serial port of the unit")
    src.add_argument("--file", type=Path, help="a raw partition read earlier")
    ap.add_argument("--elf", type=Path, help="the ELF of the build the unit ran")
    ap.add_argument("--save", type=Path, help="write the raw partition here")
    ap.add_argument("--gdb", action="store_true", help="open gdb on the dump instead of printing the summary")
    ap.add_argument("--erase", action="store_true", help="after reading, erase the coredump partition (needs --port)")
    ap.add_argument("--lock-held", action="store_true", help="this session holds the USB lock")
    args = ap.parse_args(argv)
    try:
        blob = read_partition(args.port, args.lock_held) if args.port else args.file.read_bytes()
        if args.save:
            args.save.write_bytes(blob)
            print(f"saved {len(blob)} bytes to {args.save}")
        if args.elf is None:
            status, total = inspect(blob)
            print("no core dump: the partition is empty." if status == "empty" else f"a whole dump of {total} bytes; pass --elf to decode it.")
            code = 0
        else:
            code = decode(blob, args.elf, args.gdb)
        if args.erase and args.port:
            tool = shutil.which("esptool.py") or shutil.which("esptool")
            subprocess.run([tool, "--port", args.port, "erase_region", hex(PARTITION_OFFSET), hex(PARTITION_SIZE)], check=True)
            print("coredump partition erased.")
        return code
    except DumpError as err:
        print(f"fw-coredump: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
