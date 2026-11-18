#!/usr/bin/env python3
"""List the host strings that are still English in fr, de, pt and it, and write translation chunks for lane briefs.
Usage: i18n-gaps.py [--chunks OUTDIR] [--size 60]   prints the counts; with --chunks writes OUTDIR/<lang>_<n>.json {lang, strings:{key: english}}.
A string counts as a gap when the language's text equals English (or is missing) and the English has at least two letters in a row of words.
Placement: host-side development tool. Upstream: none."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))
from maipai_body import i18n  # noqa: E402

LANGS = ("fr", "de", "pt", "it")


def gaps(lang):
    en = i18n.CATALOG["en"]
    out = {}
    for key, text in en.items():
        if i18n.CATALOG[lang].get(key, text) == text and len(re.findall(r"[A-Za-z]{3,}", text)) >= 1 and not re.fullmatch(r"[\w.+-]*(Wi-Fi|OK|URL|API)[\w .+-]*", text):
            out[key] = text
    return out


def main():
    size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 60
    out = Path(sys.argv[sys.argv.index("--chunks") + 1]) if "--chunks" in sys.argv else None
    total = 0
    for lang in LANGS:
        g = gaps(lang)
        total += len(g)
        items = list(g.items())
        n = 0
        for i in range(0, len(items), size):
            n += 1
            if out:
                out.mkdir(parents=True, exist_ok=True)
                (out / f"{lang}_{n}.json").write_text(json.dumps({"lang": lang, "strings": dict(items[i : i + size])}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{lang}: {len(g)} gaps, {n} chunks")
    print(f"total {total}")


if __name__ == "__main__":
    main()
