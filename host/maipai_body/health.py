"""One health document for the whole host: what runs, what does not, per unit and per part, in plain words.

The settings server serves it as JSON (`/api/stackchan/health`) and as a page (`/health`); `stackchan status` prints it. See
docs/plan/service-and-supervision.md."""

from __future__ import annotations

import html
import json
import time
import urllib.error
import urllib.request
from typing import Any

from maipai_body.supervisor import Supervisor


def build_health(supervisor: Supervisor | None, *, connected: list[str], paired: dict[str, dict[str, Any]], started: float, names: dict[str, str] | None = None, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    names = names or {}
    parts = supervisor.report() if supervisor is not None else []
    bad = [p for p in parts if p["state"] in ("failed", "restarting")]
    units = []
    for device_id in sorted(set(paired) | set(connected)):
        record = paired.get(device_id, {})
        last = record.get("last_seen")
        units.append({
            "unit": device_id, "name": names.get(device_id, ""), "connected": device_id in connected,
            "last_seen": float(last) if last else None,
            "message": (f"{names.get(device_id) or device_id}: connected." if device_id in connected else f"{names.get(device_id) or device_id}: not connected" + (f" (last seen {time.strftime('%Y-%m-%d %H:%M', time.localtime(float(last)))})." if last else " yet.")),
            "parts": [p for p in parts if p["unit"] == device_id],
        })
    failed = [p for p in bad if p["state"] == "failed"]
    if failed:
        summary = "Something needs you: " + "; ".join(p["message"] for p in failed[:3])
        state = "failed"
    elif bad:
        summary = "Working, with " + str(len(bad)) + " part" + ("s" if len(bad) != 1 else "") + " restarting: " + "; ".join(p["message"] for p in bad[:3])
        state = "degraded"
    else:
        summary = "Everything is running."
        state = "ok"
    return {
        "state": state, "summary": summary, "uptime_s": max(0, int(now - started)),
        "parts": [p for p in parts if not p["unit"]], "units": units,
        "advice": [p["advice"] for p in bad if p["advice"]][:3],
    }


def render_text(doc: dict[str, Any]) -> str:
    lines = [doc["summary"], f"The host has been running for {_span(doc['uptime_s'])}.", ""]
    lines.append("Parts:")
    lines += [f"  {p['message']}" for p in doc["parts"]] or ["  (none are watched yet)"]
    lines.append("")
    lines.append(f"Robots ({len(doc['units'])}):")
    for u in doc["units"]:
        lines.append(f"  {u['message']}")
        lines += [f"    {p['message']}" for p in u["parts"]]
    if not doc["units"]:
        lines.append("  No robot is paired yet. Run `stackchan pair`, or open the settings page.")
    if doc["advice"]:
        lines += ["", "What to do:"] + [f"  {a}" for a in doc["advice"]]
    return "\n".join(lines)


def _span(seconds: int) -> str:
    if seconds < 90:
        return f"{seconds} seconds"
    if seconds < 5400:
        return f"{seconds // 60} minutes"
    return f"{seconds // 3600} hours"


def render_page(doc: dict[str, Any]) -> bytes:
    def li(text: str, state: str = "") -> str:
        return f'<li class="{state}">{html.escape(text)}</li>'

    parts = "".join(li(p["message"], p["state"]) for p in doc["parts"]) or "<li>No parts are watched yet.</li>"
    units = "".join(li(u["message"], "ok" if u["connected"] else "off") + "".join(li("  " + p["message"], p["state"]) for p in u["parts"]) for u in doc["units"]) or "<li>No robot is paired yet.</li>"
    advice = "".join(li(a) for a in doc["advice"])
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Health</title>
<style>:root{{--bg:#fff;--fg:#17202a;--good:#1e7a46;--bad:#b3261e;--warn:#9a6700}}@media (prefers-color-scheme:dark){{:root{{--bg:#101418;--fg:#eaeef2;--good:#5fd08b;--bad:#ff8a80;--warn:#f0c36a}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:18px/1.5 system-ui,sans-serif}}main{{max-width:44rem;margin:0 auto;padding:1rem 16px 3rem}}li.ok{{color:var(--good)}}li.failed{{color:var(--bad)}}li.restarting{{color:var(--warn)}}</style>
<meta http-equiv="refresh" content="10"></head><body><main><h1>Health</h1><p role="status"><b>{html.escape(doc['summary'])}</b></p>
<h2>Parts</h2><ul>{parts}</ul><h2>Robots</h2><ul>{units}</ul>{('<h2>What to do</h2><ul>' + advice + '</ul>') if advice else ''}</main></body></html>"""
    from maipai_body.dashboard_shell import apply

    return apply(page, "health").encode("utf-8")


def fetch_health(host_url: str | None = None, timeout: float = 4.0) -> dict[str, Any] | None:
    """The running host's health document, or None when no host answers there."""
    import os

    host_url = host_url or f"http://127.0.0.1:{os.environ.get('MAIPAI_STACKCHAN_SETTINGS_PORT') or 8051}"
    try:
        with urllib.request.urlopen(host_url.rstrip("/") + "/api/stackchan/health", timeout=timeout) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, OSError, ValueError):
        return None
