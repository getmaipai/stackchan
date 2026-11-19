"""Offline lines by situation (owner decision 24 extension; docs/design/content-pantry.md, "Lines by situation"): with no host and no model the unit picks a canned line for the situation, shows
it in the subtitle strip and plays the code-made mumble. This is the playground's mock of that: six of the twenty situations, one line each in the six languages (the real set has about six per
situation per language and lives in the built-in set of the pantry, `seed/<language>-line.json`). The mouth levels come from the mumble reference (`mumble.py`), the same sound the unit plays.
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

LANGS = ["en", "es", "fr", "de", "pt", "it"]
SITUATIONS = ["wake_heard_offline", "cannot_reach_home", "back_online", "touch_head", "pick_up", "goodnight"]
MAX_BYTES = 100   # the record's text limit

LINES = {
    "wake_heard_offline": {
        "en": "I heard you. I'm right here.",
        "es": "Te oigo. Aquí estoy.",
        "fr": "Je vous entends. Je suis là.",
        "de": "Ich höre dich. Ich bin da.",
        "pt": "Estou ouvindo. Estou aqui.",
        "it": "Ti sento. Sono qui.",
    },
    "cannot_reach_home": {
        "en": "I can't reach Home. Still trying.",
        "es": "No encuentro Home. Pruebo.",
        "fr": "Je ne joins pas Home. J'essaie.",
        "de": "Home nicht da. Ich probiere.",
        "pt": "Não alcanço o Home. Tentando.",
        "it": "Non raggiungo Home. Riprovo.",
    },
    "back_online": {
        "en": "Home is back. Thanks.",
        "es": "Home ha vuelto. Gracias.",
        "fr": "Home est de retour. Merci.",
        "de": "Home ist wieder da. Danke.",
        "pt": "O Home voltou. Obrigado.",
        "it": "Home è tornato. Grazie.",
    },
    "touch_head": {
        "en": "That feels nice.",
        "es": "Qué agradable.",
        "fr": "C'est agréable.",
        "de": "Das fühlt sich schön an.",
        "pt": "Que gostoso.",
        "it": "Che bello.",
    },
    "pick_up": {
        "en": "Oh, up we go.",
        "es": "Vaya, arriba vamos.",
        "fr": "Oh, on monte.",
        "de": "Oh, es geht nach oben.",
        "pt": "Opa, lá vamos nós.",
        "it": "Oh, si sale.",
    },
    "goodnight": {
        "en": "Good night. See you tomorrow.",
        "es": "Buenas noches. Hasta mañana.",
        "fr": "Bonne nuit. À demain.",
        "de": "Gute Nacht. Bis morgen.",
        "pt": "Boa noite. Até amanhã.",
        "it": "Buonanotte. A domani.",
    },
}


def line(situation: str, lang: str) -> str:
    return LINES[situation][lang]


def mouth_levels(text: str, span_ms: int | None = None) -> list[int]:
    """The mouth level (0 to 100) of every mumble slot of the line, from the reference sound (`mumble.blips`): the unit's mouth follows the same list while the line plays."""
    import mumble
    return [b.mouth for b in mumble.blips(text, 0, span_ms or max(900, 75 * len(text)))]


def mid_speech_level(text: str) -> int:
    """The mouth level a still frame shows: the loudest of the first half of the line, so the frame shows an open mouth with the words under it."""
    levels = mouth_levels(text)
    half = levels[: max(1, len(levels) // 2)]
    return max(half)
