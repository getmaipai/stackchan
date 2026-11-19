#!/usr/bin/env python3
"""Intent: write the sdkconfig.h a host or WebAssembly build of the unit's screens needs, without ESP-IDF: the firmware's sdkconfig.defaults and sdkconfig.bench.defaults,
plus the default of every `config MAIPAI_*` and other option in main/Kconfig.projbuild (the IDF build would fold those in; a plain defaults file does not carry them).
Usage: gen_sdkconfig.py FIRMWARE_DIR OUT_FILE
Placement: host-side development tool. Upstream: none."""
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: gen_sdkconfig.py FIRMWARE_DIR OUT_FILE. Give the replayed firmware folder and the header to write.")
        return 2
    fw, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    cfg: dict[str, str] = {}
    kc = (fw / "main" / "Kconfig.projbuild").read_text()
    for block in re.split(r"^\s*config\s+", kc, flags=re.M)[1:]:
        name = block.split()[0]
        kind = re.search(r"^\s*(bool|int|string|hex)\b", block, re.M)
        default = re.search(r"^\s*default\s+(\S+)", block, re.M)
        if kind and default:
            v = default.group(1)
            cfg[f"CONFIG_{name}"] = "1" if v == "y" else ("" if v == "n" else v)
    for f in ("sdkconfig.defaults", "sdkconfig.bench.defaults"):
        for line in (fw / f).read_text().splitlines():
            line = line.strip()
            if not line.startswith("CONFIG_") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k] = "" if v == "n" else ("1" if v == "y" else v)
    lines = ["#pragma once"] + [f"#define {k} {v}" for k, v in cfg.items() if v != ""]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {out_path}: {len(lines) - 1} options")
    return 0


if __name__ == "__main__":
    sys.exit(main())
