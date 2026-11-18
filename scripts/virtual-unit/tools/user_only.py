"""Tools the firmware marks user-only (patches SF01 and SF02): the model's tool list hides them, a call by name still answers.
A locked unit refuses all of them. Written by hand from the patch text; the unit's rate limit on tool tries (mlk_tool_open) is not modeled."""
from tools import tool
from tools.apps import app


def _net(u):
    return u.state.setdefault("network", {}).setdefault("wifi", [])


def _locked(u):
    return app(u)["locked"]


@tool("self.wifi.add")
def wifi_add(u, a):
    if _locked(u):
        return False  # patch SF02: a locked unit keeps its networks
    ssid, password = a.get("ssid", ""), a.get("password", "")
    if not ssid or len(ssid) > 32 or len(password) > 63:
        return False
    nets = [v for v in _net(u) if v["ssid"] != ssid]
    nets.append({"ssid": ssid, "password": password})
    u.state["network"]["wifi"] = nets
    return True


@tool("self.wifi.forget")
def wifi_forget(u, a):
    nets, i = _net(u), a.get("index", -1)
    if _locked(u) or not 0 <= i < len(nets):
        return False
    nets.pop(i)
    return True


@tool("self.wifi.switch")
def wifi_switch(u, a):
    nets, i = _net(u), a.get("index", -1)
    if _locked(u) or not 0 <= i < len(nets):
        return False
    nets.insert(0, nets.pop(i))
    # The virtual unit has no Wi-Fi driver; firmware requests an immediate disconnect here.
    u.state.setdefault("network", {})["wifi_disconnect_requested"] = True
    return True


@tool("self.lock.set")
def lock_set(u, a):
    s = app(u)
    code, current = a.get("code", ""), a.get("current", "")
    if s["locked"]:
        return {"ok": False, "reason": "locked"}
    if not (code.isdigit() and 4 <= len(code) <= 6):
        return {"ok": False, "reason": "bad_code"}
    if s["code"]:
        if not current:
            return {"ok": False, "reason": "current_needed"}
        if current != s["code"]:
            return {"ok": False, "reason": "wrong_current"}
    s["code"] = code
    return {"ok": True}


@tool("self.lock.clear")
def lock_clear(u, a):
    s = app(u)
    if s["locked"]:
        return {"ok": False, "reason": "locked"}
    if not s["code"]:
        return {"ok": False, "reason": "no_code"}
    if a.get("current", "") != s["code"]:
        return {"ok": False, "reason": "wrong_current"}
    s["code"] = None
    s["auto_minutes"] = 0
    return {"ok": True}


@tool("self.lock.config")
def lock_config(u, a):
    s = app(u)
    minutes = a.get("auto_minutes", 0)
    if s["locked"]:
        return {"ok": False, "reason": "locked"}
    if minutes not in (0, 1, 5, 15, 30, 60):
        return {"ok": False, "reason": "bad_minutes"}
    if minutes == 0 and s["code"]:
        if not a.get("current", ""):
            return {"ok": False, "reason": "current_needed"}
        if a["current"] != s["code"]:
            return {"ok": False, "reason": "wrong_current"}
    s["auto_minutes"] = minutes
    return {"ok": True}
