"""What the unit does while its host is away (firmware patches 143 and SF49): the Offline label after 45 s without the link, the dim amber ring on the same timer, the plain-words notice after
10 minutes away and every 30 minutes, and the reconnect wait (doubling delay with jitter, capped at 30 s for the first ten minutes and 120 s after). The backoff and the notice rule are the unit's
own core (maipai_reconnect_core.h cut out of SF49, compiled with dance/reconnect_sim.c). The 45 s label rule is patch 143's one number; the unit's link state is the rig's (link_lost, link_up).
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import ctypes
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCH = ROOT / "firmware" / "patches" / "SF49-task-supervisor-and-reconnect.patch"
SCHEDULE_PATCH = ROOT / "firmware" / "patches" / "SF64-faster-reconnect-schedule.patch"   # the waits start at 0.5 s and the cap is 5, 15, 30, then 120 s by time away
OUT = ROOT / ".runs" / "vu-dance"
HEADER = "maipai_reconnect_core.h"
OFFLINE_LABEL_MS = 45000   # patch 143
SLEEPY_MS = 180000         # patch 143: the sleepy face from 3 minutes away
NOTICE_MS = 20000          # patch SF73: how long the notice holds the banner row (the row's limit; SF68 asked for 30)

# The notice is English in the firmware (patch SF49: hal_bridge::notice). The other five are drafts for a speaker to read: the firmware track should carry them in its language tables.
NOTICE = {
    "en": "Can't reach Home. Check it is on and on the same Wi-Fi. I keep trying.",
    "es": "No encuentro Home. Mira que esté encendido y en el mismo Wi-Fi. Sigo intentándolo.",
    "fr": "Je ne joins pas Home. Vérifiez qu'il est allumé et sur le même Wi-Fi. J'continue d'essayer.",
    "de": "Home ist nicht erreichbar. Prüfen Sie, ob es an ist und im selben WLAN. Ich versuche es weiter.",
    "pt": "Não consigo falar com o Home. Veja se está ligado e no mesmo Wi-Fi. Vou continuar tentando.",
    "it": "Non raggiungo Home. Controlla che sia acceso e sulla stessa Wi-Fi. Continuo a provare.",
}

_LIB = None


def lib() -> ctypes.CDLL:
    global _LIB
    if _LIB is not None:
        return _LIB
    text = PATCH.read_text()
    m = re.search(r"^\+\+\+ b/firmware/main/hal/" + re.escape(HEADER) + r"\n@@[^\n]*\n(.*?)(?=^diff --git )", text, re.S | re.M)
    if not m:
        raise RuntimeError(f"{HEADER} is not in {PATCH.name}: the patch changed; update scripts/virtual-unit/host_away.py")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / HEADER).write_text("\n".join(l[1:] for l in m.group(1).splitlines() if l.startswith("+")) + "\n")
    if SCHEDULE_PATCH.exists():   # patch SF64 changes the same core: apply it on top, so the rig runs the schedule the unit runs
        tree = OUT / "sf64"
        (tree / "firmware" / "main" / "hal").mkdir(parents=True, exist_ok=True)
        (tree / "firmware" / "main" / "hal" / HEADER).write_text((OUT / HEADER).read_text())
        done = subprocess.run(["patch", "-p1", "-s", "-f", "-N", "-i", str(SCHEDULE_PATCH)], cwd=tree, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if done.returncode != 0:
            raise RuntimeError(f"{SCHEDULE_PATCH.name} does not apply to the SF49 core ({done.stdout.strip()}): update scripts/virtual-unit/host_away.py")
        (OUT / HEADER).write_text((tree / "firmware" / "main" / "hal" / HEADER).read_text())
    src = HERE / "dance" / "reconnect_sim.c"
    so = OUT / "reconnect_sim.dylib"
    if not so.exists() or so.stat().st_mtime < max(src.stat().st_mtime, (OUT / HEADER).stat().st_mtime):
        subprocess.run(["cc", "-O1", "-std=c99", "-shared", "-fPIC", "-Wall", "-I", str(OUT), str(src), "-o", str(so)], check=True)
    L = ctypes.CDLL(str(so))
    for name, args, res in (("rc_cap", [ctypes.c_uint32], ctypes.c_uint32), ("rc_grow", [ctypes.c_uint32] * 2, ctypes.c_uint32), ("rc_wait", [ctypes.c_uint32] * 3, ctypes.c_uint32), ("rc_notice_due", [ctypes.c_uint32] * 2, ctypes.c_int)):
        f = getattr(L, name)
        f.argtypes, f.restype = args, res
    _LIB = L
    return L


class HostAway:
    """Attach to a VirtualUnit (u.host_away). The rig tells it when the link goes and comes back; time is the unit's fake clock."""

    def __init__(self, u, language: str = "en", seed: int = 1) -> None:
        self.u, self.language, self.L = u, language, lib()
        self.since: int | None = None
        self.last_notice_away = 0
        self.notices: list[tuple[int, str]] = []   # (away ms, text)
        self.label = False
        self.sleepy = False
        self.events: list[tuple[str, int]] = []   # (event name, away_s): the ws_away_notice events of patch SF68
        self.attempts: list[tuple[int, int]] = []   # (away ms, wait ms before the next try)
        self.delay = 500
        self.next_try = 0
        self.rng = seed | 1
        u.tickers.append(self.tick)

    def link_lost(self) -> None:
        if self.since is None:
            self.since = self.u.now_ms
            self.last_notice_away = 0
            self.delay = 500   # patch SF64: the first wait is 0.5 s
            self.next_try = self.u.now_ms
            self.attempts = []
            self.notices = []

    def link_up(self) -> None:
        self.since = None
        self.last_notice_away = 0
        self.label = False
        if self.sleepy:
            self.sleepy = False
            self.u.raw("emotion neutral")
        self.u.raw("bstatus 80 0 1 1 1")   # the Offline label and the amber ring go with the link

    def away_ms(self) -> int:
        return 0 if self.since is None else self.u.now_ms - self.since

    def _rnd(self) -> int:
        self.rng = (self.rng * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.rng >> 8

    def tick(self, now: int) -> None:
        if self.since is None:
            return
        away = now - self.since
        if not self.label and away >= OFFLINE_LABEL_MS:
            self.label = True
            self.u.raw("bstatus 80 0 1 0 1")   # hub down: the word Offline in the upper left, the dim amber ring (patch 143)
        if not self.sleepy and away >= SLEEPY_MS:
            self.sleepy = True
            self.u.raw("emotion sleepy")   # the sleepy face from 3 minutes away (patch 143)
        if self.L.rc_notice_due(away, self.last_notice_away):
            self.last_notice_away = away
            text = NOTICE[self.language]
            self.notices.append((away, text))
            self.events.append(("ws_away_notice", away // 1000))   # patch SF68: the event the bench and the host see
            self.u.raw(f"bpost privacy wifioff away {NOTICE_MS} {text}")   # patch SF73: hal_bridge::notice_urgent: the privacy priority takes the row from the steady Offline look for 20 s
        if now >= self.next_try:   # one reconnect try: the next wait is the delay plus jitter, never above the cap for this much time away
            cap = self.L.rc_cap(away)
            wait = self.L.rc_wait(self.delay, cap, self._rnd())
            self.attempts.append((away, wait))
            self.delay = self.L.rc_grow(self.delay, cap)
            self.next_try = now + wait
