#!/usr/bin/env python3
"""Asset duplicate report: how many bytes the unit holds twice, and what sharing them through a content-addressed store would save.

Intent: measure before building (docs/plan/installed-set.md, "The content-addressed asset store"). Reads the real assets: the game packs in firmware/games, and, when a
replayed firmware tree is given, the assets partition image (icons, fonts, models), the audio files and the shipped sound files. Counts whole-file duplicates by SHA-256 and, inside
the game packs, duplicate fixed-size records (states, regions, shapes, texts, transitions, actions) across packs.
Usage: python3 scripts/asset-dedupe-report.py [--tree ~/esp/stackchan-rebuild/bNN] [--ref-bytes 4]
Placement: host-side development tool; no firmware change. Upstream: none."""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = (("states", 4), ("regions", 8), ("shapes", 18), ("texts", 96), ("trans", 12), ("actions", 4))
HEADER = 40


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pack_sections(data: bytes):
    """The fixed-size records of one MPGK pack, by section (the layout is maipai_games_core.h)."""
    if data[:4] != b"MPGK":
        return {}
    n_states, n_regions, n_shapes, n_texts = data[6], data[7], data[8], data[9]
    n_trans, n_actions = struct.unpack_from("<HH", data, 10)
    counts = {"states": n_states, "regions": n_regions, "shapes": n_shapes, "texts": n_texts, "trans": n_trans, "actions": n_actions}
    out, off = {}, HEADER
    for name, size in SECTIONS:
        n = counts[name]
        out[name] = [data[off + i * size : off + (i + 1) * size] for i in range(n)]
        off += n * size
    return out


def assets_partition_entries(path: Path):
    """(name, bytes) of the items in generated_assets.bin (the xiaozhi assets layout: count, checksum, length, then 44-byte entries)."""
    d = path.read_bytes()
    n, _cs, _tl = struct.unpack_from("<III", d, 0)
    table = 12
    base = table + n * 44
    items = []
    for i in range(n):
        e = d[table + i * 44 : table + (i + 1) * 44]
        name = e[:32].split(b"\0")[0].decode(errors="replace")
        size, off = struct.unpack_from("<II", e, 32)
        items.append((name, d[base + off : base + off + size]))
    return items


def report_files(label: str, items: list[tuple[str, bytes]], ref_bytes: int, lines: list[str]) -> int:
    by = defaultdict(list)
    for name, data in items:
        by[sha(data)].append((name, len(data)))
    total = sum(len(d) for _, d in items)
    dup_extra = sum(sz * (len(v) - 1) for v in by.values() for sz in [v[0][1]] if len(v) > 1)
    lines.append(f"{label}: {len(items)} files, {total:,} bytes; {sum(1 for v in by.values() if len(v) > 1)} groups of identical files; {dup_extra:,} bytes held more than once")
    for v in by.values():
        if len(v) > 1:
            lines.append(f"  identical x{len(v)} ({v[0][1]:,} bytes each): " + ", ".join(n for n, _ in v))
    return dup_extra - ref_bytes * sum(len(v) - 1 for v in by.values() if len(v) > 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tree", help="a replayed firmware tree (holds main/assets, build-plain/generated_assets.bin)")
    ap.add_argument("--ref-bytes", type=int, default=4, help="bytes a reference to a shared asset costs (default 4: a short id)")
    a = ap.parse_args()
    lines: list[str] = []
    saved_total = 0

    packs = {p.name: p.read_bytes() for p in sorted((ROOT / "firmware" / "games").glob("*.mpk"))}
    saved_total += report_files("game packs (whole files)", list(packs.items()), a.ref_bytes, lines)
    rec_total = rec_saved = 0
    for name, size in SECTIONS:
        seen: dict[bytes, int] = defaultdict(int)
        total = 0
        for data in packs.values():
            for rec in pack_sections(data).get(name, []):
                seen[rec] += 1
                total += len(rec)
        shared = sum(len(r) * (c - 1) for r, c in seen.items() if c > 1)
        refs = sum(c for r, c in seen.items() if c > 1)
        net = shared - a.ref_bytes * refs
        lines.append(f"game pack {name}: {sum(seen.values())} records of {size} bytes ({total:,} bytes); {shared:,} bytes are a copy of a record in another place; net saving after {a.ref_bytes}-byte references: {max(net, 0):,}")
        rec_total += total
        rec_saved += max(net, 0)
    lines.append(f"game packs, record level: {rec_total:,} bytes of records, at most {rec_saved:,} bytes saved by sharing records across the packs ({100 * rec_saved / max(rec_total, 1):.1f} percent of the records)")
    saved_total += rec_saved

    if a.tree:
        tree = Path(a.tree).expanduser()
        gen = tree / "firmware" / "build-plain" / "generated_assets.bin"
        if gen.exists():
            items = assets_partition_entries(gen)
            lines.append(f"assets partition image: {len(items)} items, {sum(len(d) for _, d in items):,} bytes")
            saved_total += report_files("assets partition items", items, a.ref_bytes, lines)
        sounds = [(str(p.relative_to(tree)), p.read_bytes()) for p in sorted(tree.glob("firmware/main/**/*")) if p.suffix in (".ogg", ".wav", ".p3", ".pcm")]
        if sounds:
            saved_total += report_files("sound files in the tree", sounds, a.ref_bytes, lines)
        fonts = [(str(p.relative_to(tree)), p.read_bytes()) for p in sorted(tree.glob("firmware/main/**/*")) if p.suffix == ".c" and "font" in p.name.lower()]
        if fonts:
            saved_total += report_files("font sources in the tree", fonts, a.ref_bytes, lines)
    lines.append(f"TOTAL bytes saved by sharing what the reports above can see: {saved_total:,}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
