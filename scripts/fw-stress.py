#!/usr/bin/env python3
"""Memory gate stress run for the unit on the USB cable, with the memory line on.

  fw-stress.py SECONDS [LOG]     reset the unit, log the serial console, drive it through the host, print the gate numbers

Intent: one scripted run, the same every time, that exercises the paths a bare idle run skips (sound decode, listen cues,
lights, every screen overlay, CRT, a game, head moves, a dance, status reads) and then reads the gate numbers off the
log: internal_free steady, internal_min, int_big (steady and lowest), the fragmentation ratio int_big / internal_free,
the lowest free stack of every task, resets, task watchdog fires, panics and host websocket drops.
Placement: Mac that holds the cable (development only). Needs the host on 127.0.0.1:9782 and the unit paired to it.
Upstream: none.
"""

from __future__ import annotations

import glob
import json
import os
import re
import statistics
import sys
import threading
import time
import urllib.request

HOST = os.environ.get("MAIPAI_HOST_URL", "http://127.0.0.1:9782")
PORT = os.environ.get("MAIPAI_SERIAL_PORT") or next(iter(sorted(glob.glob("/dev/cu.usbmodem*"))), "")
HOST_LOG = os.environ.get("MAIPAI_HOST_LOG", os.path.expanduser("~/stackchan-models/newhost.log"))

# Gate floors (docs/design/memory-headroom-2026-11-16.md).
FLOORS = {"internal_free_steady": 40000, "internal_min": 24000, "int_big_steady": 24000, "int_big_min": 16000,
          "frag_ratio": 0.5, "stack_margin": 1024}

OVERLAYS = ["rain", "snow", "sun", "clouds", "wind", "thunder", "fog", "stars", "disco", "confetti", "fireworks", "hearts",
            "steam", "balloons", "leaves", "zzz", "stormy", "rainy", "snowy", "sunny", "windy", "night", "party", "celebrate", "love",
            "sleeping"]


