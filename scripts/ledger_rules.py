"""The rules of the feature ledger: how a row's status and percent are worked out from evidence the repository holds. Nothing is typed as a verdict except in OVERRIDES.

Evidence per firmware patch (firmware/patches/ORDER): built = it is in the series (40 points); proven virtual = a test or golden frame in host/tests names it (70); proven on the unit =
a bench note in docs/dev/bench-evidence names it (100). A feature with several patches takes the average of its patches ("partial credit"). A host-only feature (a module, a script) takes
built 40 when the file exists, proven virtual 70 when a test names it, proven on the unit 100 when a bench note names it. Designed (a design note or a Planned row, nothing built) is 10, an idea 0.
Status comes from the percent: under 20 designed, 20 to 54 built, 55 to 89 proven virtual, 90 and up proven on unit; a row the docs say no person has judged yet is "needs person" (its percent is
capped at 89 because the last step is a person's). Placement: docs tooling. Upstream: none."""
from __future__ import annotations

import re

POINTS = {"idea": 0, "designed": 10, "built": 40, "proven virtual": 70, "proven on unit": 100}
STATUSES = ["idea", "designed", "built", "proven virtual", "proven on unit", "needs person"]

# area profile -> a regular expression over patch name and intent (lower case); host_modules are file name parts that count as the host half; bench_words are words a bench note must hold
PROFILES: dict[str, dict] = {
    "voice": {"patch": r"wake|listen|voice|speech|barge|echo|stop-word|follow-?up|filler|offline-phrase|talk-over|aec|listening|speak", "host": ["turn.py", "stt", "tts", "barge", "voice", "wake"], "bench": ["voice", "wake", "reply", "listening"]},
    "lights": {"patch": r"led|light|ring|neon|chime|tone|sound|sfx", "host": ["light_service", "light_wiring", "sounds"], "bench": ["light", "tone", "chirp", "sound"]},
    "face": {"patch": r"face|eye|mouth|blink|gaze|expression|mood|anime|style|decor|overlay|caption|look|picface|picture|fx|skin|clock|banner|subtitle", "host": ["face", "expression", "overlay", "gaze", "captions", "idle_faces"], "bench": ["face", "mouth", "eyes", "overlay"]},
    "motion": {"patch": r"head|servo|motion|limiter|shake|tilt|pickup|orient|touch|pet|dance|move|carried|idle", "host": ["head_", "motion_limit", "head_gate", "orientation", "dance"], "bench": ["head", "servo", "dance", "reach"]},
    "timers": {"patch": r"timer|alarm|chime|clock|time|hourly|quiet", "host": ["timers", "alarm"], "bench": ["timer", "alarm"]},
    "games": {"patch": r"game|gm0|tictac|memory|whack|rps|dice|eightball|bopit", "host": ["games.py"], "bench": ["game"]},
    "music": {"patch": r"music|beat|dance", "host": ["music_dance", "music_identify"], "bench": ["music", "beat"]},
    "screens": {"patch": r"page|sheet|apps|swipe|settings|screen|quick|wall|tab|ui0|ui1|nx0", "host": ["swipe_pages", "unit_polish"], "bench": ["screen", "page", "sheet"]},
    "lock": {"patch": r"lock|passcode|keypad", "host": ["lock_voice", "i18n_lock"], "bench": ["lock", "passcode"]},
    "privacy": {"patch": r"privacy|mute|camera-?off|quiet|vision|mic", "host": ["privacy"], "bench": ["mute", "privacy", "camera"]},
    "parentview": {"patch": r"parent|family", "host": ["settings_ui_family", "i18n_family"], "bench": []},
    "languages": {"patch": r"lang|accent|words|pack", "host": ["i18n", "language_packs"], "bench": ["language", "accent"]},
    "camera": {"patch": r"camera|photo|snap|face-?detect|facedet|fd0|vision", "host": ["vision", "camera", "ambient_vision"], "bench": ["camera", "photo"]},
    "remote": {"patch": r"remote|find|token|session", "host": ["remote", "unit_remote", "remote_trust"], "bench": ["remote", "find"]},
    "monitor": {"patch": r"monitor|watch|alert|sentry", "host": ["presence_watch"], "bench": []},
    "notes": {"patch": r"^$", "host": ["memory_notes"], "bench": []},
    "ha": {"patch": r"^$", "host": ["home_assistant"], "bench": []},
    "coding": {"patch": r"^$", "host": ["coding_companion"], "bench": []},
    "charpacks": {"patch": r"persona|character|pack", "host": ["character", "i18n_character"], "bench": []},
    "wakemaker": {"patch": r"wake-?word-?maker|wakeword", "host": ["wake_word_maker"], "bench": []},
    "update": {"patch": r"update|ota|rollback|signed|first-boot|trial|build-?floor|header", "host": ["updater", "firmware_update", "update_header", "flash_manifest"], "bench": ["update", "rollback", "signed"]},
    "flasher": {"patch": r"^$", "host": [], "bench": []},
    "travel": {"patch": r"travel|tailnet|private-network|roam|wifi|wi-fi|network", "host": ["tailnet", "roam", "wifi"], "bench": ["wi-fi", "wifi", "network"]},
    "link": {"patch": r"link|psk|pair|key-|encrypt|tls|exchange", "host": ["link_exchange", "pairing", "link_security", "tls"], "bench": ["pair", "link"]},
    "setup": {"patch": r"first-?run|portal|setup|reset|boot|wifi-setup", "host": ["settings_page", "first_run"], "bench": ["first-run", "first run", "setup"]},
    "battery": {"patch": r"battery|charg|power|sleep|low", "host": ["power_idle"], "bench": ["battery"]},
    "home": {"patch": r"^$", "host": ["home", "hub"], "bench": []},
    "settings": {"patch": r"prefs|settings|tab|info", "host": ["settings_page", "settings_server", "settings_ui"], "bench": ["settings"]},
    "tools": {"patch": r"tool|mcp|serial|bench", "host": [], "bench": ["bench"]},
}

