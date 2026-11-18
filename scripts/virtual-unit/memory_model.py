"""The memory model of the virtual unit (owner decision 15, 2026-11-18): every screen, overlay, picture face, language pack, task and optional feature has a declared cost
(internal RAM, PSRAM, flash) read from schema/memory-budget.json (the firmware track owns the numbers, see docs/plan/memory-budget-model.md). The model tracks what is loaded
and freed as a scenario runs (create on open, free on close), checks the budget at every change, and gives a leak canary: when everything has closed, the loaded set must be the
baseline again.

The budget (docs/dev/gate-numbers.md): internal free median 40,000, lowest 24,000, largest free internal block 24,000 (median) and 16,000 (lowest). The model keeps a median
estimate (the baseline minus what is loaded and stays: items marked persistent) and a lowest estimate (the baseline minus everything loaded at that moment).

Events come from the rig: VirtualUnit.raw and VirtualUnit.call report to the model (RULES below), and a scenario may declare an open or close itself (u.memory.open(id)). A screen that
only a touch inside the unit opens (the Apps and Games walls) is declared by the scenario; the renderer's real LVGL object count (pcount) is the second witness.
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "schema" / "memory-budget.json"
PAGES = ("clock", "timers", "games", "actions", "frame", "tiles")
SCREEN_IDS = {"sheet": "screen.sheet", "settings": "screen.settings"}


class MemoryBudgetError(AssertionError):
    """The budget would be broken, or something stayed loaded after its screen closed."""


def load_table(path: Path | None = None) -> dict:
    return json.loads((path or TABLE).read_text())


class MemoryModel:
    def __init__(self, u=None, table: dict | None = None, strict: bool = True) -> None:
        self.u = u
        self.table = table or load_table()
        self.items = {i["id"]: i for i in self.table["items"]}
        self.gate = self.table["gate"]
        self.base = self.table["baseline"]
        self.strict = strict
        self.loaded: dict[str, int] = {}   # id -> how many times it is open (a screen opens once; an overlay layer may be open on two layers)
        self.history: list[tuple[int, str, str]] = []   # (fake clock, "open"/"close", id)
        self.violations: list[str] = []
        self.peak = {"internal": 0, "psram": 0, "block": 0}
        self.baseline_set = frozenset(k for k, v in self.items.items() if v.get("in_baseline"))
        self._timers: list[tuple[int, str]] = []   # (fake clock it ends, id): an overlay or the notes that end by themselves
        self._frun_seen = 0

    # ---- the numbers ----------------------------------------------------------------------------------------------------

    def _loaded_items(self):
        return [(self.items[k], n) for k, n in self.loaded.items() if k in self.items and not self.items[k].get("in_baseline")]

    def internal_used(self, persistent_only: bool = False) -> int:
        return sum(i["internal"] * n for i, n in self._loaded_items() if i["persistent"] or not persistent_only)

    def block_used(self, persistent_only: bool = False) -> int:
        return sum(i["largest_block"] * n for i, n in self._loaded_items() if i["persistent"] or not persistent_only)

    def psram_used(self) -> int:
        return sum(i["psram"] * n for i, n in self._loaded_items())

    def numbers(self) -> dict:
        b, g = self.base, self.gate
        out = {
            "internal_free_median": b["internal_free_median"] - self.internal_used(True),
            "internal_free_lowest": b["internal_free_lowest"] - self.internal_used(),
            "largest_block_median": b["largest_block_median"] - self.block_used(True),
            "largest_block_lowest": b["largest_block_lowest"] - self.block_used(),
            "psram_free": b["psram_free"] - self.psram_used(),
        }
        out["margin"] = {
            "internal_free_median": out["internal_free_median"] - g["internal_free_median_min"],
            "internal_free_lowest": out["internal_free_lowest"] - g["internal_free_lowest_min"],
            "largest_block_median": out["largest_block_median"] - g["largest_block_median_min"],
            "largest_block_lowest": out["largest_block_lowest"] - g["largest_block_lowest_min"],
            "psram_free": out["psram_free"] - g["psram_lowest_min"],
        }
        return out

    def broken(self) -> list[str]:
        n = self.numbers()
        return [f"{k} is {n[k]:,}, {-m:,} under its gate" for k, m in n["margin"].items() if m < 0]

    # ---- open and close -------------------------------------------------------------------------------------------------------

    def _check(self, what: str) -> None:
        for line in self.broken():
            msg = f"{what}: {line} with {self.describe()} loaded"
            self.violations.append(msg)
            if self.strict:
                raise MemoryBudgetError(msg + ". Free something that is not needed now, or shrink the feature's cost in schema/memory-budget.json.")
        used = {"internal": self.internal_used(), "psram": self.psram_used(), "block": self.block_used()}
        for k, v in used.items():
            self.peak[k] = max(self.peak[k], v)

    def describe(self) -> str:
        return ", ".join(sorted(k for k in self.loaded if k not in self.baseline_set)) or "nothing"

    def open(self, item_id: str) -> None:
        if item_id not in self.items:
            raise MemoryBudgetError(f"{item_id} has no declared cost in schema/memory-budget.json: add it (internal RAM, PSRAM, flash, when loaded, when freed) before the feature runs")
        if item_id in self.baseline_set:
            return
        self.loaded[item_id] = self.loaded.get(item_id, 0) + 1
        self.history.append((self.u.now_ms if self.u else 0, "open", item_id))
        self._check(f"opening {item_id}")

    def close(self, item_id: str) -> None:
        if item_id in self.loaded:
            self.loaded[item_id] -= 1
            if self.loaded[item_id] <= 0:
                del self.loaded[item_id]
            self.history.append((self.u.now_ms if self.u else 0, "close", item_id))

    def close_all(self, prefix: str) -> None:
        for k in [k for k in self.loaded if k.startswith(prefix)]:
            self.loaded.pop(k)
            self.history.append((self.u.now_ms if self.u else 0, "close", k))

    # ---- the baseline and the leak canary -----------------------------------------------------------------------------------------

    def snapshot(self) -> frozenset:
        """What is loaded now (the face with nothing open is the baseline)."""
        return frozenset(self.loaded)

    def assert_back_to(self, baseline: frozenset, what: str = "after every screen closed") -> None:
        left = sorted(self.loaded.keys() - baseline)
        if left:
            raise MemoryBudgetError(f"{what}, still loaded: {', '.join(left)}. Something was opened and never freed: free it when its screen closes.")

    def totals(self) -> dict:
        """Totals over the declared items for the ledger: sums by kind, what is always on, the declared peak while opening any one screen."""
        always = [i for i in self.items.values() if i["in_baseline"]]
        return {
            "items": len(self.items), "measured": sum(1 for i in self.items.values() if i["status"] in ("measured", "verified")),
            "placeholder": sum(1 for i in self.items.values() if i["status"] in ("placeholder", "to measure", "not built")),
            "always_on_internal": sum(i["internal"] for i in always), "flash": sum(i["flash"] for i in self.items.values()),
            "largest_transient_internal": max((i["internal"] for i in self.items.values() if not i["in_baseline"] and not i["persistent"]), default=0),
        }

    # ---- what the rig reports --------------------------------------------------------------------------------------------------------

    def sweep(self, now: int) -> None:
        """Called after every advance: what ends by itself (a timed overlay, the notes), the first run finishing, the music dance's own end."""
        for t, k in [x for x in self._timers if x[0] <= now]:
            self._timers.remove((t, k))
            self.close(k)
        u = self.u
        if u is not None:
            out = u.output
            if "screen.first_run" in self.loaded and any("firstrun finished" in line for line in out[self._frun_seen:]):
                self.close("screen.first_run")
            self._frun_seen = len(out)
            d = getattr(u, "_dance", None)
            if d is not None:
                if d.stage > 0 and "feature.music_dance" not in self.loaded:
                    self.open("feature.music_dance")
                elif d.stage == 0 and "feature.music_dance" in self.loaded:
                    self.close("feature.music_dance")

    EVENT_LAYER = frozenset({"leaves", "confetti", "fireworks", "hearts", "steam", "balloons", "zzz", "moon", "sparkles"})
    COMBINED = frozenset({"stormy", "rainy", "snowy", "sunny", "windy", "night", "party", "celebrate", "love", "sleeping"})

    def _layers_of(self, name: str) -> list[str]:
        if name in self.COMBINED:
            return ["overlay.layer.back", "overlay.layer.event"]   # a named combination starts one element per layer
        return ["overlay.layer.event" if name in self.EVENT_LAYER else "overlay.layer.back"]

    def on_raw(self, cmd: str) -> None:
        """A renderer command (u.raw): the screens, the first run, overlays and notes."""
        words = cmd.split()
        if not words:
            return
        c = words[0]
        if c == "pshow" and len(words) > 1:
            name = words[1]
            self.close_all("screen.page.")
            for k in ("screen.sheet", "screen.settings"):
                self.close(k) if k in self.loaded else None
            if name in PAGES:
                self.open(f"screen.page.{name}")
            elif name in SCREEN_IDS:
                self.open(SCREEN_IDS[name])
            # "face" closes everything above
        elif c == "frun" and len(words) > 1:
            if words[1] in ("start", "step"):
                if "screen.first_run" not in self.loaded:
                    self.open("screen.first_run")
        elif c == "overlay" and len(words) > 1:
            secs = int(words[3]) if len(words) > 3 and words[3].isdigit() else 0
            for lid in self._layers_of(words[1]):   # a new overlay replaces what the layer showed: the layer is loaded once
                self._timers = [x for x in self._timers if x[1] != lid]
                if lid not in self.loaded:
                    self.open(lid)
                if secs and self.u:
                    self._timers.append((self.u.now_ms + secs * 1000, lid))
        elif c == "ovclear":
            self.close_all("overlay.")
        elif c == "notes":
            n = int(words[1]) if len(words) > 1 and words[1].isdigit() else 0
            if n:
                if "decor.notes" not in self.loaded:
                    self.open("decor.notes")
                    if self.u:
                        self._timers.append((self.u.now_ms + 30000, "decor.notes"))
            else:
                self.close("decor.notes")

    def on_call(self, name: str, args: dict, result: dict) -> None:
        """A tool call (u.call) and its result: what the tool loads or frees."""
        ok = isinstance(result, dict) and result.get("ok") is not False and not result.get("isError")
        if not ok:
            return
        if name == "self.overlay.clear":
            self.close_all("overlay.")
        elif name == "self.face.music_notes" and int(args.get("count", 0)) == 0:
            self.close("decor.notes")
        elif name == "self.facepic.begin":
            self.open("picture.frame") if "picture.frame" not in self.loaded else None
        elif name in ("self.facepic.clear", "self.facepic.commit"):
            self.close("picture.frame")
