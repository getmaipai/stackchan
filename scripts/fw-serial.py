#!/usr/bin/env python3
"""Bench helper for the unit on the USB cable (bench builds only; see patch V01 and H01).

  fw-serial.py tool NAME [JSON]        call one tool, print the reply
  fw-serial.py snap OUT.png            dump the screen (self.face.snapshot) to a PNG
  fw-serial.py serve                   hold the port open (opening it resets the unit), log it, answer the commands above

Start `serve` once in the background (it logs everything to fw-serial.log in the temp folder, or MAIPAI_SERIAL_TMP); the other
commands talk to it. MAIPAI_SERIAL_PORT names the port when more than one USB serial device is plugged in.

Intent: the unit has no way to show us its screen, so the bench build writes the frame it draws on the cable and this turns
it into a picture we can open and judge. It opens the port with DTR and RTS low so that opening does not reset the unit.
Placement: Mac that holds the cable (development only). Upstream: none.
"""

from __future__ import annotations

import glob
import json
import os
import struct
import sys
import tempfile
import time
import zlib

# The first USB serial device unless MAIPAI_SERIAL_PORT names one.
PORT = os.environ.get("MAIPAI_SERIAL_PORT") or next(
    iter(sorted(glob.glob("/dev/cu.usbmodem*"))), "/dev/cu.usbmodem"
)


def open_port(port: str = PORT):
    import serial  # pyserial

    s = serial.Serial()
    s.port = port
    s.baudrate = 115200
    s.timeout = 0.2
    s.dtr = False
    s.rts = False
    s.open()
    s.dtr = False
    s.rts = False
    return s


