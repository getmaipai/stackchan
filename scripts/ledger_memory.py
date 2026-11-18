"""The Memory column of the feature ledger (owner decision 15): each feature row that loads something names the declared cost of it (internal RAM, PSRAM, flash, when it is loaded) from
schema/memory-budget.json, and the ledger header totals what the table declares. A row matched to no item says "not declared": a feature that loads something and has no row in the table is a gap.
Placement: docs tooling. Upstream: none."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "schema" / "memory-budget.json"

# row name (regular expression, case insensitive) -> the ids of the memory items it loads
MAP: list[tuple[str, list[str]]] = [
    (r"^overlay[:\s]|overlays?\b.*(rain|snow|disco|confetti)|^Weather overlay", ["overlay.layer.back"]),
    (r"confetti|fireworks|hearts|balloons|leaves|steam|zzz", ["overlay.layer.event"]),
    (r"music notes|notes beside", ["decor.notes"]),
    (r"^dance step|^dance: the way down|music dance|beat dance", ["feature.music_dance"]),
    (r"first[- ]run", ["screen.first_run"]),
    (r"control sheet|quick settings", ["screen.sheet"]),
    (r"^settings screen|settings page on the unit|^settings$", ["screen.settings"]),
    (r"\btimers?\b.*page|^timers$", ["screen.page.timers"]),
    (r"^clock$|clock page|show the clock", ["screen.page.clock"]),
    (r"quick actions", ["screen.page.actions"]),
    (r"^game: |^games$|game pack", ["screen.game", "task.game_pack"]),
    (r"picture faces?|^pictures$|picture frame", ["picture.frame"]),
    (r"subtitle|caption", ["feature.subtitles"]),
    (r"encrypted link|link key|^pair", ["feature.link_tls"]),
    (r"camera stream|avatar", ["feature.avatar_stream"]),
    (r"echo|barge", ["feature.echo_canceller"]),
    (r"custom wake word|wake word maker", ["feature.wake_word_custom"]),
    (r"passcode lock|^lock\b|keypad", ["screen.keypad"]),
    (r"banner", ["screen.banner"]),
    (r"^servo|head moves", ["feature.servo_task"]),
]
LANG = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Portuguese": "pt", "Italian": "it"}


def _table() -> dict:
    return json.loads(TABLE.read_text()) if TABLE.is_file() else {"items": [], "gate": {}, "baseline": {}}


def attach(rows: list[dict]) -> None:
    t = _table()
    items = {i["id"]: i for i in t["items"]}
    for r in rows:
        ids: list[str] = []
        m = re.match(r"^Language: (\w+)", r["name"])
        if m and LANG.get(m.group(1)):
            ids = [f"language.{LANG[m.group(1)]}"]
        else:
            for rx, got in MAP:
                if re.search(rx, r["name"], re.I):
                    ids = got
                    break
        ids = [i for i in ids if i in items]
        if not ids:
            r["memory"] = None
            continue
        picked = [items[i] for i in ids]
        r["memory"] = {
            "internal": sum(i["internal"] for i in picked), "psram": sum(i["psram"] for i in picked), "flash": sum(i["flash"] for i in picked),
            "loaded_when": "; ".join(i["loaded_when"] for i in picked), "items": ids,
            "status": "placeholder" if any(i["status"] in ("placeholder", "to measure", "not built") for i in picked) else "measured" if all(i["status"] in ("measured", "verified") for i in picked) else "estimate",
        }


def totals(rows: list[dict]) -> dict:
    t = _table()
    items = t["items"]
    declared = [r for r in rows if r.get("memory")]
    gate, base = t.get("gate", {}), t.get("baseline", {})
    return {
        "items": len(items), "measured": sum(1 for i in items if i["status"] in ("measured", "verified")), "estimate": sum(1 for i in items if i["status"] == "estimate"),
        "placeholder": sum(1 for i in items if i["status"] in ("placeholder", "to measure", "not built")),
        "rows_declared": len([r for r in declared if r["status"] != "scrapped"]), "rows_total": len([r for r in rows if r["status"] != "scrapped"]),
        "always_on_internal": sum(i["internal"] for i in items if i["in_baseline"]), "flash_declared": sum(i["flash"] for i in items),
        "headroom_lowest": base.get("internal_free_lowest", 0) - gate.get("internal_free_lowest_min", 0), "headroom_median": base.get("internal_free_median", 0) - gate.get("internal_free_median_min", 0),
        "block_margin": base.get("largest_block_median", 0) - gate.get("largest_block_median_min", 0),
        "biggest_transient": max(((i["internal"], i["name"]) for i in items if not i["in_baseline"] and not i["persistent"]), default=(0, "")),
        "persistent_internal": sum(i["internal"] for i in items if i["persistent"] and not i["in_baseline"]),
    }
