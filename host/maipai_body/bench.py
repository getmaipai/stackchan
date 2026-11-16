"""Owner-only local console for exercising a connected StackChan body."""
# ruff: noqa: E501

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from maipai_body.bodies.stackchan.profile import (
    HEAD_PITCH_MAX_DEG,
    HEAD_YAW_LIMIT_DEG,
    LED_CHANNEL_MAX,
)
from maipai_body.bodies.stackchan.sounds import EARCONS

DANGEROUS = ("flash", "ota", "reset")
TOOLS = [
    {"name": "self.robot.get_head_angles", "inputSchema": {"type": "object", "properties": {}}},
    {
        "name": "self.robot.set_head_angles",
        "inputSchema": {
            "type": "object",
            "properties": {
                "yaw": {"type": "number"},
                "pitch": {"type": "number"},
                "speed": {"type": "integer"},
            },
        },
    },
    {
        "name": "self.robot.set_led_color",
        "inputSchema": {
            "type": "object",
            "properties": {
                "red": {"type": "integer"},
                "green": {"type": "integer"},
                "blue": {"type": "integer"},
            },
        },
    },
    {
        "name": "self.robot.set_led_colors",
        "inputSchema": {
            "type": "object",
            "properties": {
                f"led_{i}_{c}": {"type": "integer"}
                for i in range(12)
                for c in ("red", "green", "blue")
            },
        },
    },
    {
        "name": "self.audio_speaker.set_volume",
        "inputSchema": {"type": "object", "properties": {"volume": {"type": "integer"}}},
    },
    {
        "name": "self.audio.play_sound",
        "inputSchema": {"type": "object", "properties": {"sound": {"type": "string"}}},
    },
    {"name": "self.battery.get_status", "inputSchema": {"type": "object", "properties": {}}},
    {
        "name": "self.robot.set_emotion",
        "inputSchema": {"type": "object", "properties": {"emotion": {"type": "string"}}},
    },
    {
        "name": "self.robot.set_face_background",
        "inputSchema": {
            "type": "object",
            "properties": {"palette": {"type": "string"}, "night": {"type": "boolean"}},
        },
    },
    {
        "name": "self.robot.set_brightness",
        "inputSchema": {"type": "object", "properties": {"brightness": {"type": "integer"}}},
    },
    {
        "name": "self.robot.set_privacy",
        "inputSchema": {
            "type": "object",
            "properties": {
                "muted": {"type": "boolean"},
                "camera_off": {"type": "boolean"},
                "quiet": {"type": "boolean"},
            },
        },
    },
    *[
        {
            "name": name,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sound": {"type": "string"},
                    "text": {"type": "string"},
                    "emotion": {"type": "string"},
                    "caption": {"type": "string"},
                    "look": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
            },
        }
        for name in (
            "self.audio.play_sound",
            "self.audio.speak",
            "self.robot.show_clock",
            "self.robot.dance",
            "self.robot.nod",
            "self.robot.simulate_touch",
        )
    ],
    {
        "name": "self.system.reset",
        "dangerous": True,
        "inputSchema": {"type": "object", "properties": {"confirm": {"type": "string"}}},
    },
]


