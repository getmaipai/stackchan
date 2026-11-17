# ruff: noqa: E501
"""The reply tag grammar, in one place: mood tags, overlay tags, and the fallback when a reply has no tag.

A reply may carry square-bracket tags. The speech path strips every one of them before anything is spoken
(a tag, known or not, is never said aloud); this module says what each one means.

Mood tag (one, at the start of a reply, or between sentences to change the mood):

    [happy] [sad] [surprised] [angry] [doubt] [love] [sleepy] [neutral]

Overlay tag (a span of the reply; the overlay starts when the span is spoken and ends after it):

    [rain]it is going to rain all day[/rain]
    [snow heavy]...[/snow]        intensity: light, normal (default) or heavy; also [snow:heavy]
    [rain]no closing tag runs to the end of that sentence

A span may cover several sentences when its closing tag has already arrived with the text (a reply spoken from
one piece); when a model streams one sentence at a time, an overlay ends with the sentence it opened in.

Spanish works too: [feliz], [triste], [lluvia]...[/lluvia], [nieve fuerte]. A tag that is not in these lists is
dropped and never spoken. ``mood:`` and ``overlay:`` prefixes are accepted ([mood:happy]).

Weather data is not here and never will be: this module only knows how to draw. Home maps a weather update to a
tag or to the ``overlay`` tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---- the one list of moods -------------------------------------------------------------------------

MOODS: tuple[str, ...] = ("happy", "sad", "surprised", "angry", "doubt", "love", "sleepy", "neutral")

# What the expression layer calls each mood (bodies/stackchan/expression_map.py REPLY_MOOD_FACE_MAP).
MOOD_CUE: dict[str, str] = {
    "happy": "happiness",
    "sad": "sadness",
    "surprised": "surprise",
    "angry": "anger",
    "doubt": "doubt",
    "love": "love",
    "sleepy": "sleepiness",
    "neutral": "neutral",
}

MOOD_ALIASES: dict[str, str] = {
    "feliz": "happy", "contento": "happy", "alegre": "happy", "joy": "happy",
    "triste": "sad",
    "sorprendido": "surprised", "sorprendida": "surprised", "sorpresa": "surprised", "surprise": "surprised",
    "enojado": "angry", "enojada": "angry", "enfadado": "angry", "enfadada": "angry", "mad": "angry",
    "duda": "doubt", "dudoso": "doubt", "curious": "doubt",
    "amor": "love", "cariño": "love", "carino": "love",
    "sueño": "sleepy", "sueno": "sleepy", "dormido": "sleepy", "tired": "sleepy",
    "neutro": "neutral", "calm": "neutral",
}  # fmt: skip

# ---- the one list of overlays ----------------------------------------------------------------------

# The single overlays, then the named combinations (patch O01). The unit's core has the same two lists (MO_NAMES without its two parts
# "moon" and "sparkles", and MOP_NAMES); tests/test_firmware_fx_cores.py keeps them equal.
ELEMENT_OVERLAYS: tuple[str, ...] = (
    "rain", "snow", "sun", "clouds", "wind", "thunder", "fog", "stars",
    "disco", "confetti", "fireworks", "hearts", "steam", "balloons", "leaves", "zzz",
)  # fmt: skip
COMBINED_OVERLAYS: tuple[str, ...] = (
    "stormy", "rainy", "snowy", "sunny", "windy", "night", "party", "celebrate", "love", "sleeping",
)  # fmt: skip
OVERLAYS: tuple[str, ...] = ELEMENT_OVERLAYS + COMBINED_OVERLAYS
# A name that is both a mood and an overlay: a bare tag means the mood, ``[overlay:love]`` (or a heavy or light word after it) the overlay.
MOOD_AND_OVERLAY: frozenset[str] = frozenset({"love"})

OVERLAY_ALIASES: dict[str, str] = {
    "lluvia": "rain", "llover": "rain",
    "nieve": "snow",
    "sol": "sun",
    "nubes": "clouds", "nube": "clouds", "nublado": "clouds", "cloud": "clouds", "cloudy": "clouds",
    "viento": "wind",
    "trueno": "thunder", "truenos": "thunder", "relampago": "thunder", "relámpago": "thunder",
    "niebla": "fog", "bruma": "fog", "foggy": "fog",
    "estrellas": "stars", "estrella": "stars", "star": "stars",
    "discoteca": "disco",
    "confeti": "confetti",
    "fuegos": "fireworks", "fuegosartificiales": "fireworks", "fuegos_artificiales": "fireworks", "firework": "fireworks",
    "corazones": "hearts", "corazon": "hearts", "corazón": "hearts", "heart": "hearts",
    "vapor": "steam", "humo": "steam",
    "globos": "balloons", "globo": "balloons", "balloon": "balloons",
    "hojas": "leaves", "hoja": "leaves", "leaf": "leaves", "otoño": "leaves", "otono": "leaves",
    "ronquido": "zzz", "dormir": "zzz", "snore": "zzz",
    # the combined names (clouds, rain, thunder and so on in one): English, then Spanish
    "storm": "stormy", "thunderstorm": "stormy", "tormenta": "stormy", "tormentoso": "stormy", "tormenta_electrica": "stormy", "tormenta_eléctrica": "stormy",
    "lluvioso": "rainy", "lluviosa": "rainy",
    "snowfall": "snowy", "nevada": "snowy", "nevado": "snowy", "nevoso": "snowy",
    "sunshine": "sunny", "soleado": "sunny", "soleada": "sunny", "despejado": "sunny", "dia_soleado": "sunny", "día_soleado": "sunny",
    "ventoso": "windy", "ventosa": "windy",
    "nighttime": "night", "noche": "night", "nocturno": "night", "noche_estrellada": "night", "starry": "night",
    "fiesta": "party", "festejo": "party", "parranda": "party", "birthday": "party", "cumpleaños": "party", "cumpleanos": "party",
    "celebration": "celebrate", "celebrar": "celebrate", "celebracion": "celebrate", "celebración": "celebrate", "hooray": "celebrate", "hurra": "celebrate",
    "lovely": "love", "romance": "love", "romantic": "love", "romantico": "love", "romántico": "love", "enamorado": "love", "enamorada": "love",
    "sleep": "sleeping", "asleep": "sleeping", "durmiendo": "sleeping",
}  # fmt: skip

INTENSITIES: tuple[str, ...] = ("light", "normal", "heavy")
INTENSITY_ALIASES: dict[str, str] = {
    "soft": "light", "gentle": "light", "ligera": "light", "ligero": "light", "suave": "light",
    "medium": "normal", "media": "normal", "medio": "normal",
    "strong": "heavy", "intense": "heavy", "fuerte": "heavy", "intensa": "heavy", "intenso": "heavy", "pesada": "heavy",
}  # fmt: skip
DEFAULT_INTENSITY = "normal"

# Seconds an overlay runs when the span's length is not known (the tool call and the settings button).
DEFAULT_SECONDS = 8
MAX_SECONDS = 600
WORDS_PER_SECOND = 2.6  # a calm speaking pace; the span's overlay lasts about as long as it is spoken


@dataclass(frozen=True)
class Tag:
    """What one ``[...]`` meant. ``kind`` is mood, overlay (open), overlay_end (close) or unknown."""

    kind: str
    name: str = ""
    intensity: str = DEFAULT_INTENSITY


def _word(text: str) -> str:
    return re.sub(r"[\s\-]+", "_", text.strip().lower())


def parse_tag(inner: str) -> Tag:
    """Classify the text between the brackets. Never raises: anything else is ``unknown``."""
    text = inner.strip().lower()
    forced = ""
    for prefix in ("mood:", "overlay:", "mood=", "overlay="):
        if text.startswith(prefix):
            forced = prefix[:-1]
            text = text[len(prefix) :].strip()
            break
    closing = text.startswith("/")
    if closing:
        text = text[1:].strip()
    words = [w for w in re.split(r"[\s:=]+", text) if w]
    if not words:
        return Tag("unknown")
    head, rest = _word(words[0]), " ".join(words[1:])
    # a name of two words ("fuegos artificiales") is tried first, then one word with an intensity after it
    name = _overlay_name(_word(" ".join(words[:2]))) if len(words) > 1 else None
    if name is not None:
        rest = " ".join(words[2:])
    else:
        name = _overlay_name(head)
    # [love] is the mood unless the tag says overlay or carries an intensity word; [/love] always closes the overlay
    if name in MOOD_AND_OVERLAY and head in MOOD_AND_OVERLAY and not closing and not rest and forced != "overlay":
        name = None
    if forced == "mood" and name is not None and head not in OVERLAYS:
        name = None
    if name is not None:
        if closing:
            return Tag("overlay_end", name)
        word = _word(rest) if rest else DEFAULT_INTENSITY
        word = INTENSITY_ALIASES.get(word, word)
        return Tag("overlay", name, word if word in INTENSITIES else DEFAULT_INTENSITY)
    if closing:
        return Tag("unknown")
    mood = MOOD_ALIASES.get(head, head)
    if mood in MOODS and not rest:
        return Tag("mood", mood)
    return Tag("unknown")


def _overlay_name(word: str) -> str | None:
    word = OVERLAY_ALIASES.get(word, word)
    return word if word in OVERLAYS else None


def span_seconds(text: str) -> float:
    """How long a span of spoken text lasts, for an overlay with a closing tag."""
    words = len(text.split())
    return float(max(2, min(MAX_SECONDS, round(words / WORDS_PER_SECOND + 1))))


# ---- the persona instruction ----------------------------------------------------------------------

PERSONA_SUFFIX = (
    " Start every reply with exactly one mood tag in square brackets, chosen from: "
    + " ".join(f"[{m}]" for m in MOODS)
    + ". The tag is never spoken. Example: [happy] Sure, I can do that!"
)


def persona_with_tags(persona: str) -> str:
    """The persona text plus the one-line mood tag instruction (not added twice)."""
    if "mood tag in square brackets" in persona:
        return persona
    return persona.rstrip() + PERSONA_SUFFIX
