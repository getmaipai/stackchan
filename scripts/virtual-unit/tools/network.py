"""Network, update, pack and remote-control virtual unit tools."""
import base64
import hashlib
import ipaddress
import re

from tools import tool

PACK_LIMITS = {"look": 1_000_000, "language": 200_000, "filler": 400_000, "sound": 400_000, "dance": 100_000, "game": 200_000}
PACK_TYPES = tuple(PACK_LIMITS)


def _net(u):
    return u.state.setdefault("network", {"wifi": [], "packs": {}, "tailnet": {}, "remote": {"active": False, "history": [], "token": None, "token_kind": None, "token_until": 0, "say_id": 0, "say_result": "none"}, "prefer_until": 0, "rx": None})


def _pack_error(code):
    texts = {"type": "That pack type is not known. Packs can be look, language, filler, sound, dance or game.", "name": "The pack name must be 1 to 40 letters, numbers, spaces, dots, dashes or underscores. Rename the pack and send it again.", "size": "That pack is empty or too big for the robot to keep. Use a smaller or simpler pack.", "sum": "The pack checksum is not valid. Export the pack again from where it came from.", "order": "The pack pieces arrived out of order. Send the pack again from the start.", "range": "A pack piece ran past the end of the pack. Send it again from the start.", "not_started": "No pack is being sent. Start a new pack first.", "short": "The pack did not arrive in full. Send it again.", "mismatch": "The pack is damaged: its contents do not match its checksum. Export it again.", "busy": "The robot is still saving the last pack. Wait a few seconds, then send again."}
    return {"ok": False, "code": code, "error": texts.get(code, "The pack could not be read. Export it again or use a pack made for this robot."), "error_es": "El paquete no se pudo procesar. Exportalo de nuevo."}


def _record(n, u, kind, result, text=""):
    n["remote"]["history"].insert(0, {"t": u.now_ms // 1000, "kind": kind, "who": "remote", "result": result, "canceled": False, "text": text[:47]})
    del n["remote"]["history"][10:]


@tool("self.firmware.update")
def firmware_update(u, a):
    n = _net(u)
    return {"started": False, "reason": "update_not_available"}


@tool("self.network.prefer_tailnet")
def prefer_tailnet(u, a):
    n = _net(u); m = a.get("minutes", 5); t = n["tailnet"]
    if not 0 <= m <= 60: return {"ok": False, "error": "bad_minutes"}
    if m and not t.get("peer"): return {"ok": False, "error": "no_hub_address"}
    if m and not t.get("ready", False): return {"ok": False, "error": "tailnet_not_ready"}
    n["prefer_until"] = u.now_ms + m * 60000
    return {"ok": True, "minutes": m}


@tool("self.network.test")
def network_test(u, a):
    _net(u)
    # Hardware link probes are not available; fixed values make this shape deterministic.
    return {"ok": True, "problems": 1, "summary": "Network needs attention.", "fix": "Connect the robot to Wi-Fi.", "steps": [{"step": "wifi", "state": "bad", "line": "Wi-Fi: not connected"}, {"step": "host", "state": "skipped", "line": "Home host: not checked"}, {"step": "private", "state": "skipped", "line": "Private network: not built in"}]}


@tool("self.pack.begin")
def pack_begin(u, a):
    n = _net(u); typ = a.get("type", "look"); name = a.get("name", "Pack"); size = a.get("size", 0); sha = a.get("sha256", "")
    if typ not in PACK_LIMITS: return _pack_error("type")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,39}", name): return _pack_error("name")
    if size <= 0 or size > min(1_000_000, PACK_LIMITS[typ]): return _pack_error("size")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha): return _pack_error("sum")
    n["rx"] = {"type": typ, "name": name, "version": a.get("version", 1), "size": size, "sha256": sha.lower(), "data": bytearray()}
    return {"ok": True, "max_bytes": PACK_LIMITS[typ]}


@tool("self.pack.data")
def pack_data(u, a):
    n = _net(u); rx = n.get("rx")
    try: raw = base64.b64decode(a.get("b64", ""), validate=True)
    except Exception: return _pack_error("order")
    if rx is None: return _pack_error("not_started")
    at = a.get("at", 0)
    if at != len(rx["data"]): return _pack_error("order")
    if at + len(raw) > rx["size"]: return _pack_error("range")
    rx["data"].extend(raw)
    return {"ok": True, "got": len(rx["data"])}


@tool("self.pack.commit")
def pack_commit(u, a):
    n = _net(u); rx = n.get("rx")
    if rx is None: return _pack_error("not_started")
    if len(rx["data"]) < rx["size"]: return _pack_error("short")
    payload = bytes(rx["data"])
    if hashlib.sha256(payload).hexdigest() != rx["sha256"]: n["rx"] = None; return _pack_error("mismatch")
    n["packs"][rx["type"]] = {"name": rx["name"], "sha256": rx["sha256"], "size": rx["size"], "cached": False}
    typ = rx["type"]; n["rx"] = None
    return {"ok": True, "type": typ, "cached": "pending"}


