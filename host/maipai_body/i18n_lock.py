# ruff: noqa: E501
"""Page words for the Security section of the settings page (the passcode lock, unit_lock.py).

English and Spanish are written for the product; French, German, Portuguese and Italian read English until a speaker writes them.
Every key starts with ``settings.ui.lk.`` except the section's name, ``settings.ui.g.security``.
"""

from __future__ import annotations

EN: dict[str, str] = {
    "g.security": "Security",
    "lk.title": "Passcode lock",
    "lk.help": "A code keeps other people from using the robot. The robot keeps the code itself and checks it by itself. This page never stores it and cannot unlock the robot: only the keypad on the robot does.",
    "lk.status": "Status",
    "lk.status.none": "No code set",
    "lk.status.unlocked": "Unlocked",
    "lk.status.locked": "Locked",
    "lk.status.unknown": "Not known: the robot is not connected",
    "lk.auto.off": "Auto lock is off",
    "lk.auto.on": "Locks itself after {n} minutes without use",
    "lk.set_title": "Set a code",
    "lk.change_title": "Change the code",
    "lk.set_help": "4 to 6 digits. Type the new code twice.",
    "lk.current": "Current code",
    "lk.new": "New code",
    "lk.again": "New code again",
    "lk.save": "Save code",
    "lk.remove_title": "Remove the code",
    "lk.remove_help": "The robot stops locking. Type the current code to confirm.",
    "lk.remove_current": "Current code",
    "lk.remove": "Remove code",
    "lk.auto_title": "Auto lock",
    "lk.auto_help": "Lock after this long without a touch, a wake word or a remote action.",
    "lk.auto_off": "Off",
    "lk.minutes": "{n} min",
    "lk.now": "Lock now",
    "lk.now_help": "Locks the robot at once. Needs a code.",
    "lk.locked_note": "The robot is locked, so it will not take changes from here. Unlock it with the code on its keypad.",
    "lk.forgot": "Forgot the code? The robot's two-step physical reset clears it, along with everything else.",
    "lk.digits": "4 to 6 digits",
}

ES: dict[str, str] = {
    "g.security": "Seguridad",
    "lk.title": "Bloqueo con código",
    "lk.help": "Un código evita que otras personas usen el robot. El robot guarda el código y lo comprueba por sí mismo. Esta página nunca lo guarda y no puede desbloquear el robot: solo lo hace el teclado del robot.",
    "lk.status": "Estado",
    "lk.status.none": "Sin código",
    "lk.status.unlocked": "Desbloqueado",
    "lk.status.locked": "Bloqueado",
    "lk.status.unknown": "No se sabe: el robot no está conectado",
    "lk.auto.off": "El bloqueo automático está desactivado",
    "lk.auto.on": "Se bloquea solo tras {n} minutos sin uso",
    "lk.set_title": "Crear un código",
    "lk.change_title": "Cambiar el código",
    "lk.set_help": "De 4 a 6 dígitos. Escribe el código nuevo dos veces.",
    "lk.current": "Código actual",
    "lk.new": "Código nuevo",
    "lk.again": "Código nuevo otra vez",
    "lk.save": "Guardar código",
    "lk.remove_title": "Quitar el código",
    "lk.remove_help": "El robot deja de bloquearse. Escribe el código actual para confirmar.",
    "lk.remove_current": "Código actual",
    "lk.remove": "Quitar código",
    "lk.auto_title": "Bloqueo automático",
    "lk.auto_help": "Se bloquea tras este tiempo sin un toque, una palabra de activación o una acción remota.",
    "lk.auto_off": "Desactivado",
    "lk.minutes": "{n} min",
    "lk.now": "Bloquear ahora",
    "lk.now_help": "Bloquea el robot de inmediato. Necesita un código.",
    "lk.locked_note": "El robot está bloqueado y no aceptará cambios desde aquí. Desbloquéalo con el código en su teclado.",
    "lk.forgot": "¿Olvidaste el código? El reinicio físico de dos pasos del robot lo borra, junto con todo lo demás.",
    "lk.digits": "De 4 a 6 dígitos",
}

CATALOGS: dict[str, dict[str, str]] = {
    code: {f"settings.ui.{k}": v for k, v in (ES if code == "es" else EN).items()}
    for code in ("en", "es", "fr", "de", "pt", "it")
}
