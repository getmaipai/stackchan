#!/usr/bin/env python3
"""Intent: owner decision 14 (2026-11-18): nothing in this project ever burns an eFuse (irreversible): no secure boot key, no flash or NVS encryption key
in an eFuse, no HMAC key block. This check fails when a config, a patch, a script or a built image could do it.
Usage: python3 scripts/efuse-check.py                  scans the repository (build overlays, Kconfig defaults, patches, scripts)
       python3 scripts/efuse-check.py --build DIR      also scans one build directory (DIR/../sdkconfig.f* and the ELF's symbols)
Exit 0: nothing found. Exit 1: each finding is printed with the file and the reason. Placement: host-side check; no firmware change. Upstream: none."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONFIG = re.compile(
    r"^\s*CONFIG_(SECURE_BOOT|SECURE_BOOT_V1_ENABLED|SECURE_BOOT_V2_ENABLED|SECURE_FLASH_ENC_ENABLED|SECURE_FLASH_ENCRYPTION_MODE_RELEASE|SECURE_FLASH_ENCRYPTION_MODE_DEVELOPMENT|"
    r"FLASH_ENCRYPTION_ENABLED|NVS_ENCRYPTION|NVS_SEC_KEY_PROTECT_USING_HMAC|NVS_SEC_KEY_PROTECT_USING_FLASH_ENC|SECURE_DISABLE_ROM_DL_MODE|SECURE_ENABLE_SECURE_ROM_DL_MODE|"
    r"SECURE_BOOT_ALLOW_ROM_BASIC|SECURE_BOOT_ALLOW_JTAG)\s*=\s*y\b"
)
KCONFIG_DEFAULT = re.compile(r"^\s*default\s+y\b")
CALL = re.compile(
    r"\b(esp_efuse_(?:write|batch_write|burn|set_write_protect|set_read_protect|set_key|set_keypurpose)\w*|esp_flash_encryption_(?:enable|set_release_mode)\w*|"
    r"esp_secure_boot_(?:enable|permanently|generate)\w*|esp_efuse_disable_\w+|esp_efuse_set_rom_log\w*)\s*\("
)
TOOL = re.compile(r"\b(espefuse(?:\.py)?|burn[_-]efuse|burn[_-]key|efuse[_-]burn|espsecure(?:\.py)?\s+(?:digest|generate)[\w-]*)\b")
BAD_SYMBOL = re.compile(r"\b(esp_efuse_(?:write|batch_write|burn|set_write_protect|set_read_protect|set_key)\w*|esp_flash_encryption_enable\w*|esp_secure_boot_(?:enable|permanently)\w*)\b")
SKIP = {"efuse-check.py"}


def scan_text(label: str, text: str, patterns: list[tuple[re.Pattern[str], str]], only_added: bool = False) -> list[str]:
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if only_added:
            if not line.startswith("+") or line.startswith("+++"):
                continue
            line = line[1:]
        stripped = line.lstrip()
        if stripped.startswith("#") and "CONFIG_" not in stripped:
            continue
        for pattern, why in patterns:
            if pattern.search(line):
                found.append(f"{label}:{n}: {why}: {line.strip()[:120]}")
    return found


def scan_repo() -> list[str]:
    found: list[str] = []
    for path in sorted((ROOT / "firmware").rglob("*")):
        if not path.is_file() or path.name in SKIP:
            continue
        rel = str(path.relative_to(ROOT))
        if path.suffix == ".patch":
            found += scan_text(rel, path.read_text(errors="replace"), [(CALL, "an eFuse or encryption write call"), (CONFIG, "a config that burns an eFuse")], only_added=True)
        elif ".defaults" in path.name or path.name.startswith("sdkconfig"):
            found += scan_text(rel, path.read_text(errors="replace"), [(CONFIG, "a config that burns an eFuse")])
    for path in sorted((ROOT / "scripts").rglob("*")):
        if path.is_file() and path.name not in SKIP and path.suffix in {".sh", ".py", ".md", ""} and "node_modules" not in path.parts:
            found += scan_text(str(path.relative_to(ROOT)), path.read_text(errors="replace"), [(TOOL, "a tool that burns an eFuse")])
    # a patch that adds a Kconfig option must not default a burning option on
    for path in sorted((ROOT / "firmware" / "patches").glob("*.patch")):
        text = path.read_text(errors="replace")
        for m in re.finditer(r"^\+config (SECURE_BOOT\w*|SECURE_FLASH_ENC\w*|FLASH_ENCRYPTION\w*|NVS_ENCRYPTION)\b", text, re.M):
            found.append(f"firmware/patches/{path.name}: a patch defines the option {m.group(1)}, which burns an eFuse when on")
    return found


def scan_build(build: Path) -> list[str]:
    found: list[str] = []
    for cfg in sorted(build.parent.glob("sdkconfig*")):
        if cfg.is_file() and "defaults" not in cfg.name and "old" not in cfg.name:
            found += scan_text(str(cfg), cfg.read_text(errors="replace"), [(CONFIG, "a config that burns an eFuse")])
    elf = build / "maipai-stackchan.elf"
    nm = sorted(Path.home().glob(".espressif/tools/xtensa-esp-elf/*/xtensa-esp-elf/bin/xtensa-esp32s3-elf-nm"))
    if elf.exists() and nm:
        out = subprocess.run([str(nm[-1]), str(elf)], capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[1] in "tTwW" and BAD_SYMBOL.search(parts[2]):
                found.append(f"{elf}: the image contains code that can burn an eFuse: {parts[2]}")
    elif elf.exists():
        found.append(f"{elf}: cannot check the symbols: the xtensa nm tool was not found; install the ESP-IDF tools")
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", type=Path, help="a build directory (firmware/build-KIND) to scan as well")
    args = ap.parse_args()
    found = scan_repo()
    if args.build:
        found += scan_build(args.build)
    for line in found:
        print(line)
    if found:
        print(f"efuse-check: {len(found)} finding(s). Owner decision 14: nothing may burn an eFuse. Remove it, or ask the owner to change the rule.", file=sys.stderr)
        return 1
    print("efuse-check: ok (no eFuse or encryption burn in configs, patches, scripts" + (" or the build" if args.build else "") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