@tool("self.pack.remove")
def pack_remove(u, a):
    n = _net(u); typ = a.get("type", "look")
    if typ not in PACK_LIMITS: return _pack_error("type")
    n["packs"].pop(typ, None); return {"ok": True}


@tool("self.pack.status")
def pack_status(u, a):
    n = _net(u); typ = a.get("type", "look")
    if typ not in PACK_LIMITS: return _pack_error("type")
    p = n["packs"].get(typ)
    return {"ok": True, "type": typ, "held": p is not None, "name": p["name"] if p else "", "sha256": p["sha256"] if p else "", "size": p["size"] if p else 0, "cached": bool(p and p["cached"]), "cache": "empty", "cache_on": False, "writing": False, "fallback": p is None, "booted": True}


@tool("self.remote.action")
def remote_action(u, a):
    n = _net(u); r = n["remote"]; kind = a.get("kind", "move"); text = a.get("text", "")
    if kind not in ("move", "find", "photo", "dance", "game", "say", "listen"): return {"ok": False, "reason": "bad_kind"}
    if not r["active"]: _record(n,u,kind,"no_session",text); return {"ok": False,"reason":"no_session"}
    token = (r.get("last_token",0) + 1) % 2147483648
    r.update(last_token=token, token=token, token_kind=kind, token_until=u.now_ms+15000)
    _record(n,u,kind,"ok",text)
    return {"ok": True,"token":token}


@tool("self.remote.history")
def remote_history(u, a):
    n = _net(u); return {"ok": True,"active":n["remote"]["active"],"items":list(n["remote"]["history"])}


@tool("self.remote.say")
def remote_say(u, a):
    n = _net(u); r = n["remote"]; text = a.get("text", ""); token = a.get("token", 0)
    reason = "ok"
    if not r["active"]: reason = "no_session"
    elif not text: reason = "empty"
    elif len(text) > 200: reason = "too_long"
    elif token == 0: reason = "no_token"
    elif token != r.get("token"): reason = "bad_token"
    elif r.get("token_kind") != "say": reason = "wrong_kind"
    elif u.now_ms > r.get("token_until", 0): reason = "bad_token"
    if reason != "ok": _record(n,u,"say",reason,text); return {"ok":False,"reason":reason}
    r["token"] = None; r["say_id"] += 1; r["say_result"] = "none"; _record(n,u,"say","ok",text)
    return {"ok":True,"id":r["say_id"]}


@tool("self.remote.say_status")
def remote_say_status(u, a):
    r = _net(u)["remote"]; return {"ok":True,"id":r["say_id"],"result":r["say_result"]}


@tool("self.remote.session")
def remote_session(u, a):
    n = _net(u); r = n["remote"]; r["active"] = bool(a.get("active",True)); r["label"] = a.get("label", "remote")[:23]
    return {"ok":True,"active":r["active"]}


@tool("self.tailnet.set")
def tailnet_set(u, a):
    n = _net(u); t = n["tailnet"]
    if a.get("forget",False):
        t.clear(); return {"ok":True,"restart":False,"forgotten":True}
    key = a.get("key", ""); peer = a.get("peer", "")
    if key and not re.fullmatch(r"[A-Za-z0-9_-]{20,256}", key): return {"ok":False,"error":"bad_key"}
    if peer:
        try:
            ip = ipaddress.ip_address(peer)
            if ip.version != 4 or not ip in ipaddress.ip_network("100.64.0.0/10"): return {"ok":False,"error":"bad_address"}
        except ValueError: return {"ok":False,"error":"bad_address"}
    if key: t["key"] = key
    if peer: t["peer"] = peer
    t["enabled"] = a.get("enabled",False)
    if t["enabled"] and a.get("now",False): t["state"] = "connecting"
    return {"ok":True,"restart":False}


@tool("self.tailnet.status")
def tailnet_status(u, a):
    t = _net(u)["tailnet"]
    return {"compiled":False,"enabled":t.get("enabled",False),"guard_off":False,"key_saved":bool(t.get("key")),"peer_saved":bool(t.get("peer")),"joined":t.get("joined",False),"state":"off","ip":"","ready":False,"route":"home","fails":0,"refusal":0,"internal_free":0,"largest_block":0}


@tool("self.version.get")
def version_get(u, a):
    return {"ok":True,"version":"virtual","tag":"","image":"flashed by cable","slot":"unknown","internal_free":0,"internal_min":0,"internal_big":0,"psram_free":0,"psram_min":0,"uptime_s":u.now_ms//1000}


@tool("self.wifi.list_saved")
def wifi_list(u, a):
    return [{"index":i,"ssid":v["ssid"]} for i,v in enumerate(_net(u)["wifi"])]
# self.wifi.add, forget and switch were removed from the firmware by patch SF02 (tool visibility); the unit has no tool to change saved networks.
