#!/usr/bin/env python3
# Intent: write the six <language>-object.json seed files from host/maipai_packages/pantry/objects/objects.json (one table of bits, six name lists).
# Usage: python3 scripts/make-object-seed.py   (run again after the table changes; docs/design/twenty-questions-library.md)
# Placement: repo tool. Upstream: none.
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANTRY = ROOT / "host" / "maipai_packages" / "pantry"
LANGS = ("en", "es", "fr", "de", "pt", "it")


def main() -> int:
    table = json.loads((PANTRY / "objects" / "objects.json").read_text(encoding="utf-8"))
    for lang in LANGS:
        rows = [{"kind": "object", "language": lang, "rating": "kid", "text": o["names"][lang], "answer": o["group"], "extra": o["bits"]} for o in table]
        lines = ",\n".join(" " + json.dumps(r, ensure_ascii=False) for r in rows)
        (PANTRY / "seed" / f"{lang}-object.json").write_text("[\n" + lines + "\n]\n", encoding="utf-8")
    print(f"make-object-seed: {len(table)} objects in {len(LANGS)} languages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
