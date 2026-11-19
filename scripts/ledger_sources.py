"""Miners for the feature ledger (scripts/feature-ledger.py): everything here only reads the repository and returns plain data.

Patches (firmware/patches/ORDER and each patch's header), the evidence corpora (tests, bench notes, docs), the user pages (tables and bold-led bullets), and the granular lists
that live in code or data (games, languages, moods, face styles, overlays, dances, tools by area, scripts). No rule about status lives here: see ledger_rules.py.
Placement: docs tooling. Upstream: none."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "docs" / "dev" / "bench-evidence"


# ---- patches -----------------------------------------------------------------------------------------------

def patches() -> list[dict]:
    out = []
    for line in (ROOT / "firmware" / "patches" / "ORDER").read_text().splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        path = ROOT / "firmware" / "patches" / name
        head = {"intent": "", "placement": "", "check": ""}
        if path.is_file():
            for raw in path.read_text(errors="ignore").splitlines()[:12]:
                for key in head:
                    if raw.lower().startswith(f"# {key}:"):
                        head[key] = raw.split(":", 1)[1].strip()
        m = re.match(r"^([A-Za-z]*\d+[a-z]?)", name)
        out.append({"name": name, "id": m.group(1) if m else name, "family": re.match(r"^[A-Za-z]+", name).group(0) if re.match(r"^[A-Za-z]+", name) else "num", **head})
    return out


def sentence(text: str, limit: int = 230) -> str:
    text = " ".join(text.split())
    cut = re.split(r"(?<=[.;])\s", text, maxsplit=1)[0]
    return (cut if len(cut) <= limit else cut[: limit - 1].rstrip() + "...")


# ---- evidence corpora ---------------------------------------------------------------------------------------

def _read_all(paths, suffixes) -> str:
    parts = []
    for p in paths:
        if p.is_file() and p.suffix in suffixes:
            try:
                parts.append(p.read_text(errors="ignore"))
            except OSError:
                pass
    return "\n".join(parts)


def tests_corpus() -> str:
    return _read_all((ROOT / "host" / "tests").rglob("*"), {".py", ".c", ".cc", ".mjs", ".json", ".h"}) + "\n" + _read_all((ROOT / "flasher" / "test").rglob("*"), {".mjs"})


def bench_corpus() -> dict[str, str]:
    return {p.name: p.read_text(errors="ignore") for p in sorted(BENCH.glob("*.md"))} if BENCH.is_dir() else {}


def docs_text(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(errors="ignore") if p.is_file() else ""


def tracked() -> list[str]:
    return subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()


# ---- the user pages --------------------------------------------------------------------------------------------

TAGS = (("Needs MaiPai Home", "home"), ("Planned", "planned"), ("Built, not flashed", "built-not-flashed"))


def _clean(text: str) -> str:
    text = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return " ".join(text.replace("**", "").replace("`", "").split())


def _tags(text: str) -> list[str]:
    return [tag for label, tag in TAGS if label in text]


def user_page_rows() -> list[dict]:
    """Every table row and every bold-led bullet of docs/user/*.md as a feature row, with the page and section it came from."""
    rows = []
    for page in sorted((ROOT / "docs" / "user").glob("*.md")):
        section, header = "", []
        lines = page.read_text(errors="ignore").splitlines()
        title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else page.stem
        for raw in lines:
            if raw.startswith("## "):
                section, header = raw[3:].strip(), []
                continue
            if raw.startswith("|"):
                cells = [c.strip() for c in raw.strip().strip("|").split("|")]
                if cells and set("".join(cells)) <= set("-: "):
                    continue
                if not header:
                    header = cells
                    continue
                first = _clean(cells[0]) or (_clean(cells[1]) if len(cells) > 1 else "")
                rest = " - ".join(_clean(c) for c in cells[1:] if _clean(c))
                if first:
                    rows.append({"page": page.name, "title": title, "section": section, "kind": "table", "header": header[0] if header else "", "name": first, "desc": rest, "tags": _tags(raw), "raw": raw})
            else:
                m = re.match(r"^\s*[-*] \*\*([^*]+?)\.?\*\*\.?\s*(.*)$", raw)
                if m:
                    rows.append({"page": page.name, "title": title, "section": section, "kind": "bullet", "header": "", "name": _clean(m.group(1)), "desc": _clean(m.group(2)), "tags": _tags(raw), "raw": raw})
    return rows


# ---- granular lists that live in code or data -------------------------------------------------------------------------

def games() -> list[dict]:
    out = []
    for f in sorted((ROOT / "firmware" / "games").glob("*.json")):
        d = json.loads(f.read_text())
        title = d.get("title", f.stem)
        text = title if isinstance(title, str) else (title.get("en") if isinstance(title, dict) else str(title))
        out.append({"id": d.get("id", f.stem), "title": text, "file": f"firmware/games/{f.name}"})
    return out


NAMES = {"es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese", "it": "Italian", "en": "English"}
NAMES.update({"nl": "Dutch", "pl": "Polish", "tr": "Turkish", "sv": "Swedish", "da": "Danish", "nb": "Norwegian (Bokmal)", "cs": "Czech"})   # tier 1, machine drafts (host/maipai_body/i18n_tier1.py)


def moods() -> list[str]:
    text = (ROOT / "scripts" / "virtual-unit" / "vunit.py").read_text()
    m = re.search(r"EMOTIONS = \{([^}]*)\}", text)
    return sorted(re.findall(r'"(\w+)"', m.group(1))) if m else []


def overlays() -> tuple[list[str], list[str]]:
    text = (ROOT / "host" / "maipai_body" / "reply_tags.py").read_text()

    def block(name: str) -> list[str]:
        m = re.search(name + r"[^=]*= \((.*?)\)\n", text, re.S)
        return re.findall(r'"([\w-]+)"', m.group(1)) if m else []

    return block("ELEMENT_OVERLAYS"), block("COMBINED_OVERLAYS")


def dances() -> list[str]:
    text = (ROOT / "host" / "maipai_body" / "bodies" / "stackchan" / "companion.py").read_text()
    return sorted(set(re.findall(r'"(\w+)"', "".join(re.findall(r"(?:BUILTIN|EXTRA)_DANCES = frozenset\(\{(.*?)\}\)", text, re.S)))))


def face_colors() -> list[str]:
    text = (ROOT / "scripts" / "virtual-unit" / "tools" / "face2.py").read_text()
    m = re.search(r'"colo' + r'ur": \{([^}]*)\}', text)   # the tool's own key is spelled the firmware's way
    return [c for c in re.findall(r'"(\w+)"', m.group(1)) if c != "none"] if m else []


def tools_by_area() -> dict[str, list[str]]:
    data = json.loads((ROOT / "schema" / "tools.json").read_text())["tools"]
    out: dict[str, list[str]] = {}
    for item in data:
        name = item["name"] if isinstance(item, dict) else item
        out.setdefault(name.split(".")[1], []).append(name)
    return out


def scripts_list() -> list[dict]:
    out = []
    for p in sorted((ROOT / "scripts").glob("*")):
        if not p.is_file() or p.suffix not in (".py", ".sh"):
            continue
        text = p.read_text(errors="ignore")
        intent = ""
        m = re.search(r"^# Intent: (.+)$", text, re.M) or re.search(r'^(?:"""|\'\'\')(?:Intent: )?([^\n]+)', text, re.M)
        if m:
            intent = sentence(m.group(1), 200)
        out.append({"name": p.name, "intent": intent})
    return out


def packages() -> list[dict]:
    out = []
    for p in sorted((ROOT / "host" / "maipai_packages").iterdir()):
        if p.is_dir() and not p.name.startswith("_"):
            doc = (p / "__init__.py").read_text(errors="ignore") if (p / "__init__.py").is_file() else ""
            m = re.match(r'^(?:#.*\n)*\s*"""(.+?)"""', doc, re.S)
            out.append({"name": p.name, "doc": sentence(m.group(1)) if m else ""})
    return out


def e2e_scenarios() -> list[str]:
    text = (ROOT / "scripts" / "virtual-unit" / "e2e.py").read_text()
    m = re.search(r"^SCENARIOS = \{(.*?)\}\n", text, re.S | re.M)
    names = re.findall(r'"(\w+)":', m.group(1)) if m else []
    names += re.findall(r'"(\w+)": \w+', (ROOT / "scripts" / "virtual-unit" / "e2e_extra.py").read_text().split("EXTRA = {")[-1]) if "EXTRA = {" in (ROOT / "scripts" / "virtual-unit" / "e2e_extra.py").read_text() else []
    names += re.findall(r'"(\w+)": \w+', (ROOT / "scripts" / "virtual-unit" / "e2e_hostile.py").read_text().split("EXTRA_HOSTILE = {")[-1])
    return list(dict.fromkeys(names))


def planned_rows() -> list[dict]:
    """What the plan wants and nobody has started: the Planned and Not included sections of the feature page (open decisions are not features and are not listed)."""
    rows = []
    text = docs_text("docs/user/features.md")
    in_planned = False
    for raw in text.splitlines():
        if raw.startswith("## "):
            in_planned = raw.strip() in ("## Planned", "## Not included")
            continue
        if in_planned and raw.startswith("|") and not set(raw) <= set("|-: "):
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            if len(cells) >= 2 and "Feature" not in cells[0]:
                rows.append({"name": _clean(cells[0]), "desc": _clean(cells[1]), "source": "docs/user/features.md (Planned)"})
    return rows
