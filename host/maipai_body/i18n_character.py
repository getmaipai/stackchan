# ruff: noqa: E501
"""Page words for the Character pack card on the Look page (install an illustrated character as the robot's face).

English and Spanish are written for the product; the other languages read English until a speaker writes them (the
machine-drafted fills in ``i18n_fill`` may replace them). Every key starts with ``settings.ui.char.``.
"""

from __future__ import annotations

EN: dict[str, str] = {
    "char.title": "Character pack",
    "char.help": "Install a shared illustrated character as this robot's face. The pack is checked first. It replaces the pictures now on the face. Press Send to the unit afterwards to show it.",
    "char.choose": "Choose a character pack (.zip)",
    "char.import": "Install the pack",
    "char.checking": "Checking the pack...",
    "char.done": "Character pack installed. Press Send to the unit to show it on the robot's face.",
    "char.too_big": "That file is larger than 8 MB. Choose a smaller pack.",
    "char.problems": "This pack has problems:",
    "char.unreadable": "That file could not be read. Choose a .zip character pack.",
}

ES: dict[str, str] = {
    "char.title": "Paquete de personaje",
    "char.help": "Instala un personaje ilustrado compartido como cara de este robot. Primero se revisa el paquete. Reemplaza las imágenes que hay ahora en la cara. Después pulsa Enviar a la unidad para verlo.",
    "char.choose": "Elige un paquete de personaje (.zip)",
    "char.import": "Instalar el paquete",
    "char.checking": "Revisando el paquete...",
    "char.done": "Paquete de personaje instalado. Pulsa Enviar a la unidad para verlo en la cara del robot.",
    "char.too_big": "Ese archivo pesa más de 8 MB. Elige un paquete más pequeño.",
    "char.problems": "Este paquete tiene problemas:",
    "char.unreadable": "No se pudo leer ese archivo. Elige un paquete de personaje .zip.",
}

CATALOGS: dict[str, dict[str, str]] = {
    code: {f"settings.ui.{k}": v for k, v in (ES if code == "es" else EN).items()}
    for code in ("en", "es", "fr", "de", "pt", "it")
}
