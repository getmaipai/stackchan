# ruff: noqa: E501
"""Page words for the wake word maker card on the Voice page (maipai_packages/wake_word_maker). Keys start with ``settings.ui.ww.``.
English and Spanish are written; the other languages read English until a speaker writes them."""

from __future__ import annotations

EN: dict[str, str] = {
    "ww.title": "Make your own wake word",
    "ww.help": "Record the word you want, then some other speech, and the host trains a small model on this computer. Nothing is uploaded. The robot does not use the new word yet: installing it only keeps it ready.",
    "ww.name": "The word (lowercase letters)",
    "ww.rec_word": "Record the word (1 second)",
    "ww.rec_other": "Record other speech (1 second)",
    "ww.counts": "Recorded: {w} of the word, {o} of other speech. You need at least {n} of each.",
    "ww.train": "Train and check",
    "ww.install": "Install",
    "ww.clear": "Start over",
    "ww.recording": "Recording... speak now.",
    "ww.no_mic": "This page cannot use a microphone here. Open the settings page on the host computer.",
    "ww.result": "Check: ",
    "ww.installed": "Installed: {w}. The robot does not use it yet.",
    "ww.error": "That did not work. Try again.",
}
ES: dict[str, str] = {
    "ww.title": "Crea tu propia palabra de activación",
    "ww.help": "Graba la palabra que quieras y después otras frases; el anfitrión entrena un modelo pequeño en este ordenador. No se sube nada. El robot aún no usa la palabra nueva: instalarla solo la deja lista.",
    "ww.name": "La palabra (letras minúsculas)",
    "ww.rec_word": "Grabar la palabra (1 segundo)",
    "ww.rec_other": "Grabar otras frases (1 segundo)",
    "ww.counts": "Grabado: {w} de la palabra, {o} de otras frases. Necesitas al menos {n} de cada una.",
    "ww.train": "Entrenar y comprobar",
    "ww.install": "Instalar",
    "ww.clear": "Empezar de nuevo",
    "ww.recording": "Grabando... habla ahora.",
    "ww.no_mic": "Esta página no puede usar un micrófono aquí. Abre la página de ajustes en el ordenador anfitrión.",
    "ww.result": "Comprobación: ",
    "ww.installed": "Instalada: {w}. El robot aún no la usa.",
    "ww.error": "No funcionó. Inténtalo de nuevo.",
}
CATALOGS: dict[str, dict[str, str]] = {
    code: {f"settings.ui.{k}": v for k, v in (ES if code == "es" else EN).items()}
    for code in ("en", "es", "fr", "de", "pt", "it")
}
