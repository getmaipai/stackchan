# ruff: noqa: E501
"""Picture faces: the owner's own pictures as the unit's face (firmware patches H03 and H04).

The owner picks one picture per expression on the settings page (neutral, happy, sad, angry, doubt, sleepy,
speaking). This module resizes each to 320 by 240, turns it into the unit's RGB565, compresses it, keeps the
result in the host's own config folder (never in this repository, and never sent anywhere but the owner's unit
over the paired link), and sends the pack to the unit with the ``self.facepic.*`` tools.

Three modes, the same three the firmware knows:

- ``picture``: one picture per expression;
- ``overlay``: one picture per expression with an animated blink and a mouth that follows the voice drawn over it
  (the owner says where the eyes and the mouth go);
- ``sequence``: up to six frames per expression played in a loop at 1 to 12 frames a second.

The limits and the plain sentences are the firmware's (``maipai_picface_core.h``): a pack that would not fit is
refused here, before anything is sent, with the same words in English and Spanish. The unit keeps the pack in
memory, so ``sync`` sends it again when the unit connects. No picture is shipped with the product.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import struct
import tempfile
import threading
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from maipai_body.hal.errors import BodyLost

logger = logging.getLogger("maipai_body.picture_faces")

WIDTH, HEIGHT = 320, 240
FRAME_BYTES = WIDTH * HEIGHT * 2
SLOTS = ("neutral", "happy", "sad", "angry", "doubt", "sleepy", "speaking")
MODES = ("picture", "overlay", "sequence")
MAX_STORE_BYTES = 1_000_000
MAX_FRAMES = 14
MAX_FRAMES_PER_SLOT = 6
MIN_FPS, MAX_FPS, DEFAULT_FPS = 1, 12, 6
CHUNK_BYTES = 2048  # raw bytes per self.facepic.data call (about 2.7 KB as base64)
MAX_SOURCE_PIXELS = 12_000_000  # a page upload larger than this is refused before it fills memory
THUMB = (80, 60)

OVERLAY_KEYS = ("lx", "ly", "rx", "ry", "eye_w", "eye_h", "mx", "my", "mouth_w", "mouth_h")
DEFAULT_OVERLAY: dict[str, Any] = {
    "lx": 112, "ly": 100, "rx": 208, "ry": 100, "eye_w": 28, "eye_h": 36,
    "mx": 160, "my": 170, "mouth_w": 70, "mouth_h": 40, "color": "#141414",
}  # fmt: skip

# The firmware's sentences by error code (maipai_picface_core.h), plus the ones only the host can say.
_SAY: dict[str, tuple[str, str]] = {
    "mode": (
        "That picture mode is not known. Choose picture, overlay or sequence.",
        "No conozco ese modo de imagen. Elige imagen, superposición o secuencia.",
    ),
    "slot": (
        "That expression is not known. Use neutral, happy, sad, angry, doubt, sleepy or speaking.",
        "No conozco esa expresión. Usa neutral, happy, sad, angry, doubt, sleepy o speaking.",
    ),
    "index": (
        "That frame number is not allowed for this mode. Send one picture per expression, or switch to sequence for up to 6.",
        "Ese número de cuadro no está permitido en este modo. Envía una imagen por expresión, o cambia a secuencia para hasta 6.",
    ),
    "fps": (
        "The frame rate must be from 1 to 12 frames a second. Choose a number in that range.",
        "La velocidad debe ser de 1 a 12 cuadros por segundo. Elige un número en ese rango.",
    ),
    "overlay": (
        "The eye and mouth places are not valid. Keep them on the picture and make each at least 4 pixels wide.",
        "Los lugares de ojos y boca no son válidos. Mantenlos dentro de la imagen y de al menos 4 píxeles de ancho.",
    ),
    "too_many_frames": (
        "That is too many frames. A pack holds at most 14 frames and 6 for each expression. Remove some and send again.",
        "Son demasiados cuadros. Un paquete lleva como máximo 14 cuadros y 6 por expresión. Quita algunos y envía de nuevo.",
    ),
    "too_big": (
        "The pictures are too big for the robot to keep. Use fewer or simpler pictures, or fewer frames, and send again.",
        "Las imágenes son demasiado grandes para que el robot las guarde. Usa menos imágenes, más simples, o menos cuadros, y envía de nuevo.",
    ),
    "frame_size": (
        "That picture is too large. Resize it to 320 by 240 and send again.",
        "Esa imagen es demasiado grande. Ajústala a 320 por 240 y envía de nuevo.",
    ),
    "order": (
        "The picture pieces arrived out of order. Send the pack again from the start.",
        "Las partes de la imagen llegaron desordenadas. Envía el paquete de nuevo desde el principio.",
    ),
    "crc": (
        "A picture was damaged on the way. Send the pack again.",
        "Una imagen se dañó en el camino. Envía el paquete de nuevo.",
    ),
    "no_neutral": (
        "The pack needs a neutral picture first. Add one and send again.",
        "El paquete necesita primero una imagen neutral. Agrega una y envía de nuevo.",
    ),
    "missing": (
        "An expression of the pack has no picture yet. Send every picture, then finish.",
        "A una expresión del paquete le falta la imagen. Envía todas las imágenes y luego termina.",
    ),
    "decode": (
        "The robot could not open one of the pictures. Send the pack again, or use a simpler picture.",
        "El robot no pudo abrir una de las imágenes. Envía el paquete de nuevo, o usa una imagen más simple.",
    ),
    "memory": (
        "The robot has no room for the pictures right now. Remove the pack or restart the robot, then send again.",
        "El robot no tiene espacio para las imágenes ahora. Quita el paquete o reinicia el robot y envía de nuevo.",
    ),
    "not_started": (
        "No picture pack is being sent. Start a new pack first.",
        "No se está enviando ningún paquete de imágenes. Empieza un paquete nuevo.",
    ),
    # host only
    "no_unit": (
        "Choose a unit first, then add pictures.",
        "Elige primero una unidad y luego agrega imágenes.",
    ),
    "bad_picture": (
        "That picture could not be read. Choose a PNG or JPEG picture, or a picture the page can open.",
        "No se pudo leer esa imagen. Elige una imagen PNG o JPEG, o una que la página pueda abrir.",
    ),
    "picture_huge": (
        "That picture is very large. Choose one under 25 million pixels.",
        "Esa imagen es muy grande. Elige una de menos de 25 millones de píxeles.",
    ),
    "nothing": (
        "There are no pictures yet. Add a neutral picture first.",
        "Todavía no hay imágenes. Agrega primero una imagen neutral.",
    ),
    "offline": (
        "The unit is not connected. The pictures are saved and go to the unit when it connects.",
        "La unidad no está conectada. Las imágenes quedan guardadas y se envían cuando se conecte.",
    ),
    "old_firmware": (
        "This unit's software has no picture faces. Update the unit, then send the pictures.",
        "El software de esta unidad no tiene caras con imágenes. Actualiza la unidad y envía las imágenes.",
    ),
    "sent": (
        "The pictures are on the unit.",
        "Las imágenes están en la unidad.",
    ),
    "removed": (
        "The picture face is removed from the unit. The drawn face is back.",
        "La cara con imágenes se quitó de la unidad. Volvió la cara dibujada.",
    ),
}


def say(lang: str | None, code: str) -> str:
    """One sentence in English or Spanish (every other language reads English)."""
    en, es = _SAY.get(code, (code, code))
    return es if (lang or "").lower().startswith("es") else en


class PictureError(Exception):
    """A plain sentence for the person on the settings page. ``code`` is the firmware's error code."""

    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        self.code = code