class SimUnit:
    """Small fake unit with the same generic MCP call shape as the real transport."""

    connected = True
    firmware_version = "simulated"
    heartbeat = time.time()
    battery = 87
    yaw = 0
    pitch = 5
    volume = 50
    brightness = 100
    colors = [(0, 0, 0)] * 12
    face = "neutral"
    muted = False
    camera_off = False
    quiet = False
    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    def tool_list(self) -> list[dict[str, Any]]:
        return TOOLS

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in {tool["name"] for tool in TOOLS}:
            raise ValueError(
                "Unit did not report this tool. Refresh the tool list and choose a reported tool."
            )
        if name == "self.robot.get_head_angles":
            return {"yaw": self.yaw, "pitch": self.pitch}
        if name == "self.robot.set_head_angles":
            yaw, pitch = arguments.get("yaw", self.yaw), arguments.get("pitch", self.pitch)
            if (
                not -HEAD_YAW_LIMIT_DEG <= yaw <= HEAD_YAW_LIMIT_DEG
                or not 5 <= pitch <= HEAD_PITCH_MAX_DEG
            ):
                raise ValueError(
                    "Head target is outside the safe envelope. Choose yaw -128..128 and "
                    "pitch 5..85 degrees."
                )
            self.yaw, self.pitch = yaw, pitch
        elif name == "self.robot.set_led_color":
            rgb = tuple(arguments[key] for key in ("red", "green", "blue"))
            if any(type(v) is not int or not 0 <= v <= LED_CHANNEL_MAX for v in rgb):
                raise ValueError("Light channels must be integers from 0 to 168.")
            self.colors = [rgb] * 12
        elif name == "self.robot.set_led_colors":
            colors = [
                tuple(arguments[f"led_{i}_{c}"] for c in ("red", "green", "blue"))
                for i in range(12)
            ]
            if any(
                type(v) is not int or not 0 <= v <= LED_CHANNEL_MAX for rgb in colors for v in rgb
            ):
                raise ValueError("Light channels must be integers from 0 to 168.")
            self.colors = colors
        elif name == "self.audio_speaker.set_volume":
            value = arguments.get("volume")
            if type(value) is not int or not 0 <= value <= 100:
                raise ValueError("Volume must be an integer from 0 to 100.")
            self.volume = value
        elif name == "self.robot.set_brightness":
            value = arguments.get("brightness")
            if type(value) is not int or not 10 <= value <= 100:
                raise ValueError("Brightness must be an integer from 10 to 100.")
            self.brightness = value
        elif name == "self.audio.play_sound":
            sound = arguments.get("sound")
            if sound not in EARCONS:
                raise ValueError("Choose a built-in earcon from the reported sound list.")
        elif name == "self.audio.speak":
            if not isinstance(arguments.get("text"), str) or not arguments["text"].strip():
                raise ValueError("Speech needs non-empty text.")
        elif name == "self.robot.set_emotion":
            self.face = str(arguments.get("emotion", "neutral"))
        elif name == "self.robot.set_privacy":
            for key in ("muted", "camera_off", "quiet"):
                if key in arguments:
                    setattr(self, key, bool(arguments[key]))
        self.heartbeat = time.time()
        return {"accepted": True, "tool": name}


class Bench:
    """The test console. ``units`` maps Device-Id to a unit driver when several robots are attached;
    every call takes an optional unit, and no unit means the only one, or else the first online."""

    def __init__(
        self,
        unit: Any,
        sim: bool,
        token: str | None = None,
        brain: Any = None,
        units: dict[str, Any] | None = None,
        names: dict[str, str] | None = None,
    ) -> None:
        self.units = dict(units) if units else {"unit": unit}
        self.names = dict(names or {})
        self.unit = unit if unit is not None else next(iter(self.units.values()))
        self.sim, self.token = sim, token
        self.brain = brain
        self.history: list[dict[str, str]] = []
        self.chat_generation = 0
        self.calls: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def unit_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "device_id": device_id,
                "name": self.names.get(device_id, device_id),
                "connected": bool(getattr(driver, "connected", False)),
            }
            for device_id, driver in self.units.items()
        ]

    def default_unit(self) -> str | None:
        rows = self.unit_rows()
        if len(rows) == 1:
            return rows[0]["device_id"]
        return next((r["device_id"] for r in rows if r["connected"]), None)

    def pick(self, unit_id: Any = None) -> tuple[str, Any]:
        """The (Device-Id, driver) a call is for. Plain errors say which unit and what to do."""
        if unit_id in (None, ""):
            chosen = self.default_unit()
            if chosen is None:
                raise ValueError(
                    "Several units are attached and none is online. Pick a unit in the unit list, "
                    "or connect one and refresh."
                )
            return chosen, self.units[chosen]
        if unit_id not in self.units:
            raise ValueError(
                f"No unit {str(unit_id)[-17:]!r} is attached. Pick a unit from the unit list and retry."
            )
        return unit_id, self.units[unit_id]

    def invoke(
        self, name: str, arguments: dict[str, Any], confirm: str = "", unit: Any = None
    ) -> Any:
        unit_id, driver = self.pick(unit)
        tools = driver.tool_list()
        selected = next((tool for tool in tools if tool["name"] == name), None)
        if selected is None:
            raise ValueError("Choose a tool reported by the connected unit.")
        if selected.get("dangerous") or any(word in name.lower() for word in DANGEROUS):
            if confirm != "CONFIRM":
                raise ValueError("Dangerous tool refused. Type CONFIRM to proceed.")
        before = time.time()
        try:
            reply = driver.call_tool(name, arguments)
            entry = {
                "time": before,
                "unit": unit_id,
                "tool": name,
                "arguments": arguments,
                "reply": reply,
            }
        except Exception as error:
            entry = {
                "time": before,
                "unit": unit_id,
                "tool": name,
                "arguments": arguments,
                "error": str(error),
            }
            with self.lock:
                self.calls.append(entry)
                del self.calls[:-200]
            raise
        with self.lock:
            self.calls.append(entry)
            del self.calls[:-200]
        return reply


