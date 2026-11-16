# ruff: noqa: E501
"""Small message catalog for the host web page and the flasher messages.

English is the source. Spanish is a full second catalog; a missing Spanish key falls back to
English so a page never shows a bare key. Languages are "en" and "es" (docs/design/languages.md).
"""

from __future__ import annotations

SUPPORTED = ("en", "es")
DEFAULT = "en"

CATALOG: dict[str, dict[str, str]] = {
    "en": {
        "settings.title": "StackChan settings",
        "settings.unit": "Unit",
        "settings.unit_name": "Unit name",
        "settings.unit_pick": "Unit",
        "settings.device_id": "Device-Id",
        "settings.wifi": "Wi-Fi setup",
        "settings.wifi.set": "Wi-Fi is set up",
        "settings.wifi.unset": "Wi-Fi is not set up yet",
        "settings.wifi.unknown": "Wi-Fi status unknown (the unit is not connected)",
        "settings.host_address": "Host address",
        "settings.persona": "Persona",
        "settings.llm": "Language model for this unit",
        "settings.llm_url": "Model URL",
        "settings.llm_model": "Model name",
        "settings.llm_key_env": "API key variable name",
        "settings.alarms": "Alarms",
        "settings.alarm_add": "Add alarm",
        "settings.alarm_time": "Time (24 hour, HH:MM)",
        "settings.alarm_label": "Label",
        "settings.volume_cap": "Volume cap (0 to 100)",
        "settings.mute": "Mute",
        "settings.firmware": "Firmware version",
        "settings.firmware.unknown": "unknown",
        "settings.online": "Connection",
        "settings.online.yes": "Online",
        "settings.online.no": "Offline",
        "settings.online.unknown": "Unknown (open this page on the running host)",
        "settings.update_confirm": "Install update",
        "settings.update_confirm_ask": "Install this update on the unit now? The unit restarts.",
        "settings.update": "Update",
        "settings.save": "Save",
        "settings.language": "Language",
        "settings.no_units": "No paired unit yet. Run stackchan pair, then enter the code on the unit.",
        "settings.saved": "Saved.",
        "settings.local_only": "Open this page on the host computer to change settings.",
        "settings.update.started": "Update started. The unit restarts when it finishes.",
        "settings.update.none": "No update source is set. Add update_source to robot.toml and try again.",
        "settings.update.current": "The unit already runs the newest firmware.",
        "update.ota_no_signature": (
            "The image signature file {name} is missing or not 64 bytes in {folder}, so nothing was sent. "
            "Sign the app image with the release key, or flash this release over USB instead."
        ),
        "update.unit_refused": "The unit refused the update. {why}",
        "update.unsigned": (
            "The release manifest is not signed, so it was not used. Download the release "
            "again from the official source, or build it with release.sh --signing-key."
        ),
        "update.no_key": (
            "No trusted release key was found at {path}. Put the release public key "
            "(a PEM file) there, or pass --public-key PATH."
        ),
        "update.bad_signature": (
            "The signature does not match the trusted key, so nothing was flashed. "
            "Download the release again from the official source."
        ),
        "update.bad_manifest": (
            "The release manifest is not valid ({why}). Download the release again "
            "from the official source."
        ),
        "update.part_missing": (
            "Release file {name} is missing from {folder}. Download the whole release folder again."
        ),
        "update.part_mismatch": (
            "Release file {name} does not match its signed size or hash, so nothing was "
            "flashed. Download the release again from the official source."
        ),
        "update.wrong_preset": (
            "This release is the {found} preset but you asked for {wanted}. "
            "Pass --preset {found} or pick the {wanted} release."
        ),
        "update.wrong_chip": (
            "This release is for {found}, not ESP32-S3. Use the StackChan release."
        ),
        "update.slot_rule": (
            "The app image would leave {free:.1f} percent of the smaller update slot free, "
            "below the {need:d} percent rule. Use a smaller build, or the home preset only "
            "if it fits."
        ),
        "update.no_table": (
            "The release has no partition table, so the free-slot rule cannot be checked "
            "and nothing was flashed. Download the whole release folder again."
        ),
        "update.slot_ok": (
            "App image {size:,} bytes of a {slot:,} byte slot: {free:.1f} percent free "
            "(rule: at least {need:d} percent)."
        ),
        "update.not_newer": (
            "The unit runs {unit} and the release is {release}, so there is nothing to "
            "update. Use stackchan flash to put this exact version on the unit."
        ),
        "update.needs_port": (
            "Say which serial port the unit is on, for example --port /dev/cu.usbmodem101. "
            "Nothing was flashed."
        ),
        "update.no_esptool": (
            "esptool is not installed, so nothing was flashed. Install it with "
            "pip install esptool and run the command again."
        ),
        "update.esptool_failed": (
            "esptool stopped with code {code}. Check the cable and port, hold the unit in "
            "download mode, and run the command again."
        ),
        "update.no_host": (
            "No running host answered at {url}, so the unit was not updated over the air. "
            "Start the host, or use stackchan flash --port PORT over USB."
        ),
        "update.dry": "Dry run: checked everything, flashed nothing.",
        "update.ok": "Release {version} ({preset}) passed every check.",
        "settings.face": "Face",
        "settings.face.style": "Face style",
        "settings.face.style.classic": "Classic",
        "settings.face.style.big_eyes": "Big eyes",
        "settings.face.style.minimal": "Minimal",
        "settings.face.colour": "Face colour",
        "settings.face.colour.none": "None (white)",
        "settings.face.colour.mint": "Mint",
        "settings.face.colour.sky": "Sky",
        "settings.face.colour.amber": "Amber",
        "settings.face.colour.rose": "Rose",
        "settings.face.colour.lilac": "Lilac",
        "settings.face.colour.lime": "Lime",
        "settings.face.colour.coral": "Coral",
        "settings.face.captions": "Show captions on the screen",
        "settings.face.tod": "Change the face with the time of day",
        "settings.face.hours": "Day starts (morning, day, evening, night hours, 0 to 23, for example 6, 9, 18, 21)",
        "settings.face.unavailable": "This unit's firmware does not have:",
        "settings.face.pending": "Saved here. The unit is not connected; it gets these settings when it reconnects.",
        "settings.face.save": "Save face",
        "settings.face.reset": "Back to the plain face",
    },
    "es": {
        "settings.title": "Ajustes de StackChan",
        "settings.unit": "Unidad",
        "settings.unit_name": "Nombre de la unidad",
        "settings.unit_pick": "Unidad",
        "settings.device_id": "Device-Id",
        "settings.wifi": "Configuracion de Wi-Fi",
        "settings.wifi.set": "El Wi-Fi esta configurado",
        "settings.wifi.unset": "El Wi-Fi aun no esta configurado",
        "settings.wifi.unknown": "Estado del Wi-Fi desconocido (la unidad no esta conectada)",
        "settings.host_address": "Direccion del host",
        "settings.persona": "Personalidad",
        "settings.llm": "Modelo de lenguaje de esta unidad",
        "settings.llm_url": "URL del modelo",
        "settings.llm_model": "Nombre del modelo",
        "settings.llm_key_env": "Nombre de la variable de la clave API",
        "settings.alarms": "Alarmas",
        "settings.alarm_add": "Agregar alarma",
        "settings.alarm_time": "Hora (24 horas, HH:MM)",
        "settings.alarm_label": "Etiqueta",
        "settings.volume_cap": "Limite de volumen (0 a 100)",
        "settings.mute": "Silencio",
        "settings.firmware": "Version del firmware",
        "settings.firmware.unknown": "desconocida",
        "settings.online": "Conexion",
        "settings.online.yes": "En linea",
        "settings.online.no": "Sin conexion",
        "settings.online.unknown": "Desconocida (abra esta pagina en el host en marcha)",
        "settings.update_confirm": "Instalar actualizacion",
        "settings.update_confirm_ask": "Instalar esta actualizacion en la unidad ahora? La unidad se reinicia.",
        "settings.update": "Actualizar",
        "settings.save": "Guardar",
        "settings.language": "Idioma",
        "settings.no_units": (
            "Aun no hay unidades emparejadas. Ejecuta stackchan pair e ingresa el codigo "
            "en la unidad."
        ),
        "settings.saved": "Guardado.",
        "settings.local_only": "Abre esta pagina en el computador host para cambiar los ajustes.",
        "settings.update.started": "Actualizacion iniciada. La unidad se reinicia al terminar.",
        "settings.update.none": (
            "No hay fuente de actualizacion. Agrega update_source en robot.toml e intenta de nuevo."
        ),
        "settings.update.current": "La unidad ya tiene el firmware mas reciente.",
        "update.ota_no_signature": (
            "Falta el archivo de firma {name} de la imagen, o no mide 64 bytes, en {folder}, asi que no se envio nada. "
            "Firma la imagen con la clave de la version, o instala esta version por USB."
        ),
        "update.unit_refused": "La unidad rechazo la actualizacion. {why}",
        "update.unsigned": (
            "El manifiesto de la version no esta firmado, asi que no se uso. Descarga la "
            "version de nuevo desde la fuente oficial, o compilala con release.sh --signing-key."
        ),
        "update.no_key": (
            "No se encontro la clave de confianza en {path}. Coloca alli la clave publica "
            "de la version (un archivo PEM), o usa --public-key RUTA."
        ),
        "update.bad_signature": (
            "La firma no coincide con la clave de confianza, asi que no se instalo nada. "
            "Descarga la version de nuevo desde la fuente oficial."
        ),
        "update.bad_manifest": (
            "El manifiesto de la version no es valido ({why}). Descarga la version de "
            "nuevo desde la fuente oficial."
        ),
        "update.part_missing": (
            "Falta el archivo {name} en {folder}. Descarga de nuevo la carpeta completa "
            "de la version."
        ),
        "update.part_mismatch": (
            "El archivo {name} no coincide con su tamano o hash firmado, asi que no se "
            "instalo nada. Descarga la version de nuevo desde la fuente oficial."
        ),
        "update.wrong_preset": (
            "Esta version es el perfil {found} pero pediste {wanted}. "
            "Usa --preset {found} o elige la version {wanted}."
        ),
        "update.wrong_chip": (
            "Esta version es para {found}, no para ESP32-S3. Usa la version de StackChan."
        ),
        "update.slot_rule": (
            "La imagen dejaria {free:.1f} por ciento libre en la ranura mas pequena, por "
            "debajo de la regla del {need:d} por ciento. Usa una compilacion mas pequena."
        ),
        "update.no_table": (
            "La version no incluye tabla de particiones, asi que no se puede comprobar la "
            "regla de espacio libre y no se instalo nada. Descarga de nuevo la carpeta completa."
        ),
        "update.slot_ok": (
            "Imagen de {size:,} bytes en una ranura de {slot:,} bytes: {free:.1f} por ciento "
            "libre (regla: al menos {need:d} por ciento)."
        ),
        "update.not_newer": (
            "La unidad tiene {unit} y la version es {release}, asi que no hay nada que "
            "actualizar. Usa stackchan flash para instalar esta version exacta."
        ),
        "update.needs_port": (
            "Indica el puerto serie de la unidad, por ejemplo --port /dev/cu.usbmodem101. "
            "No se instalo nada."
        ),
        "update.no_esptool": (
            "esptool no esta instalado, asi que no se instalo nada. Instalalo con "
            "pip install esptool y ejecuta el comando de nuevo."
        ),
        "update.esptool_failed": (
            "esptool termino con codigo {code}. Revisa el cable y el puerto, pon la unidad "
            "en modo de descarga y ejecuta el comando de nuevo."
        ),
        "update.no_host": (
            "Ningun host respondio en {url}, asi que la unidad no se actualizo por aire. "
            "Inicia el host, o usa stackchan flash --port PUERTO por USB."
        ),
        "update.dry": "Simulacion: se reviso todo, no se instalo nada.",
        "update.ok": "La version {version} (perfil {preset}) paso todas las revisiones.",
        "settings.face": "Cara",
        "settings.face.style": "Estilo de la cara",
        "settings.face.style.classic": "Clasico",
        "settings.face.style.big_eyes": "Ojos grandes",
        "settings.face.style.minimal": "Minimo",
        "settings.face.colour": "Color de la cara",
        "settings.face.colour.none": "Ninguno (blanco)",
        "settings.face.colour.mint": "Menta",
        "settings.face.colour.sky": "Cielo",
        "settings.face.colour.amber": "Ambar",
        "settings.face.colour.rose": "Rosa",
        "settings.face.colour.lilac": "Lila",
        "settings.face.colour.lime": "Lima",
        "settings.face.colour.coral": "Coral",
        "settings.face.captions": "Mostrar subtitulos en la pantalla",
        "settings.face.tod": "Cambiar la cara segun la hora del dia",
        "settings.face.hours": "Inicio de cada tramo (manana, dia, tarde, noche, horas de 0 a 23, por ejemplo 6, 9, 18, 21)",
        "settings.face.unavailable": "El firmware de esta unidad no tiene:",
        "settings.face.pending": "Guardado aqui. La unidad no esta conectada; recibe estos ajustes cuando se reconecte.",
        "settings.face.save": "Guardar cara",
        "settings.face.reset": "Volver a la cara sencilla",
    },
}


def normalize(lang: str | None) -> str:
    """Return a supported language code; unknown or empty values give English."""
    code = (lang or "").strip().lower().replace("_", "-").split("-")[0]
    return code if code in SUPPORTED else DEFAULT


def t(lang: str | None, key: str, **values: object) -> str:
    code = normalize(lang)
    text = CATALOG[code].get(key) or CATALOG[DEFAULT].get(key) or key
    return text.format(**values) if values else text


def catalog(lang: str | None) -> dict[str, str]:
    """Every key for one language, English filling gaps, for the page."""
    merged = dict(CATALOG[DEFAULT])
    merged.update(CATALOG[normalize(lang)])
    return merged