def call(device: str, path: str, body: dict | None = None, timeout: float = 20.0):
    req = urllib.request.Request(f"{HOST}/api/stackchan/unit/{device}/{path}", data=json.dumps(body or {}).encode(),
                                 headers={"content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except Exception as exc:  # the run goes on; the summary shows the unit's own log
        return str(exc)[:60]


def default_device() -> str:
    with urllib.request.urlopen(f"{HOST}/api/stackchan/settings", timeout=10) as r:
        return json.load(r)["default_unit"]


def drive(device: str, stop: threading.Event, log) -> None:
    """The scripted actions, repeated until the run ends. Each is a Remote or settings call the unit must answer."""
    def act(name: str, path: str, body: dict | None = None) -> None:
        if stop.is_set():
            return
        log(f"{time.strftime('%H:%M:%S')} {name} -> {call(device, path, body)}")
        stop.wait(4)

    stop.wait(30)  # let the unit settle after boot
    while not stop.is_set():
        for snd in ("success", "popup", "exclamation", "shutter"):
            act(f"beep {snd}", "remote", {"do": "beep", "sound": snd})
        act("listen test", "listen-test", {})
        for color in ("red", "green", "blue"):
            act(f"flash {color}", "remote", {"do": "flash", "color": color})
        for name in OVERLAYS:
            act(f"overlay {name}", "remote", {"do": "overlay", "name": name, "intensity": "heavy" if name in ("stormy", "party", "celebrate") else "normal", "seconds": 8})
        act("overlay clear", "remote", {"do": "overlay_clear"})
        act("prefs crt on", "prefs", {"fx_crt": True})
        act("prefs crt off", "prefs", {"fx_crt": False})
        act("nod", "remote", {"do": "nod"})
        act("shake", "remote", {"do": "shake"})
        act("look around", "remote", {"do": "look"})
        act("center", "remote", {"do": "center"})
        act("game", "remote", {"do": "game", "name": "memory"})
        stop.wait(20)
        act("dance", "remote", {"do": "dance", "name": "happy"})
        stop.wait(15)
        act("stop dance", "remote", {"do": "stop_dance"})
        act("photo", "remote", {"do": "photo"})
        act("network test", "network-test", {})


def main() -> int:
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 900.0
    out = sys.argv[2] if len(sys.argv) > 2 else "fw-stress.log"
    import serial  # pyserial, from the ESP-IDF python environment (source scripts/fw-env.sh)

    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = PORT, 115200, 0.5
    ser.dtr = ser.rts = False
    ser.open()
    actions = open(out + ".actions", "w")
    stop = threading.Event()
    device = default_device()
    t = threading.Thread(target=drive, args=(device, stop, lambda s: (actions.write(s + "\n"), actions.flush())), daemon=True)
    started = time.time()
    t.start()
    with open(out, "wb") as f:
        while time.time() - started < secs:
            b = ser.read(8192)
            if b:
                f.write(b)
                f.flush()
    stop.set()
    return report(out, started, secs)


def report(path: str, started: float, secs: float) -> int:
    text = open(path, "rb").read().decode("utf8", "replace")
    mem = [tuple(int(x) for x in m.groups()) for m in re.finditer(
        r"mem internal_free=(\d+) internal_min=(\d+) int_big=(\d+) psram_free=(\d+) psram_min=(\d+)", text)]
    steady = mem[len(mem) // 4:] if len(mem) > 8 else mem  # the first quarter is boot and settling
    resets = len(re.findall(r"rst:0x", text))
    wdt = len(re.findall(r"task_wdt: Task watchdog got triggered", text))
    panics = len(re.findall(r"Guru Meditation|abort\(\) was called|Backtrace:", text))
    margins: dict[str, int] = {}
    for line in re.findall(r"SystemInfo: stk(.*)", text):
        for name, val in re.findall(r"(\S+)=(\d+)[ip]", line):
            margins[name] = min(margins.get(name, 1 << 30), int(val))
    # A close that comes with a unit boot within 6 seconds is the unit being reset (the flash, or opening the serial port
    # resets it); only a close with no reset beside it is a dropped link.
    drops = 0
    try:
        lo = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started))
        closes, boots = [], []
        for ln in open(HOST_LOG, errors="replace"):
            if ln[:19] < lo:
                continue
            try:
                stamp = time.mktime(time.strptime(ln[:19], "%Y-%m-%d %H:%M:%S"))
            except ValueError:
                continue  # a traceback or other line with no timestamp
            if "connection closed during a session" in ln:
                closes.append(stamp)
            elif "unit boot:" in ln:
                boots.append(stamp)
        drops = sum(1 for c in closes if not any(0 <= b - c <= 6 for b in boots))
    except OSError:
        pass
    if not steady:
        print("no memory lines read (is the memory line on? is the unit running?)")
        return 2
    free_steady = statistics.median(m[0] for m in steady)
    big_steady = statistics.median(m[2] for m in steady)
    big_min = min(m[2] for m in steady)
    int_min = min(m[1] for m in mem)
    frag = (steady[-1][2] / steady[-1][0]) if steady[-1][0] else 0.0
    rows = [
        ("internal_free steady (median)", free_steady, FLOORS["internal_free_steady"], free_steady >= FLOORS["internal_free_steady"]),
        ("internal_min", int_min, FLOORS["internal_min"], int_min >= FLOORS["internal_min"]),
        ("int_big steady (median)", big_steady, FLOORS["int_big_steady"], big_steady >= FLOORS["int_big_steady"]),
        ("int_big lowest after settling", big_min, FLOORS["int_big_min"], big_min >= FLOORS["int_big_min"]),
        # the ratio matters when free RAM is scarce; with 64 KB or more free, a 24 KB steady block already proves it
        ("int_big / internal_free at end", round(frag, 2), FLOORS["frag_ratio"], frag >= FLOORS["frag_ratio"] or steady[-1][0] >= 64000),
        ("psram_min", min(m[4] for m in mem), 6000000, min(m[4] for m in mem) > 6000000),
    ]
    print(f"run {secs:.0f} s, {len(mem)} memory lines")
    for name, val, floor, ok in rows:
        print(f"  {name:34s} {val:>10}  floor {floor:>8}  {'ok' if ok else 'BELOW'}")
    low = sorted(margins.items(), key=lambda kv: kv[1])[:6]
    print("  lowest stack margins:", ", ".join(f"{k}={v}" for k, v in low) or "none read (run longer than 60 s)")
    # the idle and inter-processor tasks have fixed sizes set by the system library; the gate holds the tasks we create
    bad = [k for k, v in margins.items() if v < FLOORS["stack_margin"] and not k.startswith(("IDLE", "ipc"))]
    print(f"  resets {resets} (1 is the start), task_wdt {wdt}, panics {panics}, host websocket drops {drops}")
    clean = resets <= 1 and wdt == 0 and panics == 0 and drops == 0 and not bad and all(r[3] for r in rows)
    print("GATE", "PASS" if clean else "FAIL" + (f" (stack margin under {FLOORS['stack_margin']}: {', '.join(bad)})" if bad else ""))
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