def png_bytes(width: int, height: int, rgb: bytes) -> bytes:
    """A plain RGB PNG from raw 8-bit RGB rows."""
    raw = b"".join(
        b"\x00" + rgb[y * width * 3 : (y + 1) * width * 3] for y in range(height)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def rgb565le_to_rgb(row: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(row) - 1, 2):
        v = row[i] | (row[i + 1] << 8)
        r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
        out += bytes(((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)))
    return bytes(out)


def call(
    s, name: str, args: dict | None = None, wait: float = 20.0, on_line=None
) -> dict:
    """Send '@tool name json' and wait for the '@reply' line. Other lines go to on_line."""
    s.reset_input_buffer()
    line = f"@tool {name} {json.dumps(args or {}, separators=(',', ':'))}\n"
    s.write(line.encode())
    end = time.time() + wait
    buf = b""
    while time.time() < end:
        buf += s.read(4096)
        while b"\n" in buf:
            one, buf = buf.split(b"\n", 1)
            text = one.decode("utf-8", "replace").strip()
            if text.startswith("@reply "):
                reply = json.loads(text[7:])
                result = reply.get("result", reply)
                content = result.get("content") if isinstance(result, dict) else None
                if content and isinstance(content, list) and "text" in content[0]:
                    try:
                        return json.loads(content[0]["text"])
                    except ValueError:
                        return {"text": content[0]["text"]}
                return reply
            if on_line is not None:
                on_line(text)
    raise TimeoutError(f"no reply to {name} in {wait} s")


def snap(s, out: str) -> None:
    rows: dict[int, bytes] = {}
    size = [320, 240]

    def on_line(text: str) -> None:
        if text.startswith("@snapinfo "):
            _, w, h = text.split()
            size[0], size[1] = int(w), int(h)
        elif text.startswith("@snap "):
            _, y, hexdata = text.split(" ", 2)
            rows[int(y)] = bytes.fromhex(hexdata)

    call(s, "self.face.snapshot", wait=60.0, on_line=on_line)
    w, h = size
    if len(rows) != h:
        raise RuntimeError(f"snapshot incomplete: {len(rows)} of {h} rows")
    rgb = b"".join(rgb565le_to_rgb(rows[y]) for y in range(h))
    with open(out, "wb") as f:
        f.write(png_bytes(w, h, rgb))


_TMP = os.environ.get("MAIPAI_SERIAL_TMP") or tempfile.gettempdir()
SOCK = os.path.join(_TMP, "fw-serial.sock")
LOG = os.path.join(_TMP, "fw-serial.log")


def serve(port: str = PORT, sock_path: str = SOCK, log_path: str = LOG) -> None:
    """Hold the port open once (opening it resets the unit), log everything, and answer requests on a unix socket."""
    import os
    import queue
    import socket
    import threading

    s = open_port(port)
    lines: queue.Queue[str] = queue.Queue()
    logf = open(log_path, "ab", buffering=0)  # noqa: SIM115  kept open for the life of the process

    def reader() -> None:
        buf = b""
        while True:
            chunk = s.read(4096)
            if not chunk:
                continue
            logf.write(chunk)
            buf += chunk
            while b"\n" in buf:
                one, buf = buf.split(b"\n", 1)
                lines.put(one.decode("utf-8", "replace").strip())

    threading.Thread(target=reader, daemon=True).start()
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(1)
    while True:
        conn, _ = srv.accept()
        try:
            req = json.loads(conn.makefile().readline())
            while not lines.empty():
                lines.get_nowait()
            s.write(
                f"@tool {req['name']} {json.dumps(req.get('args') or {}, separators=(',', ':'))}\n".encode()
            )
            end = time.time() + float(req.get("wait", 30))
            snaps: list[str] = []
            reply = None
            while time.time() < end and reply is None:
                try:
                    text = lines.get(timeout=0.5)
                except queue.Empty:
                    continue
                if text.startswith("@reply "):
                    reply = text[7:]
                elif text.startswith("@snap"):
                    snaps.append(text)
            conn.sendall((json.dumps({"reply": reply, "snaps": snaps}) + "\n").encode())
        except Exception as error:  # noqa: BLE001  keep serving, also when the client went away
            try:
                conn.sendall(
                    (
                        json.dumps({"reply": None, "error": str(error), "snaps": []})
                        + "\n"
                    ).encode()
                )
            except OSError:
                pass
        finally:
            conn.close()


def ask(
    name: str, args: dict | None = None, wait: float = 30.0
) -> tuple[dict, list[str]]:
    import socket

    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.connect(SOCK)
    c.sendall(
        (json.dumps({"name": name, "args": args or {}, "wait": wait}) + "\n").encode()
    )
    data = b""
    c.settimeout(wait + 15)
    while not data.endswith(b"\n"):
        got = c.recv(1 << 20)
        if not got:
            break
        data += got
    c.close()
    answer = json.loads(data)
    if answer.get("reply") is None:
        raise TimeoutError(f"no reply to {name}: {answer.get('error', 'timed out')}")
    reply = json.loads(answer["reply"])
    result = reply.get("result", reply) if isinstance(reply, dict) else reply
    content = result.get("content") if isinstance(result, dict) else None
    if content and isinstance(content, list) and "text" in content[0]:
        try:
            return json.loads(content[0]["text"]), answer["snaps"]
        except ValueError:
            return {"text": content[0]["text"]}, answer["snaps"]
    return reply, answer["snaps"]


def snaps_to_png(snaps: list[str], out: str) -> None:
    rows: dict[int, bytes] = {}
    w = h = 0
    for text in snaps:
        if text.startswith("@snapinfo "):
            _, w_s, h_s = text.split()
            w, h = int(w_s), int(h_s)
        elif text.startswith("@snap "):
            _, y, hexdata = text.split(" ", 2)
            rows[int(y)] = bytes.fromhex(hexdata)
    if not h or len(rows) != h:
        raise RuntimeError(f"snapshot incomplete: {len(rows)} of {h} rows")
    rgb = b"".join(rgb565le_to_rgb(rows[y]) for y in range(h))
    with open(out, "wb") as f:
        f.write(png_bytes(w, h, rgb))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "serve":
        serve()
        return 0
    if cmd == "tool":
        args = json.loads(argv[3]) if len(argv) > 3 else {}
        print(json.dumps(ask(argv[2], args, 120.0)[0]))
    elif cmd == "snap":
        _, snaps = ask("self.face.snapshot", {}, 90.0)
        snaps_to_png(snaps, argv[2])
        print("wrote", argv[2])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
