"""The installed set's tools (docs/plan/installed-set.md B5), answered by assets_sim.AssetStore. A tool is registered only when schema/tools.json lists it (the firmware track adds
the names when the unit's core lands), so the parity check between the virtual unit and the firmware keeps holding; `sim.assets` {tool: ..., ...} reaches the same handlers before that."""
import json
from pathlib import Path

from tools import REGISTRY, tool

_SCHEMA = set(json.loads((Path(__file__).resolve().parents[3] / "schema" / "tools.json").read_text())["tools"])


def _store(u):
    return u.assets


def _call(u, which: str, args: dict):
    s = _store(u)
    if which == "list":
        return s.list()
    if which == "install":
        return s.install(args.get("kind", ""), int(args.get("slot", -1)), args.get("header_b64", ""), args.get("sig_b64", ""))
    if which == "data":
        return s.data(int(args.get("at", 0)), args.get("b64", ""))
    if which == "commit":
        return s.commit()
    if which == "remove":
        return s.remove(args.get("kind", ""), int(args.get("slot", -1)))
    if which == "swap":
        return s.swap(args.get("kind", ""), int(args.get("slot", -1)))
    if which == "abort":
        return s.abort()
    return {"ok": False, "error": f"unknown asset tool {which}"}


for _name in ("list", "install", "data", "commit", "remove", "swap", "abort"):
    if f"self.assets.{_name}" in _SCHEMA:
        REGISTRY[f"self.assets.{_name}"] = (lambda n: (lambda u, args: _call(u, n, args)))(_name)


@tool("sim.assets")
def sim_assets(u, args):
    """Virtual only: the self.assets.* tools before the firmware lists them. {tool: list|install|data|commit|remove|swap|abort, ...that tool's arguments}."""
    return _call(u, args.get("tool", "list"), args)
