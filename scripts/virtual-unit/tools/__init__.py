"""Tool handlers for the virtual unit, one module per group. A handler is registered with @tool("self.x.y") and gets (unit, args):
  def handler(u, args): ...   return a dict (the tool's JSON result). Return {"isError": True, "text": "what went wrong and what to do"} for a refusal.
State lives in u.state (a dict): use your group's own key, u.state.setdefault("lock", {...}). Time is u.now_ms (the fake clock). Never sleep.
Arguments are already checked against schema/tools.json (names and types) before a handler runs; apply the firmware's own defaults and ranges.
"""
REGISTRY: dict = {}


def tool(name: str):
    def register(fn):
        if name in REGISTRY:
            raise RuntimeError(f"tool {name} is registered twice: keep each tool in one group module")
        REGISTRY[name] = fn
        return fn
    return register