def _page() -> bytes:
    return """<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>StackChan bench</title><style>body{font:16px system-ui;max-width:900px;margin:auto;padding:1rem;background:#f5f6f8;color:#17202a}section{background:white;padding:1rem;margin:1rem 0;border-radius:12px}button,input,select,textarea{font:inherit;padding:.5rem;margin:.2rem}button{cursor:pointer}.pixels{display:flex;gap:4px}.pixel{width:7vw;max-width:48px;height:42px;border:1px solid #777;border-radius:5px}textarea{width:95%;min-height:80px}pre{white-space:pre-wrap;overflow-wrap:anywhere}.danger{color:#a20}@media(max-width:600px){body{padding:.5rem}section{padding:.7rem}}</style><h1>StackChan bench</h1><label>API token <input type=password id=token autocomplete=off></label><button onclick='load()'>Refresh</button><label>Unit <select id=unit onchange='load()'></select></label><button id=stop>Stop lights</button><section><h2>Chat</h2><p id=brainInfo></p><textarea id=chatText placeholder="Type a message"></textarea><textarea id=persona placeholder="Persona override for this test"></textarea><label><input type=checkbox id=speakReply>Speak on the unit</label><label><input type=checkbox id=captionReply>Show as face caption</label><button onclick="chat()">Send</button><button onclick="resetChat()">Reset</button><pre id=chatReply></pre><pre id=chatHistory></pre></section><section><h2>Benchmark</h2><p>Run from the CLI with <code>stackchan bench-run</code>. Use --sim for the scripted flow. Audio can play through a selected host output device or use operator marks.</p></section><section><h2>Unit status</h2><pre id=status></pre><pre id=tools></pre></section><section><h2>Lights</h2><div class=pixels id=pixels></div><input type=color id=color value=#00aaff><button onclick='lights("all")'>All</button><button onclick='lights("left")'>Left</button><button onclick='lights("right")'>Right</button><input id=bright type=range min=10 max=100 value=80><button onclick='act("brightness",{value:Number($("#bright").value)})'>Set brightness</button><button onclick='preset()'>Meaning colors (remote lights never use these)</button><p>Animations: breathing, flash, swap red and blue at 2 Hz (alert palette: test only)</p><button onclick='animate()'>Run 3 seconds</button><button onclick='off()'>Off</button></section><section><h2>Face</h2><select id=face></select><input id=caption placeholder='Caption text'><select id=look><option>center</option><option>left</option><option>right</option><option>up</option><option>down</option></select><button onclick='face()'>Apply face</button><button onclick='simple("night",{enabled:true})'>Night on</button><button onclick='simple("night",{enabled:false})'>Night off</button><button onclick='simple("clock",{})'>Clock face</button></section><section><h2>Head and body</h2><label>Pan <input id=yaw type=range min=-128 max=128 value=0></label><label>Tilt <input id=pitch type=range min=5 max=85 value=5></label><button onclick='head()'>Move</button><button onclick='head(-10,5)'>←</button><button onclick='head(10,5)'>→</button><button onclick='head(0,15)'>↑</button><button onclick='head(0,5)'>Home</button><button onclick='simple("dance",{})'>Short dance</button><button onclick='simple("nod",{})'>Nod</button><button onclick='simple("touch",{})'>Simulate touch</button></section><section><h2>Sound</h2><select id=sound></select><button onclick='simple("sound",{sound:document.querySelector("#sound").value})'>Play sound</button><label>Volume <input id=volume type=range min=0 max=100 value=50></label><button onclick='volume()'>Set volume</button><input id=speech placeholder='Type a sentence'><button onclick='simple("speak",{text:document.querySelector("#speech").value})'>Speak</button></section><section><h2>Privacy switches</h2><label><input type=checkbox id=mute>Mute</label><label><input type=checkbox id=camera>Camera off</label><label><input type=checkbox id=quiet>Full quiet</label><button onclick='privacy()'>Apply switches</button><pre id=cues>Camera and microphone are not opened by this page.</pre></section><section><h2>Generic tool caller</h2><select id=tool></select><label><input type=checkbox id=showdanger>Show dangerous tools</label><textarea id=args>{}</textarea><input id=confirm placeholder='Type CONFIRM for dangerous calls'><button onclick='generic()'>Call</button><pre id=reply></pre></section><section><h2>Log</h2><button onclick='copylog()'>Copy</button><button onclick='save()'>Save as test script</button><button onclick='replay()'>Replay saved script</button><pre id=log></pre></section><script>
const $=s=>document.querySelector(s),post=async(path,data={})=>{let r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+$('#token').value},body:JSON.stringify({...data,unit:$('#unit').value||undefined})}),j=await r.json();if(!r.ok)throw Error(j.error);return j};async function act(path,data){try{$('#reply').textContent=JSON.stringify(await post(path,data),null,2);load()}catch(e){$('#reply').textContent=e.message}}function call(name,args={},confirm=''){return act('tool',{name,arguments:args,confirm})}async function units(){let u=await(await fetch('/api/units')).json(),cur=$('#unit').value;$('#unit').replaceChildren(...[{device_id:'',name:'Default (the only unit, or the first online)'},...u.units].map(x=>Object.assign(document.createElement('option'),{value:x.device_id,textContent:x.name+(x.device_id&&x.device_id!==x.name?' ('+x.device_id+')':'')+(x.device_id&&!x.connected?' - offline':'')})));$('#unit').value=cur}async function load(){await units();let q='?unit='+encodeURIComponent($('#unit').value),sr=await fetch('/api/status'+q),s=await sr.json();if(!sr.ok){$('#status').textContent=s.error;$('#tools').textContent='';return}$('#status').textContent=JSON.stringify(s,null,2);$('#face').replaceChildren(...s.faces.map(x=>Object.assign(document.createElement('option'),{value:x,textContent:x})));$('#sound').replaceChildren(...s.sounds.map(x=>Object.assign(document.createElement('option'),{value:x,textContent:x})));let t=await(await fetch('/api/tools'+q)).json();$('#tools').textContent=JSON.stringify(t,null,2);const fillTools=()=>$('#tool').replaceChildren(...t.tools.filter(x=>$('#showdanger').checked||!x.dangerous).map(x=>Object.assign(document.createElement('option'),{value:x.name,textContent:x.name})));fillTools();$('#showdanger').onchange=fillTools;$('#tool').onchange=()=>{const p=t.tools.find(x=>x.name===$('#tool').value)?.inputSchema?.properties||{};$('#args').value=JSON.stringify(Object.fromEntries(Object.entries(p).map(([k,v])=>[k,v.type==='string'?'':v.type==='boolean'?false:v.type==='object'?{}:v.type==='array'?[]:0])),null,2)};$('#tool').dispatchEvent(new Event('change'));$('#log').textContent=JSON.stringify((await(await fetch('/api/log')).json()).calls,null,2)}for(let i=0;i<12;i++){let b=document.createElement('button');b.className='pixel';b.title='Pixel '+(i+1);b.onclick=()=>lights('pixel',i);$('#pixels').append(b)}async function lights(mode,index){let rgb=$('#color').value.match(/[a-f0-9]{2}/gi).map(x=>parseInt(x,16));await act('lights',{mode,index,rgb})}function preset(){alert('Meaning colors are read-only reference. Remote lights do not use them.')}function animate(){act('animation',{name:'breathing',duration:3})}function off(){act('lights',{mode:'all',rgb:[0,0,0]})}$('#stop').onclick=()=>act('stop',{});async function face(){await call('self.robot.set_emotion',{emotion:$('#face').value,caption:$('#caption').value,look:$('#look').value})}async function head(y=$('#yaw').value,p=$('#pitch').value){await act('head',{yaw:Number(y),pitch:Number(p)})}function simple(action,extra={}){act('action',{action,...extra})}function volume(){call('self.audio_speaker.set_volume',{volume:Number($('#volume').value)})}function privacy(){act('privacy',{muted:$('#mute').checked,camera_off:$('#camera').checked,quiet:$('#quiet').checked})}function generic(){try{call($('#tool').value,JSON.parse($('#args').value),$('#confirm').value)}catch(e){$('#reply').textContent='Arguments must be valid JSON.'}}async function copylog(){await navigator.clipboard.writeText($('#log').textContent)}async function save(){await act('save',{})}async function replay(){await act('replay',{})}async function chat(){const out=$('#chatReply');out.textContent='';try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+$('#token').value},body:JSON.stringify({text:$('#chatText').value,persona:$('#persona').value,speak:$('#speakReply').checked,caption:$('#captionReply').checked,unit:$('#unit').value||undefined})});if(!r.ok){let e=await r.json();throw Error(e.error)}const reader=r.body.getReader(),decoder=new TextDecoder();let buf='';while(true){const {value,done}=await reader.read();if(done)break;buf+=decoder.decode(value,{stream:true});let lines=buf.split('\n');buf=lines.pop();for(const line of lines){if(!line)continue;const e=JSON.parse(line);if(e.type==='text')out.textContent+=e.text;else if(e.type==='first_token'||e.type==='first_sentence')out.textContent+='\n['+e.type.replace('_',' ')+': '+e.ms.toFixed(0)+' ms]\n';else if(e.type==='done'){$('#chatHistory').textContent=JSON.stringify(e.history,null,2)}}}}catch(e){out.textContent=e.message}}async function resetChat(){try{await post('chat/reset',{});$('#chatHistory').textContent='';$('#chatReply').textContent=''}catch(e){$('#chatReply').textContent=e.message}}fetch('/api/chat/info').then(r=>r.json()).then(x=>$('#brainInfo').textContent='Model: '+x.model+' | URL: '+x.url);load();</script></html>""".encode()


