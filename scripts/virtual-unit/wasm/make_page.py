#!/usr/bin/env python3
"""Intent: make the playground page from the native viewer page (scripts/virtual-unit/view.html) without editing it: the same controls, panels and 3D drawing, with these documented changes
(each must match exactly once; a changed viewer stops the build with a message):
  1. the three.js script tag points at the site's own copy (vendor/three-r128), not a CDN;
  2. the scripts view.html loads by absolute path (view3d.js, talk.js) load from the page's own folder; the physics engine is not part of this build (physics-unavailable.js does not exist,
     so the viewer's own "did not load" message shows);
  3. the physics switch is disabled with a plain note, and the three.js failure message no longer names an outside address;
  3b. the link to /about points at about.html (made from docs/legal/affiliation.json, as view.py does);
  4. a banner above the viewer ("Simulation in your browser: nothing leaves this page", the short affiliation wording, a language switch), a loading note, and app.js before the viewer's script.
Usage: make_page.py VIEW_HTML AFFILIATION_JSON OUT_FOLDER
Placement: host-side development tool. Upstream: none."""
import html
import json
import sys
from pathlib import Path

SWAPS = [
    ('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>', '<script src="vendor/three-r128/three.min.js"></script>'),
    ("sc.src='/talk.js'", "sc.src='talk.js'"),
    ("scriptEl.src='/view3d.js'", "scriptEl.src='view3d.js'"),
    ("sc.src='/physics.js'", "sc.src='physics-unavailable.js'"),
    ('<a href="/about"', '<a href="about.html"'),
    ("the 3D drawing needs internet access to cdnjs.cloudflare.com; the flat screen is at /frame.png.", "the 3D drawing needs vendor/three-r128/three.min.js from the folder of this page. Reload; if it keeps happening, report the browser name and version."),
    ('<input id="phys" type="checkbox"> Physics mode (loads the engine, about 11 MB, only when on)', '<input id="phys" type="checkbox" disabled> Physics mode (not in the browser build: the engine file is not shipped here; use the native playground)'),
    ("<title>MaiPai for StackChan: virtual unit</title>", "<title>MaiPai for StackChan: virtual unit in your browser</title>"),
]


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: make_page.py VIEW_HTML AFFILIATION_JSON OUT_FOLDER. Give the native viewer page, the affiliation file and the folder to write index.html and about.html into.")
        return 2
    page = Path(sys.argv[1]).read_text()
    words = json.loads(Path(sys.argv[2]).read_text())
    out = Path(sys.argv[3])
    for old, new in SWAPS:
        if page.count(old) != 1:
            print(f"make_page.py: expected `{old[:70]}` once in view.html, found {page.count(old)}. The viewer changed: update SWAPS in scripts/virtual-unit/wasm/make_page.py.", file=sys.stderr)
            return 1
        page = page.replace(old, new)
    css = ("#pgbar{position:fixed;top:0;left:0;right:0;height:34px;z-index:60;display:flex;gap:12px;align-items:center;padding:0 12px;background:#0b3d24;color:#dff7e8;font:13px system-ui,sans-serif;border-bottom:1px solid #1f7a48}"
           "#pgbar b{font-weight:600}#pgbar label{display:flex;gap:6px;align-items:center;white-space:nowrap}#pgbar select{background:#15181d;color:#dfe6ee;border:1px solid #2e3641;border-radius:4px;padding:2px 4px}#pgbar .sp{flex:1}"
           "#app{margin-top:34px;height:calc(100% - 34px)}"
           "#pgboot{position:fixed;inset:34px 0 0 0;z-index:55;background:#15181dee;color:#dfe6ee;display:flex;flex-direction:column;align-items:center;justify-content:center;font:15px system-ui,sans-serif;text-align:center;padding:24px}"
           "#pgboot.done{display:none}#pgboot .t{color:#8fa0b3;font-size:13px;margin-top:8px;max-width:520px}"
           "#pggal canvas,#pggal img{width:100%;max-width:320px;image-rendering:pixelated;background:#000;border:1px solid var(--line)}</style></head><body>")
    banner = ('<div id="pgbar"><span><b>Simulation in your browser</b>: nothing leaves this page.</span>'
              f'<span class="sp" title="{html.escape(words["full"])}">{html.escape(words["short"])}</span>'
              '<label>Language <select id="pglang"><option value="en">English</option><option value="es">Espa&ntilde;ol</option></select></label></div>'
              '<div id="pgboot"><div id="pgboot-text">Loading the virtual unit: the screens renderer, the unit\'s C cores and its Python (about 6 MB over the wire, once; the browser keeps it).</div>'
              '<div class="t" id="pgboot-detail"></div></div><script src="app.js"></script>')
    if page.count("</style></head><body>") != 1 or page.count('<div id="app">') != 1:
        print("make_page.py: the viewer's head or app container changed. Update make_page.py.", file=sys.stderr)
        return 1
    page = page.replace("</style></head><body>", css + banner, 1)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page)
    about = ("<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>About: " + html.escape(words["project"]) + "</title>"
             "<body style='font:16px system-ui;max-width:640px;margin:48px auto;padding:0 16px;line-height:1.5'>"
             "<h1 style='font-size:20px'>" + html.escape(words["project"]) + "</h1><p>" + html.escape(words["full"]) + "</p>"
             "<p>The 3D model shows the real robot, with its own name and label. Those marks belong to their owners and are not this project's branding. "
             "A compliance mark drawn on a label is a detail of the original hardware; this software is not certified by anyone.</p>"
             "<p><a href='index.html'>Back to the viewer</a></p></body></html>")
    (out / "about.html").write_text(about)
    print(f"make_page: {out / 'index.html'} ({len(page)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
