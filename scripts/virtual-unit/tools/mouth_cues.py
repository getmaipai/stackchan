"""self.face.mouth_cues (patch SF10): the host sends the mouth levels of the next speech as [[ms, level], ...]. Rules are the unit's
mmc_set (maipai_mouthcue_core.h): 1 to 160 cues, ms 0 to 60000 and not decreasing, level 0 to 4, at most 12 cues in any 1000 ms.
Plays from the first audio frame of the next speech; a list not played within 10 s is dropped (the clock is the fake one)."""

import json

from tools import tool
from tools.apps import app

MAX_CUES, MAX_MS, MAX_PER_SEC, STALE_MS = 160, 60000, 12, 10000


def _muted(u):
    return bool(u.state.get("audio", {}).get("privacy", {}).get("muted"))


@tool("self.face.mouth_cues")
def mouth_cues(u, args):
    if _muted(u):
        return {"ok": False, "reason": "muted"}
    if app(u)["locked"]:
        return {"ok": False, "reason": "locked"}
    try:
        cues = json.loads(args.get("cues", ""))
        if not isinstance(cues, list) or any(not isinstance(c, list) or len(c) != 2 or not all(isinstance(x, int) and not isinstance(x, bool) for x in c) for c in cues):
            raise ValueError
    except (ValueError, TypeError):
        return {"ok": False, "reason": "bad_cues"}
    if not 1 <= len(cues) <= MAX_CUES:
        return {"ok": False, "reason": "bad_count"}
    for i, (ms, level) in enumerate(cues):
        if not 0 <= ms <= MAX_MS or (i and ms < cues[i - 1][0]):
            return {"ok": False, "reason": "bad_time"}
        if not 0 <= level <= 4:
            return {"ok": False, "reason": "bad_level"}
    j = 0
    for i in range(len(cues)):
        while cues[i][0] - cues[j][0] >= 1000:
            j += 1
        if i - j + 1 > MAX_PER_SEC:
            return {"ok": False, "reason": "too_fast"}
    u.state["mouth_cues"] = {"cues": cues, "loaded_at_ms": u.now_ms}
    return {"ok": True, "n": len(cues)}
