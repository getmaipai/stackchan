#!/usr/bin/env python3
"""Audits every touch screen against the physical standard (screen_standard.py) with the unit's own geometry: the renderer lists every clickable object (its click area, extended area included)
and every label (its font's line height) after the screen's scenario has run. A target is a leaf (a clickable object that holds no other clickable object); the full screen and scroll
containers are not targets. Failures: a target under 48 px a side, two targets closer than 8 px or overlapping, a label under the 16 px font, a target outside the panel that no scroll
container carries (clipped). Warnings: a target under 56 px (primary size), a label that is the 16 px font (secondary text only).
Writes docs/dev/screens/annotated/<screen>.png (every target drawn: green ok, orange under 56, red failing; labels blue, orange for the 16 px font, red under it; a 10 mm scale bar at the
bottom left), docs/dev/screen-audit.json and docs/dev/screen-audit.md. host/tests/test_screen_audit.py holds the failures to docs/design/screen-audit-baseline.json: they may only shrink.
Usage: screen_audit.py [--write] [screen ...]. Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import screen_standard as std  # noqa: E402
import thumbnails as tn  # noqa: E402  (the PNG reader and writer)
import vunit  # noqa: E402

_spec = importlib.util.spec_from_file_location("scenarios", HERE / "scenarios.py")
scen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scen)

OUT = ROOT / "docs" / "dev" / "screens" / "annotated"
BASELINE = ROOT / "docs" / "design" / "screen-audit-baseline.json"
SKIP = ("cover-", "first-run-started", "screen-eyes-only", "screen-muted", "screen-listening", "screen-offline", "screen-status-normal", "screen-charging", "screen-low-battery", "screen-wifi-flag",
        "host-away", "dance-", "es-sheet", "lock-", "more-version-end", "es-more-version-end", "screen-settings-look-switches", "screen-settings-general-more")   # the scrolled copies hold the same targets as the unscrolled ones   # faces, covers, banners: not touch screens


def screens() -> list[str]:
    return [n for n in scen.SCREENS if n not in scen.FILMSTRIPS and not n.startswith(SKIP) and "-" in n and not any(n.endswith(f"-{l}") for l in ("en", "es", "fr", "de", "pt", "it"))]   # the unsuffixed first-run frames and the es- pages; the language variants are audited by name when asked


def parse(lines: list[str]):
    targets, texts = [], []
    for l in lines:
        w = l.split()
        if w and w[0] == "ptarget":
            a = list(map(int, w[1:5]))
            targets.append({"x1": a[0], "y1": a[1], "x2": a[2], "y2": a[3], "own": list(map(int, w[6:10])), "scroll": int(w[11])})
        elif w and w[0] == "ptext":
            texts.append({"x1": int(w[1]), "y1": int(w[2]), "x2": int(w[3]), "y2": int(w[4]), "line": int(w[5]), "scroll": int(w[7]), "text": " ".join(w[8:]).replace("~", " ")})
    return targets, texts


def leaves(targets: list[dict]) -> list[dict]:
    def inside(a, b):   # a lies inside b and is not the same box
        return a is not b and a["x1"] >= b["x1"] and a["y1"] >= b["y1"] and a["x2"] <= b["x2"] and a["y2"] <= b["y2"] and (a["x2"] - a["x1"], a["y2"] - a["y1"]) != (b["x2"] - b["x1"], b["y2"] - b["y1"])
    out = []
    for t in targets:
        w, h = t["x2"] - t["x1"] + 1, t["y2"] - t["y1"] + 1
        if w >= 300 and h >= 220:
            continue
        if any(inside(o, t) for o in targets):
            continue
        out.append(t)
    seen, uniq = set(), []
    for t in out:
        k = (t["x1"], t["y1"], t["x2"], t["y2"])
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq


def judge(targets: list[dict], texts: list[dict]) -> dict:
    lv = leaves(targets)
    fails, warns = [], []
    for t in lv:
        w, h = t["x2"] - t["x1"] + 1, t["y2"] - t["y1"] + 1
        t["w"], t["h"] = w, h
        t["status"] = "ok"
        if min(w, h) < std.SECONDARY_PX:
            t["status"] = "fail"
            fails.append(f"target {w}x{h} px ({std.mm(w):.1f} x {std.mm(h):.1f} mm) at {t['x1']},{t['y1']}: under {std.SECONDARY_PX} px")
        elif min(w, h) < std.PRIMARY_PX:
            t["status"] = "warn"
            warns.append(f"target {w}x{h} px at {t['x1']},{t['y1']}: under the {std.PRIMARY_PX} px primary size")
        if not t["scroll"] and (t["x2"] < 0 or t["y2"] < 0 or t["x1"] > 319 or t["y1"] > 239 or t["x2"] > 319 + 4 or t["y2"] > 239 + 4):
            t["status"] = "fail"
            fails.append(f"target at {t['x1']},{t['y1']}-{t['x2']},{t['y2']} runs off the panel and no scroll carries it")
    for i, a in enumerate(lv):
        for b in lv[i + 1 :]:
            ox, oy = min(a["x2"], b["x2"]) - max(a["x1"], b["x1"]) + 1, min(a["y2"], b["y2"]) - max(a["y1"], b["y1"]) + 1
            if ox > 0 and oy > 0:
                a["status"] = b["status"] = "fail"
                fails.append(f"targets at {a['x1']},{a['y1']} and {b['x1']},{b['y1']} overlap")
            else:
                gx = -ox if oy > 0 else 10**6   # horizontal gap when they share rows
                gy = -oy if ox > 0 else 10**6
                gap = min(gx, gy)
                if 0 <= gap < std.GAP_PX:
                    a["status"] = b["status"] = "fail"
                    fails.append(f"targets at {a['x1']},{a['y1']} and {b['x1']},{b['y1']} are {gap} px apart (under {std.GAP_PX})")
    for t in texts:
        if t["line"] and t["line"] < std.LINE_SECONDARY:
            t["status"] = "fail"
            fails.append(f"text '{t['text'][:24]}' is under the 16 px font (line {t['line']})")
        elif t["line"] and t["line"] < std.LINE_BODY:
            t["status"] = "warn"
            warns.append(f"text '{t['text'][:24]}' is the 16 px font: secondary text only")
        else:
            t["status"] = "ok"
    return {"targets": lv, "texts": texts, "fails": fails, "warnings": warns}


def draw(png: bytes, res: dict) -> bytes:
    import numpy as np

    w, h, rows = tn._rows(png)
    img = np.frombuffer(b"".join(rows), dtype=np.uint8).reshape(h, w, 3).copy()
    col = {"ok": (60, 220, 90), "warn": (255, 170, 40), "fail": (255, 50, 50)}

    def box(x1, y1, x2, y2, c, thick=1):
        x1, x2, y1, y2 = max(0, x1), min(w - 1, x2), max(0, y1), min(h - 1, y2)
        if x2 < x1 or y2 < y1:
            return
        for t in range(thick):
            img[y1 + t : y1 + t + 1, x1 : x2 + 1] = c
            img[max(y1, y2 - t) : max(y1, y2 - t) + 1, x1 : x2 + 1] = c
            img[y1 : y2 + 1, x1 + t : x1 + t + 1] = c
            img[y1 : y2 + 1, max(x1, x2 - t) : max(x1, x2 - t) + 1] = c

    for t in res["texts"]:
        box(t["x1"], t["y1"], t["x2"], t["y2"], {"ok": (90, 150, 255), "warn": (255, 170, 40), "fail": (255, 50, 50)}[t["status"]])
    for t in res["targets"]:
        box(t["x1"], t["y1"], t["x2"], t["y2"], col[t["status"]], 2)
    bar = std.px(10)   # a 10 mm scale bar with ticks every millimeter, bottom left
    y = h - 6
    img[y : y + 2, 8 : 8 + bar] = (255, 255, 255)
    for k in range(0, 11):
        x = 8 + round(k * std.PX_PER_MM)
        img[y - (5 if k in (0, 10) else 3) : y, x : x + 1] = (255, 255, 255)
    return tn._png(w, h, [bytes(r) for r in img.reshape(h, w * 3)])


def audit(name: str, steps=None) -> tuple[dict, bytes]:
    with vunit.VirtualUnit(profile="screens") as u:
        scen.run(u, steps if steps is not None else scen.SCREENS[name])
        u.raw("ptargets")
        u._sync()
        targets, texts = parse(u.output)
        u.output.clear()
        png = u.snapshot()
    res = judge(targets, texts)
    return res, draw(png, res)


def main(argv: list[str]) -> int:
    names = [a for a in argv if not a.startswith("--")] or screens()
    write = "--write" in argv
    report = {}
    OUT.mkdir(parents=True, exist_ok=True)
    for n in names:
        res, ann = audit(n)
        report[n] = {"targets": len(res["targets"]), "fails": len(res["fails"]), "warnings": len(res["warnings"]), "failures": res["fails"][:12]}
        if write:
            (OUT / f"{n}.png").write_bytes(ann)
    if write:
        (ROOT / "docs" / "dev" / "screen-audit.json").write_text(json.dumps(report, indent=1) + "\n")
        lines = ["# Screen audit against the physical standard", "", f"Made by `scripts/virtual-unit/screen_audit.py --write`. Panel {std.PANEL_W_MM:.1f} mm wide, {std.PX_PER_MM:.2f} px a millimeter (assumed from the 2 inch diagonal). Targets under {std.SECONDARY_PX} px, targets closer than {std.GAP_PX} px, labels under the 16 px font and clipped targets fail; targets under {std.PRIMARY_PX} px and 16 px labels warn. Annotated frames: `docs/dev/screens/annotated/`.", "",
                 "| Screen | Targets | Failures | Warnings | First failures |", "|---|---:|---:|---:|---|"]
        for n, r in sorted(report.items()):
            lines.append(f"| {n} | {r['targets']} | {r['fails']} | {r['warnings']} | {'; '.join(r['failures'][:2]).replace('|', '/')} |")
        total = sum(r["fails"] for r in report.values())
        lines += ["", f"Total failures: {total} on {len(report)} screens."]
        (ROOT / "docs" / "dev" / "screen-audit.md").write_text("\n".join(lines) + "\n")
        BASELINE.write_text(json.dumps({n: {"fails": r["fails"]} for n, r in sorted(report.items())}, indent=1) + "\n") if not BASELINE.exists() else None
    print(f"screen audit: {len(names)} screens, {sum(r['fails'] for r in report.values())} failures, {sum(r['warnings'] for r in report.values())} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