# ---- pictures: resize, color, compression -------------------------------------------------------------


def resize_rgba(data: bytes, width: int, height: int, fit: str = "cover") -> np.ndarray:
    """Any RGBA picture to 320 by 240 (uint8, 240 x 320 x 4). ``cover`` fills the screen and crops the overflow
    from the middle; ``contain`` keeps the whole picture and fills the rest with black.
    """
    if width < 1 or height < 1 or len(data) != width * height * 4:
        raise PictureError(say(None, "bad_picture"), "bad_picture")
    if width * height > MAX_SOURCE_PIXELS:
        raise PictureError(say(None, "picture_huge"), "picture_huge")
    src = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 4)
    # Box-halve while the source is more than twice the size wanted, so a large photo does not alias.
    # The halving runs in bands of rows so the full picture is never held as float32 at once.
    while src.shape[0] >= 2 * HEIGHT and src.shape[1] >= 2 * WIDTH:
        h2, w2 = src.shape[0] // 2 * 2, src.shape[1] // 2 * 2
        halved = np.empty((h2 // 2, w2 // 2, 4), dtype=np.float32)
        for top in range(0, h2, 256):
            s = src[top : min(top + 256, h2), :w2].astype(np.float32)
            halved[top // 2 : min(top + 256, h2) // 2] = (
                s[0::2, 0::2] + s[1::2, 0::2] + s[0::2, 1::2] + s[1::2, 1::2]
            ) / 4.0
        src = halved
    src = src.astype(np.float32, copy=False)
    sh, sw = src.shape[:2]
    scale = max(WIDTH / sw, HEIGHT / sh) if fit == "cover" else min(WIDTH / sw, HEIGHT / sh)
    new_w, new_h = max(1, round(sw * scale)), max(1, round(sh * scale))
    ys = np.clip((np.arange(new_h) + 0.5) / scale - 0.5, 0, sh - 1)
    xs = np.clip((np.arange(new_w) + 0.5) / scale - 0.5, 0, sw - 1)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    y1, x1 = np.minimum(y0 + 1, sh - 1), np.minimum(x0 + 1, sw - 1)
    wy, wx = (ys - y0)[:, None, None], (xs - x0)[None, :, None]
    top = src[y0][:, x0] * (1 - wx) + src[y0][:, x1] * wx
    bottom = src[y1][:, x0] * (1 - wx) + src[y1][:, x1] * wx
    scaled = top * (1 - wy) + bottom * wy
    out = np.zeros((HEIGHT, WIDTH, 4), dtype=np.float32)
    out[..., 3] = 255.0
    if fit == "cover":
        ox, oy = (new_w - WIDTH) // 2, (new_h - HEIGHT) // 2
        out[:] = scaled[oy : oy + HEIGHT, ox : ox + WIDTH]
    else:
        ox, oy = (WIDTH - new_w) // 2, (HEIGHT - new_h) // 2
        out[oy : oy + new_h, ox : ox + new_w] = scaled
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def to_rgb565(rgba: np.ndarray) -> bytes:
    """320 by 240 RGBA to the unit's RGB565, little endian, a transparent pixel counting as black."""
    if rgba.shape != (HEIGHT, WIDTH, 4):
        raise PictureError(say(None, "frame_size"), "frame_size")
    a = rgba[..., 3].astype(np.uint16)
    r = (rgba[..., 0].astype(np.uint16) * a + 127) // 255
    g = (rgba[..., 1].astype(np.uint16) * a + 127) // 255
    b = (rgba[..., 2].astype(np.uint16) * a + 127) // 255
    packed = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    return packed.astype("<u2").tobytes()


def from_rgb565(raw: bytes) -> np.ndarray:
    """RGB565 back to 8-bit RGB (240 x 320 x 3), for the page's thumbnails and for tests."""
    v = np.frombuffer(raw, dtype="<u2").reshape(HEIGHT, WIDTH).astype(np.uint16)
    r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return np.stack(
        [(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], axis=-1
    ).astype(np.uint8)


@dataclass(frozen=True)
class Encoded:
    payload: bytes
    raw: bool  # True: the payload is the 153,600 raw bytes (zlib would not have been smaller)
    crc: int

    @property
    def size(self) -> int:
        return len(self.payload)


def encode_frame(rgb565: bytes) -> Encoded:
    if len(rgb565) != FRAME_BYTES:
        raise PictureError(say(None, "frame_size"), "frame_size")
    packed = zlib.compress(rgb565, 9)
    if len(packed) >= FRAME_BYTES:
        return Encoded(rgb565, True, zlib.crc32(rgb565) & 0xFFFFFFFF)
    return Encoded(packed, False, zlib.crc32(packed) & 0xFFFFFFFF)


def decode_frame(frame: Encoded) -> bytes:
    return frame.payload if frame.raw else zlib.decompress(frame.payload)


def png_data_uri(rgb: np.ndarray) -> str:
    """A small PNG as a data: URI (for the thumbnails; no image library needed)."""
    h, w = rgb.shape[:2]
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return (
            struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def thumbnail(rgb565: bytes) -> str:
    rgb = from_rgb565(rgb565)
    small = rgb.reshape(THUMB[1], HEIGHT // THUMB[1], THUMB[0], WIDTH // THUMB[0], 3).mean(
        axis=(1, 3)
    )
    return png_data_uri(small.astype(np.uint8))


# ---- the pack ------------------------------------------------------------------------------------------


@dataclass
class PictureSet:
    mode: str = "picture"
    fps: int = DEFAULT_FPS
    overlay: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_OVERLAY))
    frames: dict[str, list[Encoded]] = field(default_factory=dict)  # slot -> frames in order

    def total_frames(self) -> int:
        return sum(len(v) for v in self.frames.values())

    def total_bytes(self) -> int:
        return sum(f.size for v in self.frames.values() for f in v)


def check_overlay(overlay: dict[str, Any]) -> dict[str, Any]:
    """The overlay places with the firmware's rules; returns a clean copy or raises."""
    clean: dict[str, Any] = dict(DEFAULT_OVERLAY)
    for key in OVERLAY_KEYS:
        if key in overlay:
            value = overlay[key]
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise PictureError(say(None, "overlay"), "overlay")
            clean[key] = int(value)
    color = overlay.get("color", clean["color"])
    if not isinstance(color, str) or len(color) != 7 or color[0] != "#":
        raise PictureError(say(None, "overlay"), "overlay")
    try:
        int(color[1:], 16)
    except ValueError:
        raise PictureError(say(None, "overlay"), "overlay") from None
    clean["color"] = color.lower()
    c = clean
    sizes_ok = (
        4 <= c["eye_w"] <= 160
        and 4 <= c["eye_h"] <= 160
        and 4 <= c["mouth_w"] <= 200
        and 4 <= c["mouth_h"] <= 120
    )
    in_x = all(0 <= c[k] < WIDTH for k in ("lx", "rx", "mx"))
    in_y = all(0 <= c[k] < HEIGHT for k in ("ly", "ry", "my"))
    if not (sizes_ok and in_x and in_y):
        raise PictureError(say(None, "overlay"), "overlay")
    return clean


def check_set(pictures: PictureSet) -> str | None:
    """None when the pack fits, else the firmware's error code. The same rules as ``pf_admit`` and ``pf_complete``."""
    if pictures.mode not in MODES:
        return "mode"
    if not MIN_FPS <= pictures.fps <= MAX_FPS:
        return "fps"
    limit = MAX_FRAMES_PER_SLOT if pictures.mode == "sequence" else 1
    for slot, frames in pictures.frames.items():
        if slot not in SLOTS:
            return "slot"
        if len(frames) > limit:
            return "index"
        if any(f.size == 0 or f.size > FRAME_BYTES for f in frames):
            return "frame_size"
    if pictures.total_frames() > MAX_FRAMES:
        return "too_many_frames"
    if pictures.total_bytes() > MAX_STORE_BYTES:
        return "too_big"
    if not pictures.frames.get("neutral"):
        return "no_neutral"
    return None


# ---- the store: one folder per unit, in the host's own config folder -----------------------------------


def default_root() -> Path:
    return Path.home() / ".config" / "maipai" / "stackchan-pictures"


def _safe_unit(unit_id: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in unit_id)
    if not cleaned or cleaned.startswith("."):
        raise PictureError(say(None, "no_unit"), "no_unit")
    return cleaned


class PictureStore:
    """The owner's pictures per unit: ``<root>/<unit>/pack.json`` and one compressed file per frame."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else default_root()
        self._lock = threading.Lock()

    def _dir(self, unit_id: str) -> Path:
        return self.root / _safe_unit(unit_id)

    def load(self, unit_id: str) -> PictureSet:
        with self._lock:
            folder = self._dir(unit_id)
            try:
                meta = json.loads((folder / "pack.json").read_text())
            except (FileNotFoundError, ValueError, OSError):
                return PictureSet()
            pictures = PictureSet()
            if meta.get("mode") in MODES:
                pictures.mode = meta["mode"]
            if isinstance(meta.get("fps"), int) and MIN_FPS <= meta["fps"] <= MAX_FPS:
                pictures.fps = meta["fps"]
            try:
                pictures.overlay = check_overlay(meta.get("overlay") or {})
            except PictureError:
                pictures.overlay = dict(DEFAULT_OVERLAY)
            for slot in SLOTS:
                frames: list[Encoded] = []
                for index in range(MAX_FRAMES_PER_SLOT):
                    path = folder / f"{slot}-{index}.bin"
                    try:
                        blob = path.read_bytes()
                    except OSError:
                        break
                    if len(blob) < 5:
                        break
                    raw = blob[0] == 0
                    payload = blob[1:]
                    frames.append(Encoded(payload, raw, zlib.crc32(payload) & 0xFFFFFFFF))
                if frames:
                    pictures.frames[slot] = frames
            return pictures

    def save(self, unit_id: str, pictures: PictureSet) -> None:
        with self._lock:
            folder = self._dir(unit_id)
            folder.mkdir(parents=True, exist_ok=True)
            os.chmod(folder, 0o700)
            wanted = set()
            for slot, frames in pictures.frames.items():
                for index, frame in enumerate(frames):
                    name = f"{slot}-{index}.bin"
                    wanted.add(name)
                    self._write(folder / name, (b"\x00" if frame.raw else b"\x01") + frame.payload)
            for stale in folder.glob("*-*.bin"):
                if stale.name not in wanted:
                    stale.unlink(missing_ok=True)
            meta = {"mode": pictures.mode, "fps": pictures.fps, "overlay": pictures.overlay}
            self._write(folder / "pack.json", json.dumps(meta).encode())

    def clear(self, unit_id: str) -> None:
        with self._lock:
            folder = self._dir(unit_id)
            for path in list(folder.glob("*-*.bin")) + [folder / "pack.json"]:
                path.unlink(missing_ok=True)

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise


# ---- the service: edit, check and send -----------------------------------------------------------------


def _unwrap(reply: object) -> dict[str, Any]:
    """The tool's answer as a dict, whatever the link wrapped it in."""
    if isinstance(reply, dict):
        text = reply.get("text") if "ok" not in reply else None
        if isinstance(text, str):
            try:
                return json.loads(text)
            except ValueError:
                return {"ok": False, "error": text}
        return reply
    if isinstance(reply, str):
        try:
            return json.loads(reply)
        except ValueError:
            return {"ok": False, "error": reply}
    if isinstance(reply, bool):
        return {"ok": reply}
    return {"ok": False, "error": "no answer"}


class PictureService:
    """Edits one unit's pictures and sends them. ``call`` is the voice server's ``call_device_tool``."""

    def __init__(
        self,
        call: Callable[..., object],
        store: PictureStore | None = None,
        *,
        timeout: float = 8.0,
        chunk: int = CHUNK_BYTES,
        progress: Callable[[str, int, int], None] | None = None,
    ) -> None:
        self._call = call
        self.store = store if store is not None else PictureStore()
        self._timeout = timeout
        self._chunk = chunk
        self._progress = progress
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    def _tool(
        self, unit_id: str, name: str, arguments: dict[str, Any], timeout: float | None = None
    ) -> dict[str, Any]:
        return _unwrap(
            self._call(name, arguments, device_id=unit_id, timeout=timeout or self._timeout)
        )

    # ---- editing ----

    def add_picture(
        self,
        unit_id: str,
        slot: str,
        index: int,
        width: int,
        height: int,
        rgba: bytes,
        lang: str | None = None,
    ) -> dict[str, Any]:
        """Resize and keep one picture (slot, frame number). Refuses with the firmware's sentence when it would not fit."""
        if slot not in SLOTS:
            raise PictureError(say(lang, "slot"), "slot")
        pictures = self.store.load(unit_id)
        limit = MAX_FRAMES_PER_SLOT if pictures.mode == "sequence" else 1
        frames = pictures.frames.setdefault(slot, [])
        if not 0 <= index < limit or index > len(frames):
            raise PictureError(say(lang, "index"), "index")
        try:
            encoded = encode_frame(to_rgb565(resize_rgba(rgba, width, height)))
        except PictureError as error:
            raise PictureError(say(lang, error.code or "bad_picture"), error.code) from None
        if index == len(frames):
            frames.append(encoded)
        else:
            frames[index] = encoded
        problem = check_set(
            PictureSet(
                pictures.mode,
                pictures.fps,
                pictures.overlay,
                {s: v for s, v in pictures.frames.items() if v},
            )
        )
        if problem and problem != "no_neutral":
            raise PictureError(say(lang, problem), problem)
        self.store.save(unit_id, pictures)
        return self.view(unit_id, lang)

    def remove_picture(
        self, unit_id: str, slot: str, index: int | None = None, lang: str | None = None
    ) -> dict[str, Any]:
        pictures = self.store.load(unit_id)
        if slot not in SLOTS:
            raise PictureError(say(lang, "slot"), "slot")
        frames = pictures.frames.get(slot, [])
        if index is None:
            frames = []
        elif 0 <= index < len(frames):
            del frames[index]
        pictures.frames[slot] = frames
        pictures.frames = {s: v for s, v in pictures.frames.items() if v}
        self.store.save(unit_id, pictures)
        return self.view(unit_id, lang)

    def set_options(
        self,
        unit_id: str,
        mode: str | None = None,
        fps: int | None = None,
        overlay: dict[str, Any] | None = None,
        lang: str | None = None,
    ) -> dict[str, Any]:
        pictures = self.store.load(unit_id)
        if mode is not None:
            if mode not in MODES:
                raise PictureError(say(lang, "mode"), "mode")
            pictures.mode = mode
            if mode != "sequence":  # the other modes hold one picture per expression
                pictures.frames = {s: v[:1] for s, v in pictures.frames.items() if v}
        if fps is not None:
            if isinstance(fps, bool) or not isinstance(fps, int) or not MIN_FPS <= fps <= MAX_FPS:
                raise PictureError(say(lang, "fps"), "fps")
            pictures.fps = fps
        if overlay is not None:
            try:
                pictures.overlay = check_overlay(overlay)
            except PictureError:
                raise PictureError(say(lang, "overlay"), "overlay") from None
        self.store.save(unit_id, pictures)
        return self.view(unit_id, lang)

    def clear_all(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """Forget every picture on the host and take the pack off the unit (the drawn face comes back)."""
        self.store.clear(unit_id)
        with self._lock:
            self._pending.discard(unit_id)
        try:
            self._tool(unit_id, "self.facepic.clear", {})
        except BodyLost:
            pass
        return {**self.view(unit_id, lang), "message": say(lang, "removed")}

    # ---- reading ----

    def view(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        pictures = self.store.load(unit_id)
        problem = check_set(pictures) if pictures.frames else None
        slots = []
        for slot in SLOTS:
            frames = pictures.frames.get(slot, [])
            slots.append({
                "slot": slot,
                "frames": len(frames),
                "bytes": sum(f.size for f in frames),
                "thumbs": [thumbnail(decode_frame(f)) for f in frames],
            })  # fmt: skip
        with self._lock:
            pending = unit_id in self._pending
        return {
            "ok": True,
            "mode": pictures.mode,
            "fps": pictures.fps,
            "overlay": pictures.overlay,
            "slots": slots,
            "bytes": pictures.total_bytes(),
            "frames": pictures.total_frames(),
            "limits": {
                "bytes": MAX_STORE_BYTES,
                "frames": MAX_FRAMES,
                "per_slot": MAX_FRAMES_PER_SLOT if pictures.mode == "sequence" else 1,
                "fps": [MIN_FPS, MAX_FPS],
                "width": WIDTH,
                "height": HEIGHT,
            },  # fmt: skip
            "choices": {"mode": list(MODES), "slots": list(SLOTS)},
            "ready": problem is None and bool(pictures.frames),
            "problem": say(lang, problem) if problem and problem != "no_neutral" else "",
            "pending": pending,
        }

    # ---- sending ----

    def send(self, unit_id: str, lang: str | None = None) -> dict[str, Any]:
        """Send the saved pack to the unit. A unit that is not connected is not an error: ``sync`` sends it later."""
        pictures = self.store.load(unit_id)
        if not pictures.frames:
            raise PictureError(say(lang, "nothing"), "nothing")
        problem = check_set(pictures)
        if problem:
            raise PictureError(say(lang, problem), problem)
        try:
            self._push(unit_id, pictures, lang)
        except BodyLost:
            with self._lock:
                self._pending.add(unit_id)
            return {"ok": True, "sent": False, "message": say(lang, "offline")}
        with self._lock:
            self._pending.discard(unit_id)
        return {
            "ok": True,
            "sent": True,
            "message": say(lang, "sent"),
            "bytes": pictures.total_bytes(),
            "frames": pictures.total_frames(),
        }

    def _fail(self, reply: dict[str, Any], lang: str | None) -> PictureError:
        code = str(reply.get("code", ""))
        if code in _SAY:
            return PictureError(say(lang, code), code)
        text = str(reply.get("error", ""))
        if "Unknown tool" in text:
            return PictureError(say(lang, "old_firmware"), "old_firmware")
        return PictureError(text or say(lang, "decode"), code)

    def _push(self, unit_id: str, pictures: PictureSet, lang: str | None) -> None:
        reply = self._tool(
            unit_id,
            "self.facepic.begin",
            {
                "mode": pictures.mode,
                "fps": pictures.fps,
                "overlay": json.dumps(pictures.overlay) if pictures.mode == "overlay" else "",
            },
        )
        if reply.get("ok") is not True:
            raise self._fail(reply, lang)
        total = pictures.total_bytes()
        done = 0
        for slot in SLOTS:
            for index, frame in enumerate(pictures.frames.get(slot, [])):
                reply = self._tool(
                    unit_id,
                    "self.facepic.frame",
                    {
                        "slot": slot,
                        "index": index,
                        "bytes": frame.size,
                        "crc": f"{frame.crc:08x}",
                        "raw": frame.raw,
                    },
                )
                if reply.get("ok") is not True:
                    raise self._fail(reply, lang)
                for at in range(0, frame.size, self._chunk):
                    piece = frame.payload[at : at + self._chunk]
                    reply = self._tool(
                        unit_id,
                        "self.facepic.data",
                        {
                            "slot": slot,
                            "index": index,
                            "at": at,
                            "b64": base64.b64encode(piece).decode("ascii"),
                        },
                    )
                    if reply.get("ok") is not True:
                        raise self._fail(reply, lang)
                    done += len(piece)
                    if self._progress is not None:
                        self._progress(unit_id, done, total)
        reply = self._tool(unit_id, "self.facepic.commit", {}, timeout=15.0)
        if reply.get("ok") is not True:
            raise self._fail(reply, lang)

    def sync(self, unit_id: str) -> None:
        """When a unit connects: send the owner's pictures if the unit does not hold the same pack."""
        pictures = self.store.load(unit_id)
        if not pictures.frames or check_set(pictures):
            return
        try:
            reply = self._tool(unit_id, "self.facepic.status", {})
            if (
                reply.get("ok") is True
                and reply.get("held") is True
                and reply.get("showing") is not None
                and reply.get("bytes") == pictures.total_bytes()
                and reply.get("mode") == pictures.mode
                and reply.get("frames") == pictures.total_frames()
            ):
                return
            if reply.get("ok") is not True:
                return  # a unit without picture faces: nothing to send
            self._push(unit_id, pictures, None)
            with self._lock:
                self._pending.discard(unit_id)
        except (BodyLost, PictureError, OSError, TimeoutError):
            logger.debug("pictures not sent to unit %s", unit_id[-5:], exc_info=True)


def sync_on_connect(service: PictureService, unit_id: str) -> None:
    """Session listener: send the owner's pictures when a unit connects, never raising."""
    try:
        service.sync(unit_id)
    except Exception:
        logger.warning(
            "could not send the picture face to unit %s; it goes out when it reconnects",
            unit_id[-5:],
            exc_info=True,
        )
