# ruff: noqa: E501
"""Page words for the Family and safety card, the pairing code card and the phone card on the home page.

English and Spanish are written for the product; the other languages read English until a speaker writes them.
Every key starts with ``settings.ui.fam.``.
"""

from __future__ import annotations

EN: dict[str, str] = {
    "fam.title": "Family and safety",
    "fam.help": "What the robot is doing right now, in plain words.",
    "fam.l_robot": "Robot",
    "fam.l_mic": "Microphone",
    "fam.l_camera": "Camera",
    "fam.l_lock": "Lock",
    "fam.online": "Online",
    "fam.offline": "Offline",
    "fam.listening": "Listening",
    "fam.muted": "Muted",
    "fam.camera_on": "Camera on",
    "fam.camera_off": "Camera off",
    "fam.locked": "Locked",
    "fam.unlocked": "Not locked",
    "fam.unknown": "Not known",
    "fam.privacy": "Your voice and pictures stay in your home. Nothing goes to the internet unless you turn it on.",
    "fam.no_history": "The robot does not keep what it hears or says. There is no history to read.",
    "fam.brain_note": "Content levels and kid mode belong to the brain you connect (MaiPai Home for a child's robot), not to this page.",
    "fam.recent": "Who controlled the robot lately",
    "fam.recent_none": "Nobody has used remote control.",
    "pair.title": "Pair a robot",
    "pair.help": "Press the button, then type the code on the robot's setup page. It works once.",
    "pair.button": "Show a pairing code",
    "pair.minutes": "Valid for 10 minutes",
    "pair.error": "The code could not be made. Open this page on the host computer and try again.",
    "pair.waiting": "A robot is showing six digits. Type them here:",
    "pair.approve": "Approve",
    "pair.paired": "Paired. The robot now uses an encrypted link.",
    "phone.title": "Open this page on your phone",
    "phone.help": "Scan the code with your phone's camera. It logs the phone in to this page. Anyone who scans it can change the robot's settings, so keep it private.",
    "phone.show": "Show the phone code",
    "phone.error": "The phone code could not be made. Open this page on the host computer and try again.",
}

ES: dict[str, str] = {
    "fam.title": "Familia y seguridad",
    "fam.help": "Lo que hace el robot ahora, en palabras sencillas.",
    "fam.l_robot": "Robot",
    "fam.l_mic": "Micrófono",
    "fam.l_camera": "Cámara",
    "fam.l_lock": "Bloqueo",
    "fam.online": "Conectado",
    "fam.offline": "Sin conexión",
    "fam.listening": "Escuchando",
    "fam.muted": "Silenciado",
    "fam.camera_on": "Cámara encendida",
    "fam.camera_off": "Cámara apagada",
    "fam.locked": "Bloqueado",
    "fam.unlocked": "Sin bloqueo",
    "fam.unknown": "No se sabe",
    "fam.privacy": "Tu voz y tus fotos se quedan en casa. Nada sale a internet si no lo activas.",
    "fam.no_history": "El robot no guarda lo que oye ni lo que dice. No hay historial que leer.",
    "fam.brain_note": "Los niveles de contenido y el modo infantil dependen del cerebro que conectes (MaiPai Home para el robot de un niño), no de esta página.",
    "fam.recent": "Quién controló el robot hace poco",
    "fam.recent_none": "Nadie ha usado el control remoto.",
    "pair.title": "Emparejar un robot",
    "pair.help": "Pulsa el botón y escribe el código en la página de configuración del robot. Funciona una vez.",
    "pair.button": "Mostrar un código de emparejamiento",
    "pair.minutes": "Válido 10 minutos",
    "pair.error": "No se pudo crear el código. Abre esta página en el ordenador anfitrión y vuelve a intentarlo.",
    "pair.waiting": "Un robot muestra seis dígitos. Escríbelos aquí:",
    "pair.approve": "Aprobar",
    "pair.paired": "Emparejado. El robot ahora usa un enlace cifrado.",
    "phone.title": "Abre esta página en tu teléfono",
    "phone.help": "Escanea el código con la cámara del teléfono. Inicia sesión en esta página. Quien lo escanee puede cambiar los ajustes del robot, así que guárdalo en privado.",
    "phone.show": "Mostrar el código del teléfono",
    "phone.error": "No se pudo crear el código del teléfono. Abre esta página en el ordenador anfitrión y vuelve a intentarlo.",
}

CATALOGS: dict[str, dict[str, str]] = {
    code: {f"settings.ui.{k}": v for k, v in (ES if code == "es" else EN).items()}
    for code in ("en", "es", "fr", "de", "pt", "it")
}
