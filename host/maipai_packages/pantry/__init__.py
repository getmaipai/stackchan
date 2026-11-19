"""Content pantry (docs/design/content-pantry.md): jokes, riddles, trivia and stories the host generates with the owner's model, filters, dedupes and keeps,
and the unit keeps a small shelf of. Off by default; imported only when switched on in robot.toml (`[packages.pantry]`).

The host never imports Home code; with MaiPai Home paired, Home's version takes over and this package steps aside."""

from __future__ import annotations

from pathlib import Path

from maipai_packages.pantry.generator import generate
from maipai_packages.pantry.library import Library
from maipai_packages.pantry.record import Record


class Pantry:
    """The package's one object: the library plus the actions the dashboard and the sync call."""

    def __init__(self, folder: Path, ask=None, *, daily_cap: int = 200, languages: tuple[str, ...] = ("en",), adult_humor: bool = False, seed: bool = True) -> None:
        self.library = Library(folder)
        self.ask, self.daily_cap, self.languages, self.adult_humor = ask, daily_cap, languages, adult_humor
        from maipai_packages.pantry.seed_loader import load_seed

        self.seeded = load_seed(self.library, tuple(languages), adult_humor) if seed else 0  # the built-in set, on first run, with no model

    def view(self, *, kind: str | None = None, language: str | None = None, query: str = "", unit: str | None = None, limit: int = 200) -> dict:
        """What the dashboard shows: counts, the rows (text, answer, heard or not), the last report."""
        heard = self.library.heard(unit) if unit else {}
        refused = self.library.refused()
        from maipai_packages.pantry.seed_loader import built_in_state

        built = built_in_state(self.library, tuple(self.languages))
        built["ids_set"] = set(built["ids"])
        rows, needle = [], query.strip().lower()
        for record in self.library.records(kind, language):
            if needle and needle not in (record.text + " " + record.answer + " " + (record.extra if record.kind == "line" else "")).lower():
                continue
            rows.append({"built_in": record.id_hex in built["ids_set"], "id": record.id_hex, "kind": record.kind, "language": record.language, "rating": record.rating, "text": record.text, "answer": record.answer, "situation": record.extra if record.kind == "line" else "", "heard": record.id_hex in heard})
        situations: dict[str, int] = {}  # offline lines by situation, for the language filter (all languages when none)
        for record in self.library.records("line", language):
            situations[record.extra] = situations.get(record.extra, 0) + 1
        counts: dict[str, int] = {}
        for record in self.library.records():
            counts[f"{record.language}:{record.kind}"] = counts.get(f"{record.language}:{record.kind}", 0) + 1
        return {"ok": True, "enabled": True, "built_in": {"state": built["state"], "records": built["records"], "text": built["text"]}, "counts": counts, "situations": situations, "rows": rows[:limit], "total": len(rows), "refused": len(refused), "report": self.library.last_report(), "calls_today": self.library.calls_today(), "daily_cap": self.daily_cap}

    def delete(self, id_hex: str) -> bool:
        return self.library.delete(id_hex)

    def never_again(self, id_hex: str) -> bool:
        return self.library.never_again(id_hex)

    def refill(self, kind: str, language: str, batches: int = 1) -> dict:
        if self.ask is None:
            return {"added": 0, "stopped": "No model is set. Choose a brain on the Brain page, then press Refill again."}
        return generate(self.library, self.ask, kind, language, batches=batches, daily_cap=self.daily_cap, adult_allowed=self.adult_humor)


__all__ = ["Library", "Pantry", "Record", "generate"]