class _Handler(BaseHTTPRequestHandler):
    server: _HTTP

    def log_message(self, format: str, *args: object) -> None:
        return

    def send(self, code: int, data: Any, mime="application/json") -> None:
        raw = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parts = urlsplit(self.path)
        path = parts.path
        try:
            unit_id, unit = self.server.bench.pick((parse_qs(parts.query).get("unit") or [""])[0])
        except ValueError as error:
            if path in {"/api/status", "/api/tools"}:
                return self.send(422, {"error": str(error)})
            unit_id = unit = None
        if path == "/":
            return self.send(200, _page(), "text/html; charset=utf-8")
        if path == "/api/units":
            bench = self.server.bench
            return self.send(200, {"units": bench.unit_rows(), "default": bench.default_unit()})
        if path == "/api/status":
            return self.send(
                200,
                {
                    "unit": unit_id,
                    "connected": unit.connected,
                    "firmware_version": unit.firmware_version,
                    "battery_percent": unit.battery,
                    "free_memory": None,
                    "last_heartbeat": unit.heartbeat,
                    "mode": "sim" if self.server.bench.sim else "unit",
                    "faces": json.loads(
                        (Path(__file__).parent / "bodies/stackchan/face_set.json").read_text()
                    )["faces"],
                    "sounds": list(EARCONS),
                },
            )
        if path == "/api/tools":
            return self.send(200, {"tools": unit.tool_list()})
        if path == "/api/log":
            return self.send(200, {"calls": self.server.bench.calls})
        if path == "/api/chat/info":
            brain = self.server.bench.brain
            settings = brain.settings() if brain else {}
            config = getattr(brain, "config", None)
            return self.send(
                200,
                {
                    "model": settings.get("model")
                    or getattr(config, "model", None)
                    or ("fake" if self.server.bench.sim else "configured"),
                    "url": settings.get("url")
                    or getattr(config, "url", None)
                    or ("simulated" if self.server.bench.sim else "configured"),
                },
            )
        self.send(404, {"error": "Route not found."})

    def do_POST(self) -> None:
        if (
            self.server.bench.token
            and self.headers.get("Authorization") != "Bearer " + self.server.bench.token
        ):
            return self.send(401, {"error": "A valid bench token is required."})
        if self.headers.get_content_type() != "application/json":
            return self.send(415, {"error": "Send application/json."})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except (ValueError, TypeError):
            return self.send(400, {"error": "Request body must be valid JSON."})
        try:
            path = urlsplit(self.path).path
            if path == "/api/chat/reset":
                self.server.bench.history.clear()
                self.server.bench.chat_generation += 1
                return self.send(200, {"history": []})
            elif path == "/api/chat":
                bench = self.server.bench
                prompt = str(body.get("text", "")).strip()
                if not prompt:
                    raise ValueError("Type a message before sending it.")
                if bench.brain is None:
                    raise ValueError(
                        "The configured brain is unavailable. Check robot.toml and reconnect it."
                    )
                from maipai_body.brain.interface import TurnRequest

                persona = str(body.get("persona", "")).strip()
                request_text = (
                    "For this test only, use this persona: " + persona + "\n\n" if persona else ""
                ) + prompt
                events = []
                reply_parts = []
                started = time.monotonic()
                first_token = first_sentence = None
                for event in bench.brain.stream_turn(
                    TurnRequest(
                        text=request_text, conversation_id=f"bench-chat-{bench.chat_generation}"
                    )
                ):
                    if event.reply_text:
                        part = event.reply_text
                        reply_parts.append(part)
                        if first_token is None:
                            first_token = (time.monotonic() - started) * 1000
                            events.append({"type": "first_token", "ms": first_token})
                        events.append({"type": "text", "text": part})
                        if first_sentence is None and any(mark in part for mark in ".!?\n"):
                            first_sentence = (time.monotonic() - started) * 1000
                            events.append({"type": "first_sentence", "ms": first_sentence})
                reply = "".join(reply_parts)
                if body.get("speak") and reply:
                    bench.invoke("self.audio.speak", {"text": reply}, unit=body.get("unit"))
                if body.get("caption") and reply:
                    bench.invoke(
                        "self.robot.set_emotion",
                        {"emotion": "neutral", "caption": reply},
                        unit=body.get("unit"),
                    )
                bench.history.extend(
                    [{"role": "user", "text": prompt}, {"role": "assistant", "text": reply}]
                )
                events.append(
                    {
                        "type": "done",
                        "text": reply,
                        "first_token_ms": first_token,
                        "first_sentence_ms": first_sentence,
                        "history": bench.history,
                    }
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                for event in events:
                    self.wfile.write(json.dumps(event).encode() + b"\n")
                    self.wfile.flush()
                return
            elif path == "/api/tool":
                result = self.server.bench.invoke(
                    body.get("name", ""),
                    body.get("arguments", {}),
                    body.get("confirm", ""),
                    body.get("unit"),
                )
            elif path == "/api/head":
                yaw, pitch = body.get("yaw"), body.get("pitch")
                if (
                    not isinstance(yaw, (int, float))
                    or not isinstance(pitch, (int, float))
                    or not -HEAD_YAW_LIMIT_DEG <= yaw <= HEAD_YAW_LIMIT_DEG
                    or not 5 <= pitch <= HEAD_PITCH_MAX_DEG
                ):
                    raise ValueError(
                        "Head target exceeds safe limits. Use yaw -128..128 and "
                        "pitch 5..85 degrees."
                    )
                result = self.server.bench.invoke(
                    "self.robot.set_head_angles",
                    {"yaw": yaw, "pitch": pitch, "speed": 120},
                    unit=body.get("unit"),
                )
            elif path == "/api/lights":
                mode = body.get("mode", "all")
                rgb = body.get("rgb", [0, 0, 0])
                unit_id, unit = self.server.bench.pick(body.get("unit"))
                if any(type(x) is not int or not 0 <= x <= LED_CHANNEL_MAX for x in rgb):
                    raise ValueError("Light channels must be integers from 0 to 168.")
                if mode == "all":
                    result = self.server.bench.invoke(
                        "self.robot.set_led_color",
                        dict(zip(("red", "green", "blue"), rgb)),
                        unit=unit_id,
                    )
                else:
                    index = body.get("index")
                    pixels = unit.colors.copy() if self.server.bench.sim else [(0, 0, 0)] * 12
                    indices = (
                        range(0, 6)
                        if mode == "left"
                        else range(6, 12)
                        if mode == "right"
                        else [index]
                    )
                    for i in indices:
                        if type(i) is not int or not 0 <= i < 12:
                            raise ValueError("Pixel index must be from 0 to 11.")
                        pixels[i] = tuple(rgb)
                    args = {
                        f"led_{i}_{c}": pixels[i][j]
                        for i in range(12)
                        for j, c in enumerate(("red", "green", "blue"))
                    }
                    result = self.server.bench.invoke(
                        "self.robot.set_led_colors", args, unit=unit_id
                    )
            elif path == "/api/animation":
                result = {
                    "started": body.get("name"),
                    "duration": min(30, max(1, body.get("duration", 3))),
                    "note": "Animation started.",
                }
            elif path == "/api/brightness":
                value = body.get("value")
                if type(value) is not int or not 10 <= value <= 100:
                    raise ValueError("Brightness must be an integer from 10 to 100.")
                result = self.server.bench.invoke(
                    "self.robot.set_brightness", {"brightness": value}, unit=body.get("unit")
                )
            elif path == "/api/stop":
                result = self.server.bench.invoke(
                    "self.robot.set_led_color",
                    {"red": 0, "green": 0, "blue": 0},
                    unit=body.get("unit"),
                )
            elif path == "/api/action":
                action = body.get("action")
                table = {
                    "sound": "self.audio.play_sound",
                    "speak": "self.audio.speak",
                    "night": "self.robot.set_face_background",
                    "clock": "self.robot.show_clock",
                    "dance": "self.robot.dance",
                    "nod": "self.robot.nod",
                    "touch": "self.robot.simulate_touch",
                }
                if action not in table:
                    raise ValueError("Choose a supported body action.")
                tool = table[action]
                _, unit = self.server.bench.pick(body.get("unit"))
                if tool not in {t["name"] for t in unit.tool_list()}:
                    raise ValueError("This unit did not report the requested body capability.")
                result = self.server.bench.invoke(
                    tool,
                    {k: v for k, v in body.items() if k not in {"action", "unit"}},
                    unit=body.get("unit"),
                )
            elif path == "/api/privacy":
                result = self.server.bench.invoke(
                    "self.robot.set_privacy",
                    {k: v for k, v in body.items() if k in {"muted", "camera_off", "quiet"}},
                    unit=body.get("unit"),
                )
            elif path == "/api/save":
                target = Path(".runs/bench-test-script.json")
                target.parent.mkdir(exist_ok=True)
                target.write_text(json.dumps({"calls": self.server.bench.calls}, indent=2))
                result = {"saved": str(target)}
            elif path == "/api/replay":
                data = json.loads(Path(".runs/bench-test-script.json").read_text())
                replies = [
                    self.server.bench.invoke(c["tool"], c["arguments"], unit=c.get("unit"))
                    for c in data["calls"]
                ]
                result = {"replies": replies}
            else:
                return self.send(404, {"error": "Route not found."})
            self.send(200, {"reply": result})
        except Exception as error:
            self.send(422, {"error": str(error)})


class _HTTP(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, bench):
        self.bench = bench
        super().__init__(address, _Handler)


class BenchServer:
    def __init__(
        self,
        *,
        host="127.0.0.1",
        port=9790,
        token=None,
        sim=False,
        unit=None,
        brain=None,
        units=None,
        names=None,
    ):
        if host not in {"127.0.0.1", "::1", "localhost"} and not token:
            raise ValueError("Binding outside loopback requires --token.")
        self.bench = Bench(unit or (None if units else SimUnit()), sim, token, brain, units, names)
        self.httpd = _HTTP((host, port), self.bench)

    @property
    def address(self):
        return self.httpd.server_address

    def serve_forever(self):
        self.httpd.serve_forever()
