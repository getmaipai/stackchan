# ruff: noqa: E501
"""Page words for "Look around when I hear the wake word" (wake_look.py). English and Spanish; the other languages read English."""

from __future__ import annotations

EN = {
    "settings.ui.wake_look": "Look around when I hear the wake word",
    "settings.ui.wake_look_help": "A short head turn so the robot seems to look for you. Never while carried, locked, muted, asleep, at night, during games or dances.",
}
ES = {
    "settings.ui.wake_look": "Mirar a su alrededor cuando oiga la palabra de llamada",
    "settings.ui.wake_look_help": "Un giro corto de la cabeza para que el robot parezca buscarte. Nunca mientras lo llevan en la mano, está bloqueado, silenciado, dormido, de noche, ni durante juegos o bailes.",
}
# French, German, Portuguese and Italian read English until a speaker writes them (the page asks for every key in every language).
CATALOGS: dict[str, dict[str, str]] = {"en": EN, "es": ES, "fr": EN, "de": EN, "pt": EN, "it": EN}
