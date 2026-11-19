#!/usr/bin/env python3
# Intent: write the six <language>-object.json seed files from host/maipai_packages/pantry/objects/ (core.json: group, bits and the English name; es.json, fr.json, de.json, pt.json, it.json: the names in the same order).
# Usage: python3 scripts/make-object-seed.py   (run again after the table changes; docs/design/twenty-questions-library.md)
# Placement: repo tool. Upstream: none.
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANTRY = ROOT / "host" / "maipai_packages" / "pantry"
LANGS = ("en", "es", "fr", "de", "pt", "it")


def main() -> int:
    folder = PANTRY / "objects"
    core = json.loads((folder / "core.json").read_text(encoding="utf-8"))
    names = {"en": [o["en"] for o in core]}
    for lang in LANGS[1:]:
        names[lang] = json.loads((folder / f"{lang}.json").read_text(encoding="utf-8"))
        if len(names[lang]) != len(core):
            print(f"make-object-seed: {lang}.json has {len(names[lang])} names for {len(core)} objects. Make the lists the same length.", file=sys.stderr)
            return 1
    for lang in LANGS:
        rows = [{"kind": "object", "language": lang, "rating": "kid", "text": names[lang][i], "answer": o["group"], "extra": o["bits"]} for i, o in enumerate(core)]
        lines = ",\n".join(" " + json.dumps(r, ensure_ascii=False) for r in rows)
        (PANTRY / "seed" / f"{lang}-object.json").write_text("[\n" + lines + "\n]\n", encoding="utf-8")
    print(f"make-object-seed: {len(core)} objects in {len(LANGS)} languages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
