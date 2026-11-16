#!/usr/bin/env python3
"""Bench: send made-up pictures to the unit over the USB cable and look at what its face draws (bench builds only).

  fw-pictures.py push MODE [--noise N]      build a pack of generated cartoon pictures and send it
  fw-pictures.py shots MODE OUT_DIR         force each expression and save the screen as a PNG (needs a pack on the unit)
  fw-pictures.py seqshots OUT_DIR           save four screens of a playing sequence (needs a sequence pack on the unit)
  fw-pictures.py talkshot OUT.png LEVEL     hold the speaking look with a steady speech level and save the screen
  fw-pictures.py clear                      take the pack off the unit

Intent: the pictures are drawn here from plain shapes (a round cartoon mascot): no person, no photograph, nothing from
the owner. They go through the same host code as a real upload (picture_faces.py), so this also proves the transport,
the unit's refusal sentences and its decode. `fw-serial.py serve` must be running.
Placement: Mac that holds the cable (development only). Upstream: none.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "host"))
sys.path.insert(0, str(ROOT))

import importlib.util

from maipai_body import picture_faces as pf

_spec = importlib.util.spec_from_file_location("fw_serial", ROOT / "fw-serial.py")
fw_serial = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(fw_serial)  # type: ignore[union-attr]

BACKGROUND = {
    "neutral": (60, 96, 150), "happy": (236, 176, 64), "sad": (70, 84, 128), "angry": (176, 56, 52),
    "doubt": (96, 128, 96), "sleepy": (60, 52, 104), "speaking": (60, 148, 136),
}  # fmt: skip


def art(expression: str, with_face: bool, frame: int = 0, noise: float = 3.0) -> bytes:
    """A 320 by 240 RGBA cartoon mascot. with_face False leaves the eyes and mouth off (for overlay mode)."""
    yy, xx = np.mgrid[0:240, 0:320].astype(np.float32)
    bg = np.array(BACKGROUND[expression], dtype=np.float32)
    img = np.empty((240, 320, 3), dtype=np.float32)
    img[:] = bg * (0.75 + 0.25 * (yy / 240.0))[..., None]
    cy = 128 + (6 if frame % 2 else -6) * (1 if frame else 0)
    body = ((xx - 160) / 108) ** 2 + ((yy - cy) / 98) ** 2 <= 1.0
    skin = np.array((244, 214, 168), dtype=np.float32)
    shade = 1.0 - 0.18 * (((xx - 150) / 108) ** 2 + ((yy - cy + 10) / 98) ** 2)
    img[body] = (skin * np.clip(shade, 0.7, 1.0)[..., None])[body]
    for cx in (84, 236):  # cheeks
        cheek = ((xx - cx) / 22) ** 2 + ((yy - (cy + 36)) / 14) ** 2 <= 1.0
        img[cheek] = (
            img[cheek] * 0.8 + np.array((240, 120, 120), dtype=np.float32) * 0.2
        )
    # brows say the expression even when the eyes are left to the overlay
    brow = np.zeros_like(body)
    for side, cx in ((-1, 112), (1, 208)):
        tilt = {
            "angry": -side * 0.45,
            "sad": side * 0.4,
            "happy": 0.0,
            "doubt": (0.0 if side < 0 else -0.5),
            "sleepy": 0.0,
        }.get(expression, 0.0)
        rise = {"happy": -8, "doubt": (0 if side < 0 else -16), "sleepy": 10}.get(
            expression, 0
        )
        line = np.abs((yy - (cy - 56 + rise)) - tilt * (xx - cx)) <= 4
        brow |= line & (np.abs(xx - cx) <= 28)
    img[brow] = (70, 44, 30)
    if with_face:
        shut = expression == "sleepy"
        for cx in (112, 208):
            eye_h = 4 if shut else 18
            eye = ((xx - cx) / 14) ** 2 + ((yy - (cy - 28)) / eye_h) ** 2 <= 1.0
            img[eye] = (24, 24, 30)
        if expression in ("happy", "speaking"):
            ry = 22 if expression == "speaking" else 12
            mouth = ((xx - 160) / 34) ** 2 + ((yy - (cy + 40)) / ry) ** 2 <= 1.0
            img[mouth] = (120, 30, 40)
        elif expression == "sad":
            m = (np.abs((yy - (cy + 46)) - 0.012 * (xx - 160) ** 2) <= 3) & (
                np.abs(xx - 160) <= 36
            )  # ends lower: a frown
            img[m] = (90, 30, 40)
        else:
            m = (np.abs(yy - (cy + 46)) <= 3) & (np.abs(xx - 160) <= 30)
            img[m] = (90, 30, 40)
    rng = np.random.default_rng(7 + frame)
    img += rng.normal(0, noise, img.shape)
    out = np.empty((240, 320, 4), dtype=np.uint8)
    out[..., :3] = np.clip(img, 0, 255).astype(np.uint8)
    out[..., 3] = 255
    return out.tobytes()


def make_service() -> pf.PictureService:
    def call(name, arguments, device_id=None, timeout=None):
        reply, _ = fw_serial.ask(name, arguments, wait=float(timeout or 30))
        return reply

    store = pf.PictureStore(Path(tempfile.mkdtemp(prefix="pf-bench-")))
    return pf.PictureService(call, store, timeout=30.0, progress=_show)


_last = [0.0]


def _show(_unit: str, done: int, total: int) -> None:
    if time.time() - _last[0] > 2.0:
        _last[0] = time.time()
        print(f"  sent {done} of {total} bytes", flush=True)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "clear":
        print(fw_serial.ask("self.facepic.clear", {})[0])
        return 0
    if cmd == "seqshots":
        out = Path(argv[2])
        out.mkdir(parents=True, exist_ok=True)
        fw_serial.ask(
            "self.facepic.bench_force",
            {"slot": "neutral", "seconds": 120, "ignore_privacy": True},
        )
        for n in range(4):
            _, snaps = fw_serial.ask("self.face.snapshot", {}, wait=90.0)
            fw_serial.snaps_to_png(snaps, str(out / f"sequence-{n}.png"))
            print("wrote", out / f"sequence-{n}.png")
        fw_serial.ask(
            "self.facepic.bench_force",
            {"slot": "neutral", "seconds": 0, "ignore_privacy": True},
        )
        return 0
    if cmd == "talkshot":
        fw_serial.ask(
            "self.facepic.bench_force",
            {"slot": "speaking", "seconds": 60, "ignore_privacy": True},
        )
        fw_serial.ask("self.face.bench_speak", {"level": int(argv[3]), "seconds": 12})
        time.sleep(1.5)
        _, snaps = fw_serial.ask("self.face.snapshot", {}, wait=90.0)
        fw_serial.snaps_to_png(snaps, argv[2])
        print("wrote", argv[2])
        fw_serial.ask(
            "self.facepic.bench_force",
            {"slot": "neutral", "seconds": 0, "ignore_privacy": True},
        )
        return 0
    mode = argv[2] if len(argv) > 2 else "picture"
    if cmd == "push":
        noise = float(argv[argv.index("--noise") + 1]) if "--noise" in argv else 3.0
        service = make_service()
        unit = "bench-unit"
        service.set_options(
            unit, mode=mode, fps=6, overlay=dict(pf.DEFAULT_OVERLAY) | {"mouth_h": 34}
        )
        with_face = mode != "overlay"
        for slot in pf.SLOTS:
            frames = 4 if (mode == "sequence" and slot in ("neutral", "happy")) else 1
            for index in range(frames):
                service.add_picture(
                    unit, slot, index, 320, 240, art(slot, with_face, index, noise)
                )
        view = service.view(unit)
        print(
            f"pack: {view['frames']} frames, {view['bytes']} bytes, ready {view['ready']}"
        )
        t0 = time.time()
        result = service.send(unit)
        print(result, f"in {time.time() - t0:.1f} s")
        print(fw_serial.ask("self.facepic.status", {})[0])
    elif cmd == "shots":
        out = Path(argv[3])
        out.mkdir(parents=True, exist_ok=True)
        for slot in pf.SLOTS:
            fw_serial.ask(
                "self.facepic.bench_force",
                {"slot": slot, "seconds": 60, "ignore_privacy": True},
            )
            time.sleep(1.2)  # decode, then the cross-fade
            _, snaps = fw_serial.ask("self.face.snapshot", {}, wait=90.0)
            fw_serial.snaps_to_png(snaps, str(out / f"{mode}-{slot}.png"))
            print("wrote", out / f"{mode}-{slot}.png")
        fw_serial.ask(
            "self.facepic.bench_force",
            {"slot": "neutral", "seconds": 0, "ignore_privacy": True},
        )
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