# page -> profile (the default for a row from that page)
PAGE_PROFILE = {
    "voice.md": "voice", "lights-and-sounds.md": "lights", "face-and-look.md": "face", "moves-and-moods.md": "motion", "timers-and-alarms.md": "timers", "games-and-pet.md": "games",
    "music-and-dance.md": "music", "swipe-pages.md": "screens", "lock.md": "lock", "mute-and-camera-off.md": "privacy", "privacy.md": "privacy", "parent-view.md": "parentview",
    "languages.md": "languages", "camera.md": "camera", "find-and-remote.md": "remote", "watch-and-alerts.md": "monitor", "watch-the-room.md": "monitor", "memory-notes.md": "notes",
    "home-assistant.md": "ha", "coding-companion.md": "coding", "character-packs.md": "charpacks", "wake-word-maker.md": "wakemaker", "updates.md": "update", "web-flasher.md": "flasher",
    "use-it-anywhere.md": "travel", "security.md": "link", "home-tools.md": "home", "with-maipai-home.md": "home", "settings.md": "settings", "bench-listening.md": "voice",
    "install-the-host.md": "setup", "switch-from-the-factory-firmware.md": "setup", "no-stealth.md": "camera", "try-the-virtual-robot.md": "tools",
}
SECTION_PROFILE = {"Talk": "voice", "Look": "face", "Keep time": "timers", "React": "motion", "Privacy": "privacy", "Connect": "link", "Set up and keep safe": "setup", "Camera, remote control and MaiPai Home": "camera",
                   "Optional extras (all off until you turn them on)": "notes"}
KEYWORD_PROFILE = [
    (r"battery|charg", "battery"), (r"timer|alarm|clock|chime|quiet hours", "timers"), (r"lock|passcode", "lock"), (r"mute|camera off|full quiet|privacy", "privacy"), (r"game|tic-tac|memory|whack|8-ball|dice|coin|rock paper", "games"),
    (r"dance|music|song", "music"), (r"wi-fi roam|private network|travel", "travel"), (r"update|rollback|signed", "update"), (r"language|spanish|french|german|portuguese|italian|translation", "languages"),
    (r"face|eye|mood|overlay|expression|caption|picture", "face"), (r"light|tone|sound|chirp", "lights"), (r"wake word|stop|barge|talk over|voice|speech|listen", "voice"), (r"head|pet|shake|pick|tilt|move|servo", "motion"),
    (r"page|sheet|swipe|apps|settings screen|control sheet", "screens"), (r"camera|photo|snapshot|face detect", "camera"), (r"find me|remote", "remote"), (r"home assistant", "ha"), (r"coding", "coding"), (r"notes|remember", "notes"),
]


def pick_profile(page: str, section: str, name: str, desc: str) -> str:
    text = f"{name} {desc}".lower()
    for rx, profile in KEYWORD_PROFILE:
        if re.search(rx, name.lower()):
            return profile if page in ("features.md",) or PAGE_PROFILE.get(page) in (None, profile, "settings", "home", "link", "setup") else PAGE_PROFILE[page]
    if page in PAGE_PROFILE:
        return PAGE_PROFILE[page]
    if page == "features.md":
        return SECTION_PROFILE.get(section) or next((p for rx, p in KEYWORD_PROFILE if re.search(rx, text)), "settings")
    return next((p for rx, p in KEYWORD_PROFILE if re.search(rx, text)), "settings")


def patch_points(p: dict, tests: str, bench: dict[str, str]) -> tuple[int, list[str]]:
    """Points and the bench files that name the patch."""
    ident, name = p["id"], p["name"]
    numeric = ident.isdigit()
    rx = re.compile(r"patch(?:es)?\s+" + re.escape(ident) + r"\b|\b" + re.escape(name[:-6]) + r"\b") if numeric else re.compile(r"\b" + re.escape(ident) + r"\b")
    in_tests = bool(rx.search(tests)) or name in tests
    files = [f for f, text in bench.items() if rx.search(text)]
    if files:
        return 100, files
    return (70 if in_tests else 40), []


def host_points(parts: list[str], tests: str, files: list[str], bench_words: list[str], bench: dict[str, str]) -> tuple[int, list[str], list[str]]:
    """Points for the host half: the files that exist whose name holds one of `parts`, whether a test names them, whether a bench note holds one of the words."""
    found = [f for f in files if any(part in f for part in parts)]
    if not found:
        return 0, [], []
    stems = {f.rsplit("/", 1)[-1].rsplit(".", 1)[0] for f in found}
    tested = any(re.search(r"\b" + re.escape(s) + r"\b", tests) for s in stems)
    notes = [f for f, text in bench.items() if any(w in text.lower() for w in bench_words)] if bench_words else []
    return (100 if notes and tested else 70 if tested else 40), found[:6], notes[:4]


def status_for(points: float, *, designed: bool = False, person: bool = False) -> str:
    if designed:
        return "designed"
    if person:
        return "needs person"
    if points < 20:
        return "designed" if points >= 5 else "idea"
    if points < 55:
        return "built"
    if points < 90:
        return "proven virtual"
    return "proven on unit"


PERSON_RX = re.compile(r"not yet (?:seen|heard|checked|tested|measured)|no one has seen|not tested with|has not been (?:seen|checked)|nobody has seen", re.I)
DESIGN_RX = re.compile(r"\bplanned\b|design only|not built|still being built|in progress|an experiment", re.I)
BUILT_NOT_FLASHED_RX = re.compile(r"built, not flashed|not flashed", re.I)
