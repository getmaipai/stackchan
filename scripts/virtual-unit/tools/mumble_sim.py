"""Virtual only (not a firmware tool): the offline mumble on the virtual unit (patch UX16, docs/design/offline-mumble.md). sim.mumble {text, ms} mumbles a caption: the notes are the reference
implementation's (scripts/virtual-unit/mumble.py, the same algorithm as the unit's core) and the face's mouth follows them on the fake clock; {action: "stop"} ends it. No sound plays on the
virtual unit: the notes are listed in the result and kept in u.state["mumble"], and the sounds page (scripts/sounds-demo.py) plays the same notes."""
from . import tool

import mumble


@tool("sim.mumble")
def sim_mumble(u, args):
    st = u.state.setdefault("mumble", {"active": False, "played": []})
    if args.get("action") == "stop":
        st["active"] = False
        u.raw("speak 0")
        return {"ok": True}
    text = str(args.get("text", ""))
    if not text.strip():
        return {"ok": False, "error": "text is empty: give the caption to mumble"}
    ms = int(args.get("ms", max(600, 70 * len(text))))
    if not 200 <= ms <= 60000:
        return {"ok": False, "error": "ms must be from 200 to 60000: the length of the caption on screen"}
    start = u.now_ms
    blips = mumble.blips(text, start, start + ms)
    st.update(active=True, played=[], text=text, start=start, end=start + ms, last=-1, seen=start - 1)

    def tick(now):
        if not st.get("active") or st.get("start") != start:
            if tick in u.tickers:
                u.tickers.remove(tick)
            return
        cur = 0
        for b in blips:
            if b.t_ms <= now < b.t_ms + max(1, b.dur_ms):
                cur = b.mouth if b.dur_ms else 0
        for b in blips:   # a note that began since the last slice counts as played, even when it was shorter than the slice
            if b.dur_ms and st["seen"] < b.t_ms <= now:
                st["played"].append(b.t_ms)
        st["seen"] = now
        if cur != st["last"]:
            st["last"] = cur
            u.raw("speak %d" % cur)
        if now >= start + ms:
            st["active"] = False
            u.raw("speak 0")
            u.tickers.remove(tick)

    u.tickers.append(tick)
    return {"ok": True, "notes": sum(1 for b in blips if b.dur_ms), "rests": sum(1 for b in blips if not b.dur_ms), "ms": ms}
