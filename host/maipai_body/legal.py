# ruff: noqa: E501
"""The affiliation statements, copied from docs/legal/affiliation.json (owner policy docs/plan/trademark-and-affiliation.md).

Do not reword here: a test fails when a copy drifts from the JSON. The short notice goes in the same small place on every page of the host's
local pages, linking to the About page; the full statement is on the About page and in the documentation."""

from __future__ import annotations

import html

PROJECT = "MaiPai for StackChan"
FULL = "MaiPai for StackChan is an independent project providing custom firmware and tools for the M5Stack StackChan robot. It is not affiliated with, endorsed by, or sponsored by M5Stack or the original StackChan creators. Product names and trademarks belong to their respective owners."
SHORT = "Independent project. Not affiliated with or endorsed by M5Stack or the original StackChan creators."

FOOTER_CSS = ".legal{font-size:.8rem;opacity:.75;margin:2rem 0 1rem;text-align:center}.legal a{color:inherit}"


def footer_html() -> str:
    """The short notice, small, in the same place on every page: the foot of the page, linking to the full statement."""
    return f'<p class="legal" role="contentinfo">{html.escape(SHORT)} <a href="/about">About and legal</a></p>'


LICENSES = (
    ("This project", "AGPL-3.0 (see LICENSE). Firmware source files added through patches carry an MIT notice."),
    ("StackChan firmware base and xiaozhi-esp32", "MIT. Their notices stay with those sources."),
    ("StackChan structure files used for the 3D model", "MIT, copyright M5Stack, pinned and unchanged with their license."),
    ("Espressif ESP-SR and ESP-IDF", "The build downloads them under their own licenses. We hold none of their files."),
    ("LVGL", "MIT, fetched by the build."),
    ("esptool-js", "Apache-2.0, one file copied unchanged into the web flasher."),
    ("The local stack (downloaded on request)", "llama.cpp MIT; Qwen2.5 Apache-2.0; Moonshine MIT; Piper MIT with public-domain voice data."),
)
CREDITS = (
    "M5Stack for the StackChan robot and its open structure files.",
    "The xiaozhi-esp32 project, the firmware base beneath the robot's software.",
    "Espressif for ESP-IDF and ESP-SR.",
    "The llama.cpp, Qwen, Moonshine, Piper, sherpa-onnx and LVGL projects.",
)


def about_page() -> bytes:
    licenses = "".join(f"<li><b>{html.escape(a)}.</b> {html.escape(b)}</li>" for a, b in LICENSES)
    credits = "".join(f"<li>{html.escape(c)}</li>" for c in CREDITS)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>About and legal - {PROJECT}</title>
<style>:root{{--bg:#fff;--fg:#17202a;--muted:#566573;--accent:#0b6bcb;--card:#f4f6f8;--line:#d5dbe1}}@media (prefers-color-scheme:dark){{:root{{--bg:#101418;--fg:#eaeef2;--muted:#a0abb6;--accent:#6cb2ff;--card:#1a2027;--line:#2c3640}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:18px/1.5 system-ui,sans-serif}}main{{max-width:46rem;margin:0 auto;padding:1rem 16px 3rem}}</style></head><body><main>
<h1>About and legal</h1><p>{html.escape(FULL)}</p>
<h2>Licenses</h2><ul>{licenses}</ul><p>The full list is in THIRD-PARTY.md and NOTICE.</p>
<h2>Credits</h2><ul>{credits}</ul>
</main></body></html>"""
    from maipai_body.dashboard_shell import apply

    return apply(page, "settings").encode("utf-8")
