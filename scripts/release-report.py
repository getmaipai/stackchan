#!/usr/bin/env python3
"""One markdown page per firmware build: image sizes per slot, memory numbers from a stress log, frame cost per screen from the
virtual unit baseline, tool count and patch count. Lane P's record of what a build costs.
Usage: release-report.py BUILD_ROOT --name NAME [--memory-log LOG] [--out docs/dev/releases]
  BUILD_ROOT is the firmware folder that holds build-plain, build-gate and build-bench (for example ~/esp/stackchan-rebuild/b13/firmware).
  --memory-log is the log fw-stress.py wrote (lines "mem internal_free=... internal_min=... int_big=... psram_free=... psram_min=..."); without it
  the memory section says it was not measured, never invents numbers.
Writes OUT/NAME.md and prints its path. Placement: host-side development tool. Upstream: none."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDS = [
    ("build-plain", "plain (the image the owner runs)"),
    ("build-gate", "gate (memory line on)"),
    ("build-bench", "bench (serial tools on)"),
]
FREE_RULE = 0.20  # keep at least 20 percent of each OTA slot free (docs/design/firmware-memory.md)
MEM = re.compile(
    r"mem internal_free=(\d+) internal_min=(\d+) int_big=(\d+) psram_free=(\d+) psram_min=(\d+)"
)


def partitions(build_root: Path) -> dict[str, int]:
    """Partition sizes from the tree's partitions.csv (name -> bytes)."""
    sizes: dict[str, int] = {}
    path = build_root / "partitions.csv"
    if not path.exists():
        return sizes
    for row in csv.reader(
        line for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")
    ):
        cells = [c.strip() for c in row]
        if len(cells) >= 5 and cells[4]:
            sizes[cells[0]] = int(cells[4], 0)
    return sizes


def image_section(build_root: Path) -> list[str]:
    parts = partitions(build_root)
    slot = parts.get("ota_0", 0)
    out = [
        "## Images",
        "",
        "| Build | App image bytes | OTA slot bytes | Used | Free | Room left before the 20 percent rule |",
        "|---|---|---|---|---|---|",
    ]
    for folder, label in BUILDS:
        dirs = build_root / folder
        images = sorted(dirs.glob("*.bin"))
        app = next(
            (
                p
                for p in images
                if p.stem
                not in ("generated_assets", "ota_data_initial", "bootloader", "partition-table")
            ),
            None,
        )
        if app is None:
            out.append(f"| {label} | not found | | | | |")
            continue
        size = app.stat().st_size
        used = f"{100 * size / slot:.1f} percent" if slot else "unknown"
        free = f"{slot - size:,}" if slot else "unknown"
        room = int(slot - size - FREE_RULE * slot) if slot else 0
        if not slot:
            ok = "unknown"
        elif folder == "build-bench":
            ok = f"{room:,} (developer build: the rule is not applied)"  # the bench image carries serial tools the owner never runs
        else:
            ok = f"{room:,}" if room >= 0 else f"{room:,} (BELOW the rule)"
        out.append(f"| {label} | {size:,} | {slot:,} | {used} | {free} | {ok} |")
    assets = next(iter((build_root / "build-plain").glob("generated_assets.bin")), None)
    if assets is not None and parts.get("assets"):
        a = assets.stat().st_size
        out += [
            "",
            f"Assets image `{assets.name}`: {a:,} bytes of the {parts['assets']:,} byte assets partition ({100 * a / parts['assets']:.1f} percent used, {parts['assets'] - a:,} free).",
        ]
    return out + [""]


def memory_section(log: Path | None) -> list[str]:
    out = ["## Memory (internal RAM, bytes)", ""]
    if log is None or not log.exists():
        return out + [
            "Not measured for this report: pass `--memory-log` with the log `scripts/fw-stress.py` wrote. The gate floors are in `docs/dev/gate-numbers.md`.",
            "",
        ]
    mem = [tuple(int(x) for x in m.groups()) for m in MEM.finditer(log.read_text(errors="replace"))]
    if not mem:
        return out + [
            f"`{log.name}` holds no memory lines: the memory line was off or the unit was not running. Nothing measured.",
            "",
        ]
    steady = mem[len(mem) // 4 :] if len(mem) > 8 else mem  # the first quarter is boot and settling
    rows = [
        ("internal_free, median after settling", statistics.median(m[0] for m in steady)),
        ("internal_free, lowest seen (low water)", min(m[1] for m in mem)),
        ("largest free block, median after settling", statistics.median(m[2] for m in steady)),
        ("largest free block, lowest after settling", min(m[2] for m in steady)),
        ("PSRAM free, lowest", min(m[4] for m in mem)),
    ]
    out += [f"From `{log.name}`: {len(mem)} memory lines.", "", "| Number | Bytes |", "|---|---|"]
    return out + [f"| {name} | {int(v):,} |" for name, v in rows] + [""]


def frame_section() -> list[str]:
    path = ROOT / "docs" / "dev" / "frame-cost-baseline-2026-11-18.md"
    out = ["## Frame cost per screen (virtual unit baseline)", ""]
    if not path.exists():
        return out + [
            "No baseline file: run `python3 scripts/virtual-unit/frame_cost.py --write`.",
            "",
        ]
    rows = [line for line in path.read_text().splitlines() if line.startswith("|")]
    return (
        out
        + rows
        + [
            "",
            f"Source: `{path.relative_to(ROOT)}` (host renderer, dirty-area mode; pixels are exact, milliseconds are an estimate).",
            "",
        ]
    )


def counts_section() -> list[str]:
    tools = json.loads((ROOT / "schema" / "tools.json").read_text())
    order = [
        line
        for line in (ROOT / "firmware" / "patches" / "ORDER").read_text().splitlines()
        if line.strip()
    ]
    ux = sum(1 for line in order if line.startswith("UX"))
    goldens = len(list((ROOT / "host" / "tests" / "golden").rglob("*.png")))
    return [
        "## Counts",
        "",
        f"- Firmware tools: {tools['count']} ({len(tools.get('user_only', []))} user-only).",
        f"- Patches in ORDER: {len(order)} ({ux} display patches named UX).",
        f"- Golden frames in `host/tests/golden`: {goldens}.",
        "",
    ]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("build_root")
    p.add_argument("--name", required=True)
    p.add_argument("--memory-log")
    p.add_argument("--out", default=str(ROOT / "docs" / "dev" / "releases"))
    a = p.parse_args()
    root = Path(a.build_root).expanduser()
    source = root.parent.name if root.name == "firmware" else root.name
    lines = [
        f"# Build report: {a.name}",
        "",
        f"Made by `scripts/release-report.py` from `{source}`. Numbers that were not measured say so.",
        "",
    ]
    lines += (
        image_section(root)
        + memory_section(Path(a.memory_log) if a.memory_log else None)
        + frame_section()
        + counts_section()
    )
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.name}.md").write_text("\n".join(lines))
    print(out / f"{a.name}.md")


if __name__ == "__main__":
    main()
