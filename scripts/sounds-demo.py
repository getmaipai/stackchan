#!/usr/bin/env python3
"""A page to listen to the robot's sounds: the game sounds (the unit's own tone clips and the sketches) and the offline mumble in six languages, with the mouth that goes with each
mumble drawn beside the player. Loopback only, nothing leaves this computer, no outside script or font.
Usage: python3 scripts/sounds-demo.py [port, default 8796]   then open http://127.0.0.1:8796/
Placement: host-side development tool. Upstream: none."""
import html
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GS = ROOT / "docs" / "dev" / "game-sounds"
MUMBLE = ROOT / "docs" / "dev" / "mumble"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Robot sounds</title><style>
:root{--bg:#f7f8fa;--fg:#1c2128;--mut:#58626e;--card:#fff;--line:#dde1e6;--acc:#1b63c4}
@media (prefers-color-scheme:dark){:root{--bg:#12161b;--fg:#e4e8ec;--mut:#a0aab5;--card:#1a2027;--line:#2c343d;--acc:#6aa8ff}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}main{max-width:860px;margin:0 auto;padding:16px}
h1{font-size:1.6rem}h2{font-size:1.15rem;margin-top:1.8em}.row{display:flex;gap:14px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:8px 0;flex-wrap:wrap}
.row b{min-width:9ch}.t{color:var(--mut);flex:1 1 240px}audio{height:36px}canvas{background:#000;border-radius:8px}
</style></head><body><main><h1>Robot sounds</h1>
<p>Press play. The sounds are made from tone tables and a small rule, not recorded; nothing here leaves this computer. Listen at a low volume first.</p>
%(body)s
<script>
const MOUTH=%(mouth)s;
document.querySelectorAll('canvas[data-id]').forEach(function(c){
  const levels=MOUTH[c.dataset.id], a=document.getElementById('a-'+c.dataset.id), g=c.getContext('2d');
  function draw(){const t=a.currentTime*1000, i=Math.min(levels.length-1,Math.floor(t/33)), v=a.paused&&t===0?0:levels[Math.max(0,i)]/100;
    g.clearRect(0,0,c.width,c.height);g.fillStyle='#fff';const w=70,h=6+v*34;g.beginPath();g.ellipse(c.width/2,c.height/2,w/2,h/2,0,0,7);g.fill();
    if(!a.paused&&!a.ended)requestAnimationFrame(draw);}
  a.addEventListener('play',draw);a.addEventListener('pause',draw);a.addEventListener('ended',draw);draw();
});
</script></main></body></html>"""


def build() -> tuple[str, dict]:
    parts = ["<h2>Offline mumble (when the robot has words but no voice)</h2>"]
    mouth = {}
    meta = json.loads((MUMBLE / "samples.json").read_text(encoding="utf-8")) if (MUMBLE / "samples.json").exists() else {"samples": []}
    for s in meta["samples"]:
        mouth[s["id"]] = s["mouth_33ms"]
        parts.append(f'<div class="row"><b>{html.escape(s["language"])}</b><audio id="a-{s["id"]}" controls preload="none" src="/mumble/{s["id"]}.wav"></audio>'
                     f'<canvas data-id="{s["id"]}" width="110" height="60"></canvas><span class="t">{html.escape(s["text"])}</span></div>')
    for title, folder, url in (("Game sounds the robot plays (rendered from its own tone table)", GS / "on-the-robot", "/robot"), ("Game sound sketches (proposals, not on the robot)", GS, "/sketch")):
        parts.append(f"<h2>{html.escape(title)}</h2>")
        for f in sorted(folder.glob("*.wav")):
            parts.append(f'<div class="row"><b>{html.escape(f.stem)}</b><audio controls preload="none" src="{url}/{f.name}"></audio></div>')
    return PAGE % {"body": "\n".join(parts), "mouth": json.dumps(mouth)}, mouth


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, data: bytes, kind: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._send(build()[0].encode("utf-8"), "text/html; charset=utf-8")
            return
        for prefix, folder in (("/mumble/", MUMBLE), ("/robot/", GS / "on-the-robot"), ("/sketch/", GS)):
            if path.startswith(prefix):
                f = folder / Path(path[len(prefix):]).name
                if f.suffix == ".wav" and f.is_file():
                    self._send(f.read_bytes(), "audio/wav")
                    return
        self._send(b"not found: this page serves / and its sounds", "text/plain", 404)


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8796
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"robot sounds on http://127.0.0.1:{server.server_port}/", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
