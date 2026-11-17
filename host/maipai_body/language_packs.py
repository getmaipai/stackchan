# ruff: noqa: E501
"""Language packs: the words the unit draws on its own screen, held on the host and sent when the unit's language is set.

The unit's image keeps English only (firmware patch K11). The weekday, month and chip words of every other screen
language are a pack of type ``language``: a zip with one file, ``words.txt``, in the format ``maipai_lang_core.h`` reads
(``lang``, ``order``, ``weekdays`` Sunday first, ``months``, ``alarm``, ``timer``). Plain ASCII only: the unit's Montserrat fonts
draw 0x20 to 0x7E and the degree sign, so an accented letter would show as a box. ``unit_extras.screen_text`` folds accents.

The five packs below ship with the host (they are only words, about 400 bytes each) and are put in the library at start, so
choosing a language on the settings page needs no download. A pack author may add another language with the same file layout;
the unit refuses a pack whose words are not ASCII, whose counts are wrong or whose keys are missing, and shows English instead.
"""

from __future__ import annotations

from maipai_body import packs as packs_mod
from maipai_body.unit_extras import screen_text

# code -> (native name for the page, weekdays Sunday first, months, alarm word, timer word, day first)
# The words are the ones the unit had built in before K11 (Train 4 patch U06), so a unit looks the same before and after.
WORDS: dict[str, dict[str, object]] = {
    "es": {
        "name": "Español",
        "weekdays": ("dom", "lun", "mar", "mie", "jue", "vie", "sab"),
        "months": (
            "ene",
            "feb",
            "mar",
            "abr",
            "may",
            "jun",
            "jul",
            "ago",
            "sep",
            "oct",
            "nov",
            "dic",
        ),
        "alarm": "Alarma",
        "timer": "Tiempo",
    },
    "fr": {
        "name": "Français",
        "weekdays": ("dim", "lun", "mar", "mer", "jeu", "ven", "sam"),
        "months": (
            "jan",
            "fev",
            "mar",
            "avr",
            "mai",
            "jun",
            "jul",
            "aou",
            "sep",
            "oct",
            "nov",
            "dec",
        ),
        "alarm": "Alarme",
        "timer": "Minut.",
    },
    "de": {
        "name": "Deutsch",
        "weekdays": ("So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"),
        "months": (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "Mai",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Okt",
            "Nov",
            "Dez",
        ),
        "alarm": "Wecker",
        "timer": "Timer",
    },
    "pt": {
        "name": "Português",
        "weekdays": ("dom", "seg", "ter", "qua", "qui", "sex", "sab"),
        "months": (
            "jan",
            "fev",
            "mar",
            "abr",
            "mai",
            "jun",
            "jul",
            "ago",
            "set",
            "out",
            "nov",
            "dez",
        ),
        "alarm": "Alarme",
        "timer": "Tempo",
    },
    "it": {
        "name": "Italiano",
        "weekdays": ("dom", "lun", "mar", "mer", "gio", "ven", "sab"),
        "months": (
            "gen",
            "feb",
            "mar",
            "apr",
            "mag",
            "giu",
            "lug",
            "ago",
            "set",
            "ott",
            "nov",
            "dic",
        ),
        "alarm": "Sveglia",
        "timer": "Timer",
    },
}
BUILT_IN = "en"  # English is in the image; there is no pack for it
CODES = tuple(WORDS)
NAMES = {
    "en": "English",
    **{code: str(row["name"]) for code, row in WORDS.items()},
}  # for the page, with their accents


def words_text(code: str) -> str:
    """The ``words.txt`` of one language pack, accents folded and every limit of the unit's reader checked."""
    row = WORDS[code]
    days = [screen_text(str(w)) for w in row["weekdays"]]  # type: ignore[attr-defined]
    months = [screen_text(str(w)) for w in row["months"]]  # type: ignore[attr-defined]
    alarm, timer = screen_text(str(row["alarm"])), screen_text(str(row["timer"]))
    check = [*days, *months]
    if len(days) != 7 or len(months) != 12:
        raise ValueError(f"{code}: 7 weekdays and 12 months are needed")
    for word in check:
        if not 1 <= len(word) <= 7 or any(not 0x21 <= ord(c) <= 0x7E or c in ",=" for c in word):
            raise ValueError(f"{code}: {word!r} cannot be drawn by the unit's screen font")
    for word in (alarm, timer):
        if not 1 <= len(word) <= 11 or any(not 0x20 <= ord(c) <= 0x7E or c == "=" for c in word):
            raise ValueError(f"{code}: {word!r} is not a chip word the unit can draw")
    return f"lang={code}\norder=dmy\nweekdays={','.join(days)}\nmonths={','.join(months)}\nalarm={alarm}\ntimer={timer}\n"


def build(code: str) -> packs_mod.Pack:
    """The pack for one language (the same bytes every time, so the unit's cache writes nothing twice)."""
    payload = packs_mod.zip_payload({"words.txt": words_text(code).encode("ascii")})
    return packs_mod.make_pack("language", f"Screen words {code}", payload, lang=code)


def install(library: packs_mod.PackLibrary) -> list[str]:
    """Put the shipped language packs in the library (once; a pack already there with the same bytes is left alone)."""
    added: list[str] = []
    have = {p["id"]: p["sha256"] for p in library.list("language")}
    for code in CODES:
        pack = build(code)
        pid = f"language/{packs_mod._slug(pack.name)}"
        if have.get(pid) == pack.sha256:
            continue
        library.add(pack)
        added.append(pid)
    return added


def pack_id(code: str) -> str:
    return f"language/{packs_mod._slug(f'Screen words {code}')}"
