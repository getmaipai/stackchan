#!/usr/bin/env python3
"""The feature ledger: every feature and improvement as one row, in two lists (an everyday user's and a maker's), with a status and a percent worked out from evidence in the repository.

  python3 scripts/feature-ledger.py            write docs/dev/feature-ledger.md and docs/dev/feature-ledger.html (the page to read first: searchable, filters, light and dark, phone friendly)
  python3 scripts/feature-ledger.py --check    exit 1 when either file is out of date (run by scripts/check.sh)
  python3 scripts/feature-ledger.py --sync-bench   first copy the bench notes from the notes folder into docs/dev/bench-evidence/ (paths, ports, hashes and ids removed)

Sources: firmware/patches/ORDER and each patch header, docs/user (every table row and bold-led bullet), the games pack, language tables, face and overlay lists, schema/tools.json, scripts/,
host modules and packages, golden frames, bench notes, the plan's Planned and open-decision rows. Rules for status and percent: scripts/ledger_rules.py. Placement: docs tooling. Upstream: none."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_decisions as decisions  # noqa: E402
import ledger_render as render  # noqa: E402
import ledger_rules as rules  # noqa: E402
import ledger_sources as src  # noqa: E402

ROOT = src.ROOT
MD, HTML = ROOT / "docs" / "dev" / "feature-ledger.md", ROOT / "docs" / "dev" / "feature-ledger.html"
NOTES = [Path.home() / "Library/Application Support/Claude/side-session-notes/local_afcae7f7-83f0-4ece-9c2a-5dd3e7ce1ff2"]
EXCLUDED_PAGES = {"compare.md", "troubleshooting.md", "glossary.md", "faq.md", "getting-started.md", "hardware-and-models.md", "local-vs-home.md", "release-notes.md", "which-setup.md", "install-the-host.md", "switch-from-the-factory-firmware.md"}
RULE = ("a patch is built 40, proven virtual 70 when a test or golden frame names it, proven on the unit 100 when a bench note names it; several patches average (partial credit); "
        "a host-only feature is built 40 when its file exists, 70 when a test names it, 100 when a bench note names it; designed 10; idea 0; 'needs person' caps at 89. 'Scrapped' is a status of its own: the owner dropped it on purpose (decision 10 scrapped the baby monitor; the plan's not-included lists add more), so it is listed in a collapsed Scrapped section with the reason and never counted in a percent, a bar or a row total. "
        "The Decisions tab lists each owner decision of 2026-11-18 as built, in progress or not started, from the files that exist (scripts/ledger_decisions.py).")

IMAGE_RULES = [
    (r"control sheet|quick sheet", "docs/images/vu-control-sheet.png"), (r"\bclock\b", "docs/images/vu-clock.png"), (r"lock screen|keypad|passcode", "docs/images/vu-lock-screen.png"),
    (r"timer", "docs/images/vu-timers.png"), (r"games? wall|games page|\bgames\b", "docs/images/vu-games.png"), (r"pairing|pair\b", "docs/images/vu-pairing.png"), (r"update", "docs/images/vu-update.png"),
    (r"first run|first-run|setup language", "docs/images/vu-first-run-language.png"), (r"settings", "docs/images/vu-settings-general.png"), (r"muted|mute", "host/tests/golden/screens/screen-muted.png"),
    (r"camera (?:on|mark)", "host/tests/golden/screens/screen-camera-on.png"), (r"low battery", "host/tests/golden/screens/screen-low-battery.png"), (r"charging", "host/tests/golden/screens/screen-charging.png"),
    (r"listening", "host/tests/golden/screens/screen-listening.png"), (r"subtitle|caption", "host/tests/golden/screens/screen-subtitles.png"), (r"offline", "host/tests/golden/screens/screen-offline.png"),
    (r"status icon", "host/tests/golden/screens/screen-status-normal.png"), (r"apps", "host/tests/golden/screens/screen-apps-wall.png"), (r"wi-fi setup|wifi setup", "host/tests/golden/screens/cover-wifi-setup.png"),
    (r"big eyes|big-eyes", "docs/images/unit-face-big-eyes.png"),
]
GAME_NAMES = {"bopit": "Do It", "dice": "Dice and Coin", "eightball": "Magic 8-Ball", "memory": "Color Memory", "rps": "Rock Paper Scissors", "tictactoe": "Tic-Tac-Toe", "whack": "Whack-a-mole"}
GAME_IMG = {"memory": "docs/images/unit-game-color-memory.png", "bopit": "docs/images/unit-game-do-it.png", "rps": "docs/images/unit-game-rps.png"}
TALK_GAMES = ["20 Questions", "Riddles", "Trivia", "Word chain", "Would you rather", "Bedtime stories"]
STYLES = [("big_eyes", "Big eyes (the default)"), ("eyes_only", "Eyes only (no mouth)"), ("stock", "Stock (the original face)"), ("classic", "Classic (rounder eyes)"), ("minimal", "Minimal (a quiet face)")]
FAMILY_NAMES = {"SF": "Safety, speed and update fixes series", "UX": "Screen and word polish", "UI": "Hands-on test fixes: bigger targets, sheets and settings", "NX": "Quick sheet, lock tile and listening cues", "V": "Face design, speed and the bench verification path",
                "P": "Wi-Fi setup page", "L": "Wake and listening front end", "S": "Core trim of the base firmware", "M": "Mood from care", "TN": "Travel over the private network", "FI": "Memory and banner fixes", "RM": "Wi-Fi roaming",
                "C": "Battery status and shake threshold", "F": "Face configuration", "U": "Face decorators", "GM": "Full height games", "T": "Low battery ladder", "TB": "Listening cues", "FM": "First boot trial and fixes", "R": "Reset on the device",
                "H": "Face bench tools", "Y": "Head moves while idle", "TA": "Preference store", "TC": "Remote token gate", "N": "Banner row and subtitles", "K": "Pack types and cache", "FD": "Face detection experiment", "G": "Game engine",
                "O": "Overlay engine", "LK": "Passcode lock", "MD": "Music dance", "A": "Per pixel light tool", "X": "Faces core and skin", "B": "Base adaptation", "I": "Orientation event", "W": "Screen wake and saved level",
                "Z": "Boot event names the crash", "QS": "Quick settings padding", "MF": "Music feature stack", "ML": "Movement limiter", "num": "Base firmware changes (numbered patches: the rebuilt base)"}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", text.lower()).strip().replace(" ", "-")


def exists(rel: str) -> bool:
    return (ROOT / rel).is_file()


# ---- evidence ---------------------------------------------------------------------------------------------------------

class Evidence:
    def __init__(self) -> None:
        self.patches = src.patches()
        self.tests = src.tests_corpus()
        self.bench = src.bench_corpus()
        self.files = [f for f in src.tracked() if f.startswith(("host/maipai_body/", "host/maipai_packages/", "scripts/", "flasher/", "firmware/"))]
        self.pp = {p["name"]: rules.patch_points(p, self.tests, self.bench) for p in self.patches}
        self.used: set[str] = set()

    def profile(self, key: str) -> dict:
        """Points, the patches that matched, the host files, the bench files for one area profile."""
        prof = rules.PROFILES.get(key, rules.PROFILES["settings"])
        rx = re.compile(prof["patch"])
        mine = [p for p in self.patches if prof["patch"] != "^$" and rx.search((p["name"] + " " + p["intent"]).lower())]
        pts = [self.pp[p["name"]][0] for p in mine]
        host_pts, host_files, host_bench = rules.host_points(prof["host"], self.tests, self.files, prof["bench"], self.bench) if prof["host"] else (0, [], [])
        allpts = pts + ([host_pts] if host_pts else [])
        bench = sorted({f for p in mine for f in self.pp[p["name"]][1]} | set(host_bench))
        for p in mine:
            self.used.add(p["name"])
        return {"percent": round(sum(allpts) / len(allpts)) if allpts else 0, "patches": [p["name"] for p in mine], "host": host_files, "bench": bench, "count": len(mine)}


STOP = set("with that this from have when then they their about into your the and for are not you its it's robot robots unit unitt screen shows shown show make makes made also only each other every more most some what which will would could should there these those them than been being does done using used uses ask asks".split())


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def relevant(ev: "Evidence", profile: str, text: str, limit: int = 4) -> list[dict]:
    """The patches of the area that share rare words with this row, best first. A word counts by how few patches hold it (inverse document frequency); a patch needs a score of 2.5, about one word
    that only a few patches use. Common words (face, voice, screen) never carry a match on their own."""
    import math

    prof = rules.PROFILES.get(profile, rules.PROFILES["settings"])
    if prof["patch"] == "^$":
        return []
    if not hasattr(ev, "_df"):
        ev._ptok = {p["name"]: _tokens(p["name"].replace("-", " ") + " " + p["intent"][:300]) for p in ev.patches}
        df: dict[str, int] = {}
        for toks in ev._ptok.values():
            for t in toks:
                df[t] = df.get(t, 0) + 1
        ev._df = df
    rx = re.compile(prof["patch"])
    want = _tokens(text) - {"needs", "maipai", "home", "runs", "page", "pages", "built", "planned"}
    scored = []
    for p in ev.patches:
        if not rx.search((p["name"] + " " + p["intent"]).lower()):
            continue
        score = sum(math.log(len(ev.patches) / ev._df[t]) for t in want & ev._ptok[p["name"]] if ev._df[t] <= 40)
        if score >= 2.5:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    top = scored[0][0] if scored else 0
    return [p for score, p in scored[:limit] if score >= 0.6 * top]


def row(**kw) -> dict:
    base = {"image": "", "bench": [], "where": [], "doc": "", "rule": "", "tags": [], "source": ""}
    base.update(kw)
    return base


def decision_rows(ev: Evidence, audience: str) -> list[dict]:
    """Rows the 2026-11-18 decisions add: the three ways to get a brain and the encrypted-link default (everyday user), the memory budget table (maker)."""
    first_run_tested = "first_run_core" in ev.tests or "firstrun_core" in ev.tests
    ux12 = exists("firmware/patches/UX12-first-run-skip-brain-question-and-next-steps.patch")
    out: list[dict] = []
    if audience == "user":
        steps = [("eyes", "Dance step 1: the eyes", "Only the eyes look side to side on every beat, about 1.5 s, the head still and the ring dark."),
                 ("nod", "Dance step 2: the nod", "The head nods on the beat, the eyes follow with a small shift, music notes float up, the ring breathes slowly."),
                 ("sway", "Dance step 3: the sway", "The head sways side to side, a small disco ball shows, the ring chases one light a beat."),
                 ("full", "Dance step 4: the full dance", "Pan, tilt and sway together, the disco ball in full, confetti at the peak, the ring swells on the beat."),
                 ("down", "Dance: the way down", "Steps 3, 2 and 1 in reverse as the music fades, then the eyes ahead and the head level.")]
        simulated = exists("scripts/virtual-unit/dance_sim.py") and "test_virtual_unit_dance" in ev.tests.replace("-", "_") or "dance_sim" in ev.tests
        pct = 70 if simulated else 40
        for key, name, desc in steps:
            out.append(row(audience="user", area="Motion and dances", name=name, desc=desc, percent=pct, status=rules.status_for(pct),
                           where=["firmware/patches/MD01-music-dance-ladder-and-beat-dance.patch", "scripts/virtual-unit/dance_sim.py", f"host/tests/golden/screens/dance-{'5-down' if key == 'down' else {'eyes': '1-eyes', 'nod': '2-nod', 'sway': '3-sway', 'full': '4-full'}[key]}.png"],
                           doc="docs/dev/virtual-unit-dance.md", rule="the ladder core and the show run in the virtual unit with a golden frame per step; none of it has run on the unit's screen and ring together", tags=["music dance"]))
        area, doc = "Updates and setup", "docs/design/first-run-flow.md"
        base = 70 if ux12 and first_run_tested else 40 if ux12 else 10
        shown = "the first run shows the choice in six languages and saves the answer; a person has not done it on the unit"
        out.append(row(audience="user", area=area, name="Setup way 1: connect to MaiPai Home", desc="At first run, pick MaiPai Home as the robot's brain. It is the first choice when a hub is already known.", percent=base, status=rules.status_for(base),
                       where=["firmware/patches/UX12-first-run-skip-brain-question-and-next-steps.patch", "host/maipai_body/first_run_name.py"], doc=doc, rule=shown, tags=["decision 12"]))
        out.append(row(audience="user", area=area, name="Setup way 2: use my own servers", desc="At first run, pick your own language model, speech-to-text and text-to-speech servers, and give their addresses on the settings page.", percent=base, status=rules.status_for(base),
                       where=["firmware/patches/UX12-first-run-skip-brain-question-and-next-steps.patch", "host/maipai_body/brain/own_llm.py"], doc=doc, rule=shown, tags=["decision 12"]))
        out.append(row(audience="user", area=area, name="Setup way 3: set one up for me", desc="At first run, pick a minimal local stack: small defaults for all three servers, downloaded not vendored, with a plain progress page and a removal option.", percent=10 if ux12 else 0,
                       status="designed" if ux12 else "idea", where=["docs/plan/first-run-brain-choice.md"], doc=doc, rule="the choice and its saved answer exist (mode 2 in the first run); the installer, the progress page and the removal option are not built", tags=["decision 12"]))
        linked = exists("docs/design/encrypted-link.md")
        out.append(row(audience="user", area="Link and travel", name="Encrypted link on by default", desc="A paired host and robot use the encrypted link unless the owner chooses the plain link and reads a plain warning.", percent=10 if linked else 0, status="designed" if linked else "idea",
                       where=["docs/design/encrypted-link.md", "firmware/patches/SF20-link-key-schedule-core.patch"], doc="docs/design/encrypted-link.md", rule="the encrypted link is built and opt-in; the default waits for the memory budget table (decision 11)", tags=["decision 13"]))
    else:
        sim = exists("scripts/virtual-unit/dance_sim.py")
        out.append(row(audience="maker", area="Virtual playground", name="Music dance simulation", desc="The unit's real ladder core (compiled from patch MD01) and the host's director run on simulated songs, with a golden frame per step.", percent=70 if sim else 10,
                       status=rules.status_for(70 if sim else 10), where=["scripts/virtual-unit/dance_sim.py", "scripts/virtual-unit/dance_core.py", "scripts/virtual-unit/dance/ladder_sim.c"], doc="docs/dev/virtual-unit-dance.md", rule="files exist and test_virtual_unit_dance.py runs it"))
        table = exists("docs/dev/memory-budget.md")
        tested = "memory-budget" in ev.tests or "memory_budget" in ev.tests
        pct = 70 if table and tested else 40 if table else 10
        out.append(row(audience="maker", area="Build and gate", name="Memory budget table", desc="One table of what fits in internal RAM at once, what is on by default and what excludes what, measured by firmware before more optional features land.", percent=pct, status=rules.status_for(pct),
                       where=["docs/dev/memory-budget.md"] if table else ["docs/design/firmware-memory.md"], doc="docs/dev/memory-budget.md" if table else "docs/design/firmware-memory.md",
                       rule="the table exists" + (" and a test reads it" if tested else "") if table else "decided (decision 11); the table is firmware's and is not written yet", tags=["decision 11"]))
    return out


# ---- user rows ---------------------------------------------------------------------------------------------------------------

def user_rows(ev: Evidence) -> list[dict]:
    rows: list[dict] = []
    doc_text = {p.name: p.read_text(errors="ignore") for p in (ROOT / "docs" / "user").glob("*.md")}

    def doc_for(name: str) -> str:
        key = name.lower()
        for page, text in doc_text.items():
            if key in text.lower() and page not in EXCLUDED_PAGES:
                return f"docs/user/{page}"
        return ""

    def image_for(text: str, fallback: str = "") -> str:
        for rx, rel in IMAGE_RULES:
            if re.search(rx, text.lower()) and exists(rel):
                return rel
        return fallback if fallback and exists(fallback) else ""

    def add(profile: str, name: str, desc: str, area: str, *, image: str = "", doc: str = "", tags=None, percent=None, status=None, where=None, rule="", bench=None, person=False, designed=False):
        e = ev.profile(profile)
        rel = relevant(ev, profile, name + " " + desc)
        if rel:
            pts = [ev.pp[p["name"]][0] for p in rel]
            own = round(sum(pts) / len(pts))
            own_bench = sorted({f for p in rel for f in ev.pp[p["name"]][1]})
            basis = f"average of the {len(rel)} patch(es) that share words with this row: " + ", ".join(p["id"] for p in rel)
        else:
            own, own_bench = min(e["percent"], 70), e["bench"][:2]
            basis = "no patch shares words with this row; the evidence is the area's (" + (f"{e['count']} patch(es), {len(e['host'])} host file(s)" if e["count"] or e["host"] else "no code found") + ")"
        pct = own if percent is None else percent
        img = image or image_for(name + " " + desc)
        if img.startswith("docs/images/unit-") and not person and percent is None:
            pct, basis = 100, "a screenshot taken on the flashed robot exists (" + img.rsplit("/", 1)[-1] + ")"
        if designed:
            pct, status = 10, "designed"
        if person:
            pct = min(pct, 89)
        st = status or rules.status_for(pct, person=person)
        rows.append(row(audience="user", area=area, name=name, desc=desc, percent=pct, status=st, image=img, doc=doc or doc_for(name), tags=tags or [],
                        where=where or ([p["name"] for p in rel[:3]] + e["host"][:2]), bench=bench if bench is not None else own_bench[:3], rule=rule or basis))

    # games
    for g in src.games():
        name = GAME_NAMES.get(g["id"], g["id"])
        add("games", f"Game: {name}", f"Play {name} on the robot's screen.", "Games", image=GAME_IMG.get(g["id"], "docs/images/vu-games.png"), where=[g["file"], "firmware/patches (G01 to G03, GM01 to GM06)"], doc=doc_for(name) or "docs/user/games-and-pet.md",
            bench=[f for f in ev.bench if "game" in ev.bench[f].lower()][:2])
    for t in TALK_GAMES:
        add("games", f"Talk game: {t}", f"Play {t} by talking with your model.", "Games", where=["host/maipai_body/bodies/stackchan/games.py"], doc="docs/user/games-and-pet.md", percent=40, status="built", rule="built, not flashed and not tested with a live model (the feature page says so)")
    # languages
    status_path = ROOT / "docs" / "dev" / "translation-review" / "status.json"
    stats = json.loads(status_path.read_text()) if status_path.is_file() else {}
    for code, label in src.NAMES.items():
        if code == "en":
            add("languages", "Language: English", "The robot's screens, settings page and messages in English (the source language).", "Languages", percent=100, status="proven on unit", where=["host/maipai_body/i18n.py"], doc="docs/user/languages.md", image="docs/images/vu-first-run-language.png", rule="the source language: every screen and message is written in it and was seen on the robot")
            continue
        s = stats.get(code, {})
        rows_n, missing, drafts = s.get("rows", 0), s.get("missing", 0), s.get("machine_draft", 0)
        golden = exists(f"host/tests/golden/screens/first-run-1-{code}.png")
        comp = round(100 * (rows_n - missing) / rows_n) if rows_n else 0
        add("languages", f"Language: {label}", f"Screens, settings page and messages in {label}: {comp} percent translated, every line a machine draft until a native speaker reviews it ({drafts} draft rows, {missing} still English or missing).", "Languages",
            image=f"host/tests/golden/screens/first-run-1-{code}.png" if golden else "", percent=70 if golden else 40, status="proven virtual" if golden else "built", where=["host/maipai_body/i18n.py", "host/maipai_body/i18n_fill/", f"docs/dev/translation-review/{code}.csv"],
            doc="docs/user/languages.md", bench=[f for f in ev.bench if re.search(r"accent|first-run language", ev.bench[f], re.I)][:1] if code in ("es", "fr", "pt") else [],
            rule=f"first-run screens drawn by the robot's own code in {label} are golden frames (virtual); translation is machine draft, reviewed by nobody yet", person=True)
    # moods
    for m in src.moods():
        g = f"host/tests/golden/face/face-{'doubtful' if m == 'doubt' else m}.png"
        add("face", f"Mood: {m}", f"The face shows {m}.", "Faces and moods", image=g if exists(g) else "", percent=70 if exists(g) else 40, rule="a golden frame of the real face drawing code" if exists(g) else "built; no golden frame yet", doc="docs/user/face-and-look.md",
            where=["scripts/fw-face-render", "firmware/patches (F, X, V families)"])
    for key, label in STYLES:
        sheet = f"docs/dev/ledger-assets/faces-{key}.png"
        add("face", f"Face style: {label}", f"Pick the {label.split(' (')[0].lower()} face style; one tap on the settings page, no reflash.", "Faces and moods", image=sheet if exists(sheet) else "", doc="docs/user/face-and-look.md",
            percent=70, status="proven virtual", rule="drawn by the robot's own face code in the virtual unit (contact sheet of every mood)" + ("" if exists(sheet) else "; sheet not made yet"), where=["firmware/patches/X01-look-core-and-skin.patch", "firmware/patches/V10-face-design-shapes.patch"])
    add("face", "Anime big-eyes face with chunky mouth", "The default face: big anime-style eyes with a chunky mouth that follows the voice.", "Faces and moods", image="docs/images/unit-face-big-eyes.png", where=["firmware/patches/V10-face-design-shapes.patch", "firmware/patches/V12-chunky-mouth-on-anime-eyes.patch"],
        percent=100, status="proven on unit", bench=[f for f in ev.bench if "mouth" in ev.bench[f].lower()][:2], rule="a real photo-grade screenshot from the flashed robot exists (unit-face-big-eyes.png) and the bench saw the mouth open and close", doc="docs/user/face-and-look.md")
    for c in src.face_colors():
        add("face", f"Face color: {c}", f"Tint the face {c}.", "Faces and moods", image="docs/images/face-colors.svg", doc="docs/user/face-and-look.md", percent=70, status="proven virtual", rule="the virtual unit's face config accepts and draws it", where=["scripts/virtual-unit/tools/face2.py"])
    elems, combos = src.overlays()
    for o in dict.fromkeys(elems):
        add("face", f"Overlay: {o}", f"A {o} effect drawn over the face.", "Overlays", doc="docs/user/face-and-look.md", rule="built and drawn by the overlay engine; nobody has seen it on a robot", person=True, where=["firmware/patches/O01-overlay-engine-bigger-shapes-and-combined.patch", "host/maipai_body/overlays.py"])
    for o in dict.fromkeys(combos):
        add("face", f"Combined overlay: {o}", f"The named combination of effects: {o}.", "Overlays", doc="docs/user/face-and-look.md", rule="built; combinations are named lists of single overlays", person=True, where=["host/maipai_body/reply_tags.py"])
    for n, label in (("picture", "Picture only"), ("overlay", "Picture with eyes and mouth drawn on top"), ("sequence", "A short run of frames")):
        img = f"docs/images/picture-faces-{n}.png"
        add("face", f"Picture face: {label}", f"Your own picture as a look: {label.lower()}.", "Faces and moods", image=img, doc="docs/user/face-and-look.md", percent=70, status="proven virtual", rule="drawn by the real face code in the virtual unit", where=["firmware/patches/V23-face-pictures-for-eyes-and-mouth.patch"])
    # dances
    for d in src.dances():
        add("motion", f"Dance: {d.replace('_', ' ')}", f"The robot does the {d.replace('_', ' ')} dance.", "Motion and dances", doc="docs/user/moves-and-moods.md", where=["host/maipai_body/dance.py", "host/maipai_body/bodies/stackchan/companion.py"], bench=[f for f in ev.bench if "dance" in ev.bench[f].lower()][:2])
    # docs rows
    seen = {r["name"].lower().replace("game: ", "") for r in rows}
    for d in src.user_page_rows():
        if d["page"] in EXCLUDED_PAGES:
            continue
        name = d["name"].strip(" .:")
        if not name or name.lower() in seen or len(name) > 90 or name.lower() in {"feature", "key", "light", "tone", "say", "you do", "tap", "battery", "your", "what"}:
            continue
        seen.add(name.lower())
        if "_" in name or (len(name.split()) == 1 and len(name) < 8 and d["page"] in ("settings.md", "home-tools.md", "with-maipai-home.md") and d["kind"] == "table"):
            continue   # a setting key or a one-word column cell, not a feature
        if len(name.split()) == 1:
            name = f"{d['title']}: {name}"
        label = {"Say": "Voice command: ", "You do": "Reaction: ", "Tap": "Tap: ", "Light": "Light: ", "Tone": "Tone: ", "Battery": "Battery: "}.get(d["header"], "")
        text = d["raw"] + " " + d["desc"]
        profile = rules.pick_profile(d["page"], d["section"], name, d["desc"])
        designed = bool(rules.DESIGN_RX.search(" ".join(d["tags"]) + " " + d["raw"][:200])) and "Planned" in d["tags"]
        person = bool(rules.PERSON_RX.search(text))
        built_only = bool(rules.BUILT_NOT_FLASHED_RX.search(text))
        area = {"voice": "Voice", "lights": "Lights and sounds", "face": "Faces and moods", "motion": "Motion and dances", "timers": "Time: timers, alarms, clock", "games": "Games", "music": "Music and dance", "screens": "Screens and pages",
                "lock": "Safety and privacy", "privacy": "Safety and privacy", "parentview": "Parent view", "languages": "Languages", "camera": "Camera, remote, monitor", "remote": "Camera, remote, monitor", "monitor": "Camera, remote, monitor",
                "notes": "Optional packages", "ha": "Optional packages", "coding": "Optional packages", "charpacks": "Optional packages", "wakemaker": "Voice", "update": "Updates and setup", "flasher": "Updates and setup",
                "travel": "Link and travel", "link": "Link and travel", "setup": "Updates and setup", "battery": "Battery and power", "home": "With MaiPai Home", "settings": "Settings page", "tools": "Virtual robot"}.get(profile, "Settings page")
        add(profile, label + name, d["desc"] or d["title"], area, doc=f"docs/user/{d['page']}#{slug(d['section'])}" if d["section"] else f"docs/user/{d['page']}", tags=d["tags"], designed=designed, person=person and not designed,
            percent=40 if built_only else None, status="built" if built_only and not person else None, rule=("the page marks it Planned: designed, not built" if designed else "built, not flashed" if built_only else ""))
    for p in src.planned_rows():
        name = re.sub(r"\s+(Planned|Built, not flashed)$", "", p["name"]).strip()
        if name.lower() in seen or not name:
            continue
        seen.add(name.lower())
        rows.append(row(audience="user", area="Wanted, not started", name=name, desc=p["desc"], status="designed" if "Planned" in p["name"] else "idea", percent=10 if "Planned" in p["name"] else 0, where=[p["source"]], rule="listed in the plan; nothing built", doc=""))
    rows += decision_rows(ev, "user")
    return rows


# ---- maker rows ------------------------------------------------------------------------------------------------------------------

CURATED = [
    ("Updates and release", "Signed over-the-air update with rollback", "The unit fetches a signed header and image from its paired host, checks signature, build number, length and hash, and goes back to the old slot if the new one does not start.", ["firmware/patches/SF25-signed-update-header-and-build-number.patch", "scripts/release.sh", "host/maipai_body/bodies/stackchan/firmware/update_header.py"], ["SF25", "SF37"], ["bench-b9"], "docs/dev/update-checks.md"),
    ("Updates and release", "Anti-rollback build floor", "An update must beat the build number kept in flash and the one compiled into the image, so a USB flash keeps the floor.", ["firmware/patches/SF37-compiled-build-floor.patch"], ["muh_floor"], [], "docs/dev/update-checks.md"),
    ("Updates and release", "Signed release script", "Turns one finished build into a signed release folder (manifest, images, signatures, header, key scan).", ["scripts/release.sh"], ["release.sh"], [], "docs/dev/update-checks.md"),
    ("Updates and release", "Web flasher page", "A static page that checks the signed list and every file before it writes the robot over USB.", ["flasher/flasher-core.js", "flasher/flasher.js"], ["flasher-core"], [], "docs/user/web-flasher.md"),
    ("Updates and release", "Release report", "One page per build: image sizes per slot, memory numbers, frame cost.", ["scripts/release-report.py"], ["release-report"], ["bench-window"], ""),
    ("Link and security", "Encrypted link and six-digit key exchange", "The unit and host pair by a key exchange and six digits; the link is encrypted with a key only they hold.", ["host/maipai_body/bodies/stackchan/xiaozhi/link_exchange.py", "firmware/patches/SF20-link-key-schedule-core.patch"], ["key_exchange", "SF20"], [], "docs/plan/link-key-exchange.md"),
    ("Link and security", "Hostile peer scenarios", "A peer with no credentials and one with a stolen token try malformed frames, floods and replays against the real host.", ["scripts/virtual-unit/e2e_hostile.py"], ["hostile_paired_peer"], [], "docs/dev/fuzzing-and-hostile-peer.md"),
    ("Link and security", "Sanitizer fuzz of the unit's parsers", "Thirteen parsers of the firmware cores built with address and undefined behavior sanitizers and fed mutated input.", ["scripts/fuzz-cores.sh", "scripts/fuzz/core_fuzz.c"], ["fuzz-cores"], [], "docs/dev/fuzzing-and-hostile-peer.md"),
    ("Brain and tools", "Own-model brain", "The host answers with any OpenAI-compatible chat, speech to text and text to speech address you name.", ["host/maipai_body/brain/own_llm.py"], ["own_llm"], [], "docs/user/which-setup.md"),
    ("Brain and tools", "Tool protocol and schema", "Every firmware tool the host can call, as a schema generated from the patches and checked for drift.", ["schema/tools.json", "scripts/virtual-unit/tools_extract.py"], ["tools_extract", "tools.json"], [], ""),
    ("Brain and tools", "Spec drift check", "The vendored shared spec is a snapshot and the check fails when it differs from its pinned tag.", ["scripts/spec-drift-check.sh"], ["spec-drift", "spec_pin"], [], ""),
    ("Virtual playground", "Headless virtual unit", "The robot's real screen code, tools and body running on a computer with a fake clock.", ["scripts/virtual-unit/vunit.py"], ["VirtualUnit"], [], "docs/user/try-the-virtual-robot.md"),
    ("Virtual playground", "3D rigged model and physics view", "A browser view with the robot's model, a physics engine, an IMU and a head that follows its commands.", ["scripts/virtual-unit/view3d.js", "scripts/virtual-unit/physics/physics.js"], ["test_virtual_unit_physics"], ["bench-window"], "docs/dev/virtual-unit-3d.md"),
    ("Virtual playground", "End to end on the virtual unit", "The real host in a clean venv talks to the virtual unit through scripted model and speech servers.", ["scripts/virtual-unit/e2e.py"], ["e2e.py"], [], "docs/dev/e2e-virtual-unit.md"),
    ("Virtual playground", "Head recording and fit", "Record head steps on the unit, fit the servo model and compare it with the simulated head.", ["scripts/fw-head-record.py", "scripts/virtual-unit/physics/calibrate.py"], ["fw-head-record"], ["bench-window"], "docs/dev/head-recording.md"),
    ("Virtual playground", "Golden frames", "Reference pictures of every screen drawn by the real screen code, compared on every test run.", ["host/tests/golden"], ["golden"], [], ""),
    ("Build and gate", "Rebuild from the repo and the patch series", "Rebuild the firmware tree from the pinned upstream bases and every patch in ORDER.", ["scripts/fw-rebuild.sh", "scripts/patch-replay.sh"], ["patch-replay", "fw-rebuild"], ["bench-"], ""),
    ("Build and gate", "Bench tools", "Serial tool path, stress run, voice bench and the memory line for a unit on the cable.", ["scripts/fw-serial.py", "scripts/fw-stress.py", "scripts/fw-voice-bench.py"], ["fw-stress"], ["bench-"], ""),
    ("Build and gate", "Memory gate and off-cost script", "Memory floors every image must keep, and a proof that an optional feature switched off costs nothing.", ["scripts/off-cost.sh", "scripts/fw-stress.py"], ["off-cost", "memory"], ["bench-"], "docs/design/firmware-memory.md"),
    ("Build and gate", "Suite in four processes", "The whole host suite runs in about four minutes by sharding test files across pytest processes.", ["scripts/test-sharded.py", "scripts/test-all.sh"], ["test-sharded"], [], "docs/dev/test-speed.md"),
    ("Build and gate", "Soak and flake hunt", "A 500 turn leak canary and a loop that runs the end to end under CPU load.", ["scripts/virtual-unit/e2e_extra.py", "scripts/e2e-flake-hunt.sh"], ["leak_verdict"], [], "docs/dev/e2e-virtual-unit.md"),
    ("Build and gate", "Cross-review status table", "Every review bug as a test with an owner, and a table of what is fixed.", ["scripts/review-status.py", "docs/dev/cross-review-status.md"], ["cross_review"], [], "docs/dev/cross-review-status.md"),
    ("Packages and extension", "Host packages API", "Optional local packages (memory notes, Home Assistant, coding companion, wake word maker) loaded only when switched on.", ["host/maipai_packages"], ["maipai_packages"], [], "docs/dev/overview.md"),
    ("Packages and extension", "Hooks for coding agents", "A hook a coding agent runs to tell the robot its state.", ["host/maipai_packages/coding_companion/hook.py"], ["hook_send", "coding_companion"], [], "docs/user/coding-companion.md"),
    ("Packages and extension", "Character pack format", "A pack that gives the robot a persona, a voice style and word reactions.", ["host/maipai_body/i18n_character.py"], ["character"], [], "docs/user/character-packs.md"),
    ("Packages and extension", "Wake word maker scripts", "Record clips on the settings page, train a small model, check it and install it.", ["host/maipai_packages/wake_word_maker"], ["wake_word_maker"], [], "docs/user/wake-word-maker.md"),
    ("Docs and translation", "Translator review pack", "One CSV per language with an importer that checks length and glyphs; reviewed words win.", ["scripts/translation-pack.py", "docs/dev/translation-review"], ["translation_pack"], [], "docs/dev/translation-review/README.md"),
    ("Docs and translation", "Docs claims and reading level checks", "Scripts that test claims in the docs against the code and report the reading grade of each page.", ["scripts/docs-claims-check.py", "scripts/docs-grade.py"], ["docs-claims"], [], ""),
]


def maker_rows(ev: Evidence) -> list[dict]:
    rows: list[dict] = []

    def pts(files, test_kw, bench_kw):
        built = any(exists(f) or (ROOT / f).is_dir() for f in files)
        tested = any(k in ev.tests for k in test_kw)
        benched = [n for n in ev.bench if any(k in n or k in ev.bench[n] for k in bench_kw)] if bench_kw else []
        pct = (100 if benched and tested else 70 if tested else 40) if built else 10
        return pct, benched[:3], built, tested

    for area, name, desc, files, tk, bk, doc in CURATED:
        pct, benched, built, tested = pts(files, tk, bk)
        rows.append(row(audience="maker", area=area, name=name, desc=desc, percent=pct, status=rules.status_for(pct), where=files, bench=benched, doc=doc, rule="files exist" + (", a test names it" if tested else "") + (", a bench note names it" if benched else "")))
    # patch families
    groups: dict[str, list[dict]] = {}
    for p in ev.patches:
        groups.setdefault(p["family"], []).append(p)
    for fam, ps in sorted(groups.items(), key=lambda x: -len(x[1])):
        points = [ev.pp[p["name"]][0] for p in ps]
        pct = round(sum(points) / len(points))
        bench = sorted({f for p in ps for f in ev.pp[p["name"]][1]})
        rows.append(row(audience="maker", area="Firmware patch series", name=FAMILY_NAMES.get(fam, f"Patch family {fam}"), desc=f"{len(ps)} patch(es): " + "; ".join(src.sentence(p["intent"] or p["name"], 70) for p in ps[:3]) + ("..." if len(ps) > 3 else ""),
                        percent=pct, status=rules.status_for(pct), where=[p["name"] for p in ps][:6], bench=bench[:3], doc="", rule=f"average of {len(ps)} patch(es): built 40, a test names it 70, a bench note names it 100"))
    # tools by area
    vu_tools = "".join(p.read_text(errors="ignore") for p in (ROOT / "scripts" / "virtual-unit" / "tools").glob("*.py"))
    for area, names in sorted(src.tools_by_area().items()):
        sim = sum(1 for n in names if f'"{n}"' in vu_tools)
        benched = [f for f in ev.bench if f"self.{area}." in ev.bench[f]]
        pct = 100 if benched and sim else 70 if sim else 40
        rows.append(row(audience="maker", area="Tool protocol", name=f"Tools: self.{area}.* ({len(names)})", desc=", ".join(n.split(".", 2)[2] for n in names[:8]) + ("..." if len(names) > 8 else ""), percent=pct, status=rules.status_for(pct),
                        where=["schema/tools.json"], bench=benched[:3], doc="", rule=f"{sim} of {len(names)} simulated by the virtual unit; " + ("a bench note names the area" if benched else "no bench note names the area")))
    # scripts
    for s in src.scripts_list():
        name = s["name"]
        tested = name in ev.tests or name.rsplit(".", 1)[0] in ev.tests
        benched = [f for f in ev.bench if name in ev.bench[f]]
        pct = 100 if benched and tested else 70 if tested else 40
        rows.append(row(audience="maker", area="Scripts and tools", name=f"Script: {name}", desc=s["intent"] or "A repository script.", percent=pct, status=rules.status_for(pct), where=[f"scripts/{name}"], bench=benched[:2], rule="file exists" + (", a test names it" if tested else "") + (", a bench note names it" if benched else "")))
    # host modules
    for f in ev.files:
        if not (f.startswith("host/maipai_body/") and f.endswith(".py") and f.count("/") <= 4) or f.endswith(("__init__.py", "_test.py")) or "/i18n" in f:
            continue
        stem = f.rsplit("/", 1)[-1][:-3]
        text = (ROOT / f).read_text(errors="ignore")
        m = re.search(r'^\s*(?:#.*\n)*\s*"""(.+?)"""', text, re.S)
        desc = src.sentence(m.group(1)) if m else "A host module."
        tested = re.search(r"\b" + re.escape(stem) + r"\b", ev.tests) is not None
        benched = [n for n in ev.bench if re.search(r"\b" + re.escape(stem) + r"\b", ev.bench[n])]
        pct = 100 if benched and tested else 70 if tested else 40
        rows.append(row(audience="maker", area="Host modules", name=f"Host: {stem}", desc=desc, percent=pct, status=rules.status_for(pct), where=[f], bench=benched[:2], rule="file exists" + (", a test names it" if tested else "") + (", a bench note names it" if benched else "")))
    for pk in src.packages():
        rows.append(row(audience="maker", area="Packages and extension", name=f"Package: {pk['name']}", desc=pk["doc"], percent=70 if f"maipai_packages.{pk['name']}" in ev.tests or pk["name"] in ev.tests else 40, status="proven virtual" if pk["name"] in ev.tests else "built", where=[f"host/maipai_packages/{pk['name']}"], rule="package exists; a test names it"))
    for sc in src.e2e_scenarios():
        rows.append(row(audience="maker", area="Virtual playground", name=f"End to end scenario: {sc.replace('_', ' ')}", desc=f"A scenario of the end to end run: {sc.replace('_', ' ')}.", percent=70, status="proven virtual", where=["scripts/virtual-unit/e2e.py"], doc="docs/dev/e2e-virtual-unit.md", rule="runs against the real host and the virtual unit"))
    rows += decision_rows(ev, "maker")
    return rows


# ---- bench evidence -----------------------------------------------------------------------------------------------------------

def sanitize(text: str) -> str:
    text = re.sub(r"(?:/Users|/private|/var|/tmp|~)/[^\s)`|,;]+", "<path>", text)
    text = re.sub(r"/dev/cu\.[A-Za-z0-9]+", "<serial port>", text)
    text = re.sub(r"\busbmodem\d+", "<serial port>", text)
    text = re.sub(r"\b[0-9a-f]{16,64}\b", "<hash>", text)
    text = re.sub(r"\bpid[ =]\s*\d+", "pid <n>", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<address>", text)
    text = re.sub(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b", "<device id>", text)
    return text


def sync_bench() -> int:
    notes = next((n for n in NOTES if n.is_dir()), None)
    if notes is None:
        print("feature-ledger: the notes folder is not on this computer; the committed copies in docs/dev/bench-evidence are used.")
        return 0
    out = ROOT / "docs" / "dev" / "bench-evidence"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(notes.glob("bench-*.md")):
        (out / p.name).write_text("<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->\n" + sanitize(p.read_text(errors="ignore")))
        n += 1
    print(f"feature-ledger: copied {n} bench note(s) into docs/dev/bench-evidence")
    return 0


# ---- build and write ---------------------------------------------------------------------------------------------------------------

OVERRIDES = [  # (name regex, status, percent, bench note substring, rule): what the bench proved by name, said in the bench notes
    (r"^Passcode lock|^Lock", "needs person", 85, "lock", "the lockout after wrong codes and across a restart was checked on the robot; a person on the keypad has not"),
    (r"Mute, camera off|Reaction: tap|^Tap: ", "needs person", 85, "privacy", "tap on and hold off were checked on the robot with a test touch; a real finger has not"),
    (r"Wi-Fi setup", "proven on unit", 100, "Wi-Fi setup", "the setup screen was seen on the robot after a Wi-Fi wipe"),
    (r"First run|first-run", "needs person", 85, "first-run", "the flow showed once after Wi-Fi on the robot with test touches; a person has not done it"),
    (r"find me|Find me", "proven on unit", 100, "find-me volume", "the find chirp and the volume restore were measured on the robot"),
    (r"Movement limits", "needs person", 85, "reach", "the USB limit and the dance stop were measured; carried and flipped need a person"),
]


def build() -> tuple[list[dict], dict]:
    ev = Evidence()
    rows = user_rows(ev) + maker_rows(ev)
    for r in rows:
        if r["audience"] != "user":
            continue
        for rx, status, pct, key, rule in OVERRIDES:
            if re.search(rx, r["name"]):
                benched = [f for f in ev.bench if key.lower() in ev.bench[f].lower()]
                if benched:
                    r["status"], r["percent"], r["bench"], r["rule"] = status, pct, benched[:3], rule
                break
    for r in rows:   # decision 10: every baby monitor row is scrapped, kept for the record, and counted nowhere
        if r["audience"] == "user" and (decisions.BABY_PAGE in r["doc"] or "baby" in r["name"].lower()):
            r["status"], r["percent"], r["bench"], r["rule"] = "scrapped", 0, [], decisions.BABY_REASON
    for name, desc in (("Baby monitor", "Watching or listening to a baby from the robot, with a baby label on the screen and lullabies."), ("Monitoring a child or a person who needs care", "Any promise that the robot watches over a child or a person who needs care.")):
        if not any(r["name"] == name for r in rows):   # the docs pages are gone; the record of the decision stays
            rows.append(row(audience="user", area="Scrapped and dropped", name=name, desc=desc, status="scrapped", percent=0, where=["docs/design/decisions.md (decision 10)"], rule=decisions.BABY_REASON))
    have = {re.sub(r"[^a-z]", "", r["name"].lower()) for r in rows}
    for d in decisions.dropped_items():   # the plan's own dropped and not-included lists
        if re.sub(r"[^a-z]", "", d["name"].lower()) not in have:
            rows.append(row(audience="user", area="Scrapped and dropped", name=d["name"], desc="Not built and not planned.", status="scrapped", percent=0, where=[d["source"]], rule=d["reason"]))
    for i, r in enumerate(rows):
        r["id"] = f"{'U' if r['audience'] == 'user' else 'M'}{i + 1:04d}"
    named = {w for r in rows for w in r["where"]}
    unmapped = [{"name": p["name"], "intent": src.sentence(p["intent"] or "(no intent line)", 140)} for p in ev.patches if p["name"] not in ev.used and p["name"] not in named and not any(p["name"] in w for w in named)]
    return rows, {"rule": RULE, "unmapped": unmapped, "decisions": decisions.decisions(), "baby_reason": decisions.BABY_REASON}


def main(argv: list[str]) -> int:
    if "--sync-bench" in argv:
        sync_bench()
    rows, meta = build()
    md, html = render.markdown(rows, meta), render.page(rows, meta)
    if "--check" in argv:
        stale = [p.name for p, text in ((MD, md), (HTML, html)) if not p.is_file() or p.read_text() != text]
        if stale:
            print(f"feature-ledger: {', '.join(stale)} out of date. Run python3 scripts/feature-ledger.py.")
            return 1
        print("feature-ledger: ok")
        return 0
    MD.write_text(md)
    HTML.write_text(html)
    c = render.counts(rows)
    print(f"wrote {MD.relative_to(ROOT)} and {HTML.relative_to(ROOT)}: {sum(c['user'].values())} user rows, {sum(c['maker'].values())} maker rows, {len(meta['unmapped'])} unmapped patches")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
