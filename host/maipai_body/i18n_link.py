# ruff: noqa: E501
"""Page words for the encrypted-link card in the Security section (xiaozhi/link_security.py).

English and Spanish are written for the product; the other languages read English until a speaker writes them.
Every key starts with ``settings.ui.ln.``.
"""

from __future__ import annotations

EN: dict[str, str] = {
    "ln.title": "Encrypted link",
    "ln.help": "Scrambles everything between the robot and this computer, so nobody else on your Wi-Fi can listen in or pose as either one. The robot has to be updated to use it.",
    "ln.state": "Link right now",
    "ln.state.encrypted": "Encrypted",
    "ln.state.plain_allowed": "Plain allowed: it has used the encrypted link, but may also connect without it",
    "ln.state.plain": "Plain: not encrypted",
    "ln.state.never_seen": "Never seen encrypted: this robot has not used the encrypted link yet",
    "ln.choice": "Choice",
    "ln.required": "Required",
    "ln.allowed": "Allowed",
    "ln.off": "Off",
    "ln.required_help": "Required: the robot must use the encrypted link. A plain connection is refused. Use this once the robot has connected encrypted.",
    "ln.allowed_help": "Allowed: both links work. Choose this while you update the robot.",
    "ln.off_help": "Off: no encryption. For debugging only.",
    "ln.off_warning": "Warning: the link is not encrypted. Anyone on this network can read what the robot sends and hears. Turn it back to Allowed or Required when you are done.",
    "ln.unknown": "Not known: this page cannot reach the link settings",
}

ES: dict[str, str] = {
    "ln.title": "Enlace cifrado",
    "ln.help": "Cifra todo lo que va entre el robot y este ordenador, para que nadie más en tu Wi-Fi pueda escuchar ni hacerse pasar por ninguno de los dos. El robot debe estar actualizado para usarlo.",
    "ln.state": "Enlace ahora",
    "ln.state.encrypted": "Cifrado",
    "ln.state.plain_allowed": "Sin cifrar permitido: ya usó el enlace cifrado, pero también puede conectarse sin él",
    "ln.state.plain": "Sin cifrar",
    "ln.state.never_seen": "Nunca visto cifrado: este robot aún no ha usado el enlace cifrado",
    "ln.choice": "Opción",
    "ln.required": "Obligatorio",
    "ln.allowed": "Permitido",
    "ln.off": "Desactivado",
    "ln.required_help": "Obligatorio: el robot debe usar el enlace cifrado. Se rechaza una conexión sin cifrar. Úsalo cuando el robot ya se haya conectado cifrado.",
    "ln.allowed_help": "Permitido: funcionan los dos enlaces. Elígelo mientras actualizas el robot.",
    "ln.off_help": "Desactivado: sin cifrado. Solo para depurar.",
    "ln.off_warning": "Aviso: el enlace no está cifrado. Cualquiera en esta red puede leer lo que el robot envía y oye. Vuelve a Permitido u Obligatorio cuando termines.",
    "ln.unknown": "No se sabe: esta página no puede llegar a los ajustes del enlace",
}

CATALOGS: dict[str, dict[str, str]] = {
    code: {f"settings.ui.{k}": v for k, v in (ES if code == "es" else EN).items()}
    for code in ("en", "es", "fr", "de", "pt", "it")
}
