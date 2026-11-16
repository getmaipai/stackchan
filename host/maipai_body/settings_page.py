# ruff: noqa: E501
"""The core settings page: one small local page, no Home, no household data.

``SettingsBackend`` holds the logic (testable with no server); ``render_page`` makes the HTML.
The dashboard server routes /settings and /api/stackchan/settings* to it, local administrator only.
"""

from __future__ import annotations

import base64
import html
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from maipai_body import faces as face_settings
from maipai_body import picture_faces as picture_mod
from maipai_body import unit_extras as extras_mod
from maipai_body.bodies.stackchan import updater
from maipai_body.i18n import SUPPORTED, catalog, normalize, t
from maipai_body.picture_faces_page import pictures_js
from maipai_body.unit_settings import SettingsError, UnitSettingsStore

Live = Callable[[str], dict[str, Any]]


class SettingsBackend:
    def __init__(
        self,
        *,
        devices: Callable[[], dict[str, Any]],
        store: UnitSettingsStore | None = None,
        live: Live | None = None,
        host_address: str = "",
        update_source: str | Path | None = None,
        public_key: str | Path | None = None,
        push: updater.OtaPush | None = None,
        preset: str = "core",
        language: str = "en",
        faces: face_settings.FaceService | None = None,
        extras: extras_mod.UnitExtras | None = None,
        people: extras_mod.PeopleStore | None = None,
        pictures: picture_mod.PictureService | None = None,
    ) -> None:
        self.devices, self.store = devices, store or UnitSettingsStore()
        self.live = live or (lambda _device_id: {})
        self.host_address = host_address
        self.update_source, self.public_key = update_source, public_key
        self.push, self.preset, self.language = push, preset, normalize(language)
        self._faces = faces
        self._extras = extras
        self._people = people
        self._pictures = pictures

    @property
    def pictures(self) -> picture_mod.PictureService:
        """The owner's picture faces. Without a live link a unit counts as offline: the pictures are saved and go to
        the unit when the host next sees it connect."""
        if self._pictures is None:
            self._pictures = picture_mod.PictureService(face_settings.offline_call)
        return self._pictures

    @property
    def extras(self) -> extras_mod.UnitExtras:
        """Reactions, clock, network test and details. Without a live link a unit counts as offline."""
        if self._extras is None:
            self._extras = extras_mod.UnitExtras(extras_mod.offline_call)
        return self._extras

    @property
    def people(self) -> extras_mod.PeopleStore:
        if self._people is None:
            self._people = extras_mod.PeopleStore()
        return self._people

    @property
    def faces(self) -> face_settings.FaceService:
        """The face settings of every unit. Without a live link a unit counts as offline: a change
        is saved and goes to the unit when the host next sees it connect."""
        if self._faces is None:
            self._faces = face_settings.FaceService(face_settings.offline_call)
        return self._faces

    def state(self, lang: str | None = None) -> dict[str, Any]:
        units = []
        for device_id in sorted(self.devices()):
            own = self.store.get(device_id)
            live = self.live(device_id)
            wifi = live.get("wifi_configured")
            units.append(
                {
                    "device_id": device_id,
                    "name": own.get("name", f"StackChan {device_id[-5:]}"),
                    "wifi": "unknown" if wifi is None else ("set" if wifi else "unset"),
                    "persona": own.get("persona", ""),
                    "llm": own.get("llm", {"url": "", "model": "", "api_key_env": ""}),
                    "alarms": own.get("alarms", []),
                    "volume_cap": own.get("volume_cap", 100),
                    "speech_speed": own.get("speech_speed", 1.0),
                    "speech_pitch": own.get("speech_pitch", 0),
                    "muted": own.get("muted", bool(live.get("muted", False))),
                    "firmware_version": live.get("firmware_version"),
                    "online": live.get("online"),
                }
            )
        online = [u["device_id"] for u in units if u["online"]]
        default = units[0]["device_id"] if len(units) == 1 else (online[0] if online else None)
        return {
            "default_unit": default or (units[0]["device_id"] if units else None),
            "host_address": self.host_address,
            "language": normalize(lang or self.language),
            "update_source_set": bool(self.update_source),
            "units": units,
        }

    def save(self, device_id: str, values: dict[str, Any]) -> dict[str, Any]:
        if device_id not in self.devices():
            raise SettingsError("That unit is not paired. Pair it first, then open its settings.")
        return self.store.update(device_id, values)

    def update(self, device_id: str, lang: str | None = None, *, dry_run: bool = True) -> str:
        """The Update button: check the signed release. It only checks (dry run) unless the caller
        passes dry_run=False after the person confirmed; then it pushes over the air, which needs
        the host's push (a unit that is online). Without one, the refusal says what to do."""
        lang = normalize(lang or self.language)
        folder = updater.read_source(self.update_source)
        if folder is None:
            raise updater.UpdateRefused(t(lang, "settings.update.none"))
        release = updater.load_release(
            folder, public_key=self.public_key, preset=self.preset, lang=lang
        )
        unit_version = self.live(device_id).get("firmware_version")
        try:
            return updater.update_over_air(
                release,
                device_id=device_id,
                unit_version=unit_version,
                push=self.push,
                dry_run=dry_run,
                lang=lang,
            )
        except updater.UpdateRefused as error:
            if unit_version and not updater.is_newer(release.version, unit_version):
                raise updater.UpdateRefused(t(lang, "settings.update.current")) from error
            raise

    # -- face settings (faces.py): one section per unit on the page ----------------------------

    def _face_unit(self, device_id: str) -> None:
        if device_id not in self.devices():
            raise face_settings.FaceError(
                "That unit is not paired. Pair it first, then open its face settings."
            )

    def _faces_get(self, device_id: str, lang: str) -> tuple[int, str, bytes]:
        try:
            self._face_unit(device_id)
            view = face_settings.settings_view(self.faces, device_id, lang)
            return 200, JSON, json.dumps(view).encode()
        except face_settings.FaceError as error:
            return 400, JSON, json.dumps({"error": str(error)}).encode()

    def _faces_post(self, rest: str, body: dict[str, Any], lang: str) -> tuple[int, dict[str, Any]]:
        """Save and send one unit's face settings. ``.../reset`` goes back to the plain face."""
        values = {k: v for k, v in body.items() if k not in {"lang", "confirm", "screen_lang"}}
        if "screen_lang" in body:
            values["lang"] = body[
                "screen_lang"
            ]  # the words on the unit's screen, not the page language
        try:
            if rest.endswith("/reset"):
                device_id = rest[: -len("/reset")]
                self._face_unit(device_id)
                return 200, self.faces.reset(device_id, lang)
            self._face_unit(rest)
            return 200, face_settings.apply_settings(self.faces, rest, values, lang)
        except face_settings.FaceError as error:
            return 400, {"error": str(error)}

    # -- unit extras (unit_extras.py): reactions, clock, network test, details, face extras, people ----

    def _unit_known(self, device_id: str) -> None:
        if device_id not in self.devices():
            raise extras_mod.ExtrasError(
                "That unit is not paired. Pair it first, then open its settings."
            )

    def _people_view(self) -> dict[str, Any]:
        return {
            "people": [p.to_json() for p in self.people.all()],
            "choices": {
                "colour": ["none", *face_settings.PALETTE],
                "caption_size": list(face_settings.CAPTION_SIZES),
            },
            "limits": {"people": extras_mod.PEOPLE_MAX},
            "problem": self.people.problem,
        }

    def _unit_get(self, rest: str, lang: str) -> tuple[int, str, bytes]:
        """GET /api/stackchan/unit/<id>/(reactions|clock|details|games)."""
        device_id, _, what = rest.rpartition("/")
        try:
            self._unit_known(device_id)
            if what == "reactions":
                body = self.extras.reactions_view(device_id)
            elif what == "clock":
                body = self.extras.clock_view(device_id)
            elif what == "details":
                body = self.extras.details(device_id, lang)
            elif what == "games":
                body = self.extras.games(device_id, lang)
            elif what == "pictures":
                body = self.pictures.view(device_id, lang)
            else:
                return 404, JSON, json.dumps({"error": "not found"}).encode()
            return 200, JSON, json.dumps(body).encode()
        except (
            extras_mod.ExtrasError,
            face_settings.FaceError,
            picture_mod.PictureError,
        ) as error:
            return 400, JSON, json.dumps({"error": str(error)}).encode()

    def _pictures_post(
        self, device_id: str, action: str, values: dict[str, Any], lang: str
    ) -> tuple[int, dict[str, Any]]:
        """POST /api/stackchan/unit/<id>/pictures/<add|remove|options|send|clear>."""
        self._unit_known(device_id)
        service = self.pictures
        if action == "add":
            try:
                raw = base64.b64decode(str(values.get("rgba_b64", "")), validate=True)
                width, height = int(values.get("width", 0)), int(values.get("height", 0))
                index = int(values.get("index", 0))
            except (ValueError, TypeError):
                raise picture_mod.PictureError(
                    picture_mod.say(lang, "bad_picture"), "bad_picture"
                ) from None
            return 200, service.add_picture(
                device_id, str(values.get("slot", "")), index, width, height, raw, lang
            )
        if action == "remove":
            index = values.get("index")
            return 200, service.remove_picture(
                device_id,
                str(values.get("slot", "")),
                index if isinstance(index, int) else None,
                lang,
            )
        if action == "options":
            overlay = values.get("overlay")
            fps = values.get("fps")
            return 200, service.set_options(
                device_id,
                mode=values.get("mode"),
                fps=fps if isinstance(fps, int) and not isinstance(fps, bool) else None,
                overlay=overlay if isinstance(overlay, dict) else None,
                lang=lang,
            )
        if action == "send":
            return 200, service.send(device_id, lang)
        if action == "clear":
            return 200, service.clear_all(device_id, lang)
        return 404, {"error": "not found"}

    def _unit_post(self, rest: str, body: dict[str, Any], lang: str) -> tuple[int, dict[str, Any]]:
        """POST /api/stackchan/unit/<id>/<action>, and the people routes."""
        values = {k: v for k, v in body.items() if k not in {"lang", "confirm"}}
        try:
            if rest == "people" or rest.startswith("people/"):
                return self._people_post(rest, values, lang)
            if "/pictures/" in rest:
                device_id, _, action = rest.partition("/pictures/")
                return self._pictures_post(device_id, action, values, lang)
            device_id, _, action = rest.rpartition("/")
            if action == "reset" and device_id.endswith("/reactions"):
                device_id = device_id[: -len("/reactions")]
                self._unit_known(device_id)
                return 200, self.extras.reset_reactions(device_id, lang)
            self._unit_known(device_id)
            if action == "reactions":
                return 200, self.extras.save_reactions(device_id, values, lang)
            if action == "clock":
                if values.get("sync") is True:
                    return 200, self.extras.set_clock_now(device_id, lang)
                return 200, self.extras.save_zone(device_id, values.get("zone"), lang)
            if action == "network-test":
                result = self.extras.network_test(device_id, lang)
                return 200, {**result, "message": result.get("summary", "")}
            if action == "decorate":
                seconds = values.get("seconds", face_settings.DECOR_DEFAULT_S)
                return 200, self.faces.decorate(
                    device_id, str(values.get("name", "none")), seconds, lang
                )
            return 404, {"error": "not found"}
        except (
            extras_mod.ExtrasError,
            face_settings.FaceError,
            picture_mod.PictureError,
        ) as error:
            return 400, {"error": str(error)}

    def _people_post(
        self, rest: str, values: dict[str, Any], lang: str
    ) -> tuple[int, dict[str, Any]]:
        if rest == "people":
            person = extras_mod.clean_person(values, lang)
            self.people.save(person, lang)
            return 200, self._people_view()
        parts = rest.split("/")  # people/<id>/remove  or  people/<id>/use/<unit>
        pid = parts[1] if len(parts) > 1 else ""
        if len(parts) == 3 and parts[2] == "remove":
            self.people.remove(pid)
            return 200, self._people_view()
        if len(parts) == 4 and parts[2] == "use":
            person = next((p for p in self.people.all() if p.id == pid), None)
            if person is None:
                raise extras_mod.ExtrasError(extras_mod.say(lang, "person_unknown"))
            self._unit_known(unquote(parts[3]))
            return 200, extras_mod.apply_person(self.faces, unquote(parts[3]), person, lang)
        return 404, {"error": "not found"}

    # -- routes shared by every server that hosts the page ------------------------------------

    def route_get(self, path: str, lang: str, local_admin: bool) -> tuple[int, str, bytes] | None:
        """(status, content type, body) for a settings GET, or None when it is not a settings path."""
        if path.startswith(FACES):
            if not local_admin:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            return self._faces_get(unquote(path[len(FACES) :]), lang)
        if path.startswith(UNIT) or path == PEOPLE:
            if not local_admin:
                return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
            if path == PEOPLE:
                return 200, JSON, json.dumps(self._people_view()).encode()
            return self._unit_get(unquote(path[len(UNIT) :]), lang)
        if path != "/settings" and not path.startswith("/api/stackchan/settings"):
            return None
        if not local_admin:
            return 403, JSON, json.dumps({"error": t(lang, "settings.local_only")}).encode()
        if path == "/settings":
            return 200, "text/html; charset=utf-8", render_page(lang)
        if path == "/api/stackchan/settings":
            return 200, JSON, json.dumps(self.state(lang)).encode()
        return 404, JSON, json.dumps({"error": "not found"}).encode()

    def route_post(
        self, path: str, body: dict[str, Any], local_admin: bool
    ) -> tuple[int, dict[str, Any]] | None:
        """(status, JSON payload) for a settings POST, or None when it is not a settings path.

        The update route checks the release and changes nothing unless the body says
        ``"confirm": true``."""
        prefix = "/api/stackchan/settings/"
        if not path.startswith(prefix) and not path.startswith((FACES, UNIT, PEOPLE)):
            return None
        lang = normalize(str(body.get("lang", "")) or self.language)
        if not local_admin:
            return 403, {"error": t(lang, "settings.local_only")}
        if path.startswith(FACES):
            return self._faces_post(unquote(path[len(FACES) :]), body, lang)
        if path.startswith(UNIT):
            return self._unit_post(unquote(path[len(UNIT) :]), body, lang)
        if path == PEOPLE or path.startswith(PEOPLE + "/"):
            return self._unit_post(unquote(path[len("/api/stackchan/") :]), body, lang)
        rest = path[len(prefix) :]
        try:
            if rest.endswith("/update"):
                device_id = unquote(rest[: -len("/update")])
                try:
                    message = self.update(device_id, lang, dry_run=body.get("confirm") is not True)
                except updater.UpdateRefused as error:
                    return 422, {"error": str(error)}
                return 200, {"message": message}
            body = {k: v for k, v in body.items() if k not in {"lang", "confirm"}}
            return 200, self.save(unquote(rest), body)
        except SettingsError as error:
            return 400, {"error": str(error)}


JSON = "application/json"
FACES = "/api/stackchan/faces/"
UNIT = "/api/stackchan/unit/"
PEOPLE = "/api/stackchan/people"


def render_page(lang: str | None) -> bytes:
    code = normalize(lang)
    strings = catalog(code)
    e = html.escape
    options = "".join(
        f"<option value='{c}'{' selected' if c == code else ''}>{c}</option>" for c in SUPPORTED
    )
    page = f"""<!doctype html><html lang='{code}'><meta charset='utf-8'>
<meta name='viewport' content='width=device-width'>
<title>{e(strings["settings.title"])}</title>
<style>body{{font:16px system-ui;max-width:42rem;margin:1rem auto;padding:0 1rem}}
label{{display:block;margin:.6rem 0 .2rem}}input,textarea,select{{width:100%;box-sizing:border-box}}
section{{border:1px solid #888;border-radius:8px;padding:1rem;margin:1rem 0}}
.row{{display:flex;gap:.5rem}}button{{margin-top:.6rem}}</style>
<h1>{e(strings["settings.title"])}</h1>
<label>{e(strings["settings.language"])}
<select id='lang' onchange="location='/settings?lang='+this.value">{options}</select></label>
<p>{e(strings["settings.host_address"])}: <b id='host'></b></p>
<p id='status' role='status'></p><div id='units'></div>
<script>
const S={json.dumps(strings)};
const status=m=>document.querySelector('#status').textContent=m;
async function call(path,body){{const r=await fetch(path,{{method:'POST',
headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
const d=await r.json();status(r.ok?(d.message||S['settings.saved']):d.error);return r.ok}}
function field(parent,label,el){{const l=document.createElement('label');l.textContent=label;
parent.append(l,el);return el}}
function choice(parent,label,values,current,words){{const el=document.createElement('select');
for(const v of values)el.append(Object.assign(document.createElement('option'),{{value:v,selected:v===current,
textContent:S[words+v]||v}}));return field(parent,label,el)}}
function tick(parent,label,on){{const el=Object.assign(document.createElement('input'),{{type:'checkbox',checked:on}});
el.style.width='auto';return field(parent,label,el)}}
function faceSection(id){{const f=document.createElement('fieldset');
const lg=document.createElement('legend');lg.textContent=S['settings.face'];f.append(lg);
const path='/api/stackchan/faces/'+encodeURIComponent(id);
fetch(path+'?lang={code}').then(r=>r.json().then(d=>({{ok:r.ok,d}}))).then(({{ok,d}})=>{{
if(!ok){{const p=document.createElement('p');p.textContent=d.error;f.append(p);return}}
const v=d.values,c=d.choices;
const style=choice(f,S['settings.face.style'],c.style,v.style,'settings.face.style.');
const colour=choice(f,S['settings.face.colour'],c.colour,v.colour,'settings.face.colour.');
const caps=tick(f,S['settings.face.captions'],v.captions);
const capsize=choice(f,S['settings.face.caption_size'],c.caption_size,v.caption_size,'settings.face.caption_size.');
const flang=choice(f,S['settings.face.lang'],c.lang,v.lang,'settings.lang.');
const tod=tick(f,S['settings.face.tod'],v.tod);
const hrs=field(f,S['settings.face.hours'],Object.assign(document.createElement('input'),{{value:v.tod_hours.join(', ')}}));
if(d.unavailable.length){{const p=document.createElement('p');p.textContent=S['settings.face.unavailable']+' '+d.unavailable.join(', ');f.append(p)}}
if(d.pending){{const p=document.createElement('p');p.textContent=S['settings.face.pending'];f.append(p)}}
const go=document.createElement('button');go.textContent=S['settings.face.save'];
go.onclick=()=>call(path,{{lang:'{code}',style:style.value,colour:colour.value,captions:caps.checked,caption_size:capsize.value,screen_lang:flang.value,tod:tod.checked,
tod_hours:hrs.value.split(/[ ,]+/).filter(x=>x).map(Number)}});
const rs=document.createElement('button');rs.textContent=S['settings.face.reset'];
rs.onclick=()=>call(path+'/reset',{{lang:'{code}'}});
f.append(go,' ',rs)}}).catch(()=>{{}});return f}}
function extrasSection(id){{const f=document.createElement('fieldset');
const lg=document.createElement('legend');lg.textContent=S['settings.extra'];f.append(lg);
const dp='/api/stackchan/faces/'+encodeURIComponent(id);
fetch(dp+'?lang={code}').then(r=>r.json()).then(d=>{{if(!d.choices)return;
const pick=choice(f,S['settings.extra.pick'],d.choices.decorators,d.choices.decorators[0],'settings.decor.');
const show=document.createElement('button');show.textContent=S['settings.extra.show'];
show.onclick=()=>call('/api/stackchan/unit/'+encodeURIComponent(id)+'/decorate',{{lang:'{code}',name:pick.value,seconds:6}});
const stop=document.createElement('button');stop.textContent=S['settings.extra.stop'];
stop.onclick=()=>call('/api/stackchan/unit/'+encodeURIComponent(id)+'/decorate',{{lang:'{code}',name:'none'}});
f.append(show,' ',stop)}}).catch(()=>{{}});return f}}
function reactSection(id){{const f=document.createElement('fieldset');
const lg=document.createElement('legend');lg.textContent=S['settings.react'];f.append(lg);
const path='/api/stackchan/unit/'+encodeURIComponent(id)+'/reactions';
fetch(path+'?lang={code}').then(r=>r.json()).then(d=>{{if(d.error){{const p=document.createElement('p');p.textContent=d.error;f.append(p);return}}
const help=document.createElement('p');help.textContent=S['settings.react.help'];f.append(help);
if(d.builtin){{const b=document.createElement('p');b.textContent=S['settings.react.builtin'];f.append(b)}}
const box=Object.assign(document.createElement('textarea'),{{id:'reactions',rows:10,value:d.text}});f.append(box);
const go=document.createElement('button');go.textContent=S['settings.react.save'];
go.onclick=()=>call(path,{{lang:'{code}',text:box.value}});
const rs=document.createElement('button');rs.textContent=S['settings.react.reset'];
rs.onclick=()=>call(path+'/reset',{{lang:'{code}'}}).then(ok=>{{if(ok)load()}});
f.append(go,' ',rs)}}).catch(()=>{{}});return f}}
function clockSection(id){{const f=document.createElement('fieldset');
const lg=document.createElement('legend');lg.textContent=S['settings.clock'];f.append(lg);
const path='/api/stackchan/unit/'+encodeURIComponent(id)+'/clock';
fetch(path+'?lang={code}').then(r=>r.json()).then(d=>{{if(!d.zones)return;
const el=document.createElement('select');el.id='zone';
for(const z of d.zones)el.append(Object.assign(document.createElement('option'),{{value:z.id,selected:z.id===d.zone,textContent:z.label}}));
field(f,S['settings.clock.zone'],el);
const go=document.createElement('button');go.textContent=S['settings.clock.save'];
go.onclick=()=>call(path,{{lang:'{code}',zone:el.value}});
const sy=document.createElement('button');sy.textContent=S['settings.clock.sync'];
sy.onclick=()=>call(path,{{lang:'{code}',sync:true}});
f.append(go,' ',sy)}}).catch(()=>{{}});return f}}
function toolSection(id,title,label,action,method){{const f=document.createElement('fieldset');
const lg=document.createElement('legend');lg.textContent=title;f.append(lg);
const out=document.createElement('pre');out.style.whiteSpace='pre-wrap';
const go=document.createElement('button');go.textContent=label;
const path='/api/stackchan/unit/'+encodeURIComponent(id)+'/'+action;
go.onclick=async()=>{{const r=await fetch(path+(method==='GET'?'?lang={code}':''),method==='GET'?{{}}:{{method:'POST',
headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{lang:'{code}'}})}});const d=await r.json();
if(d.steps){{out.textContent=d.steps.map(s=>s.line).join('\\n')+'\\n'+(d.summary||'')+(d.fix?'\\n'+d.fix:'')}}
else if(d.version){{out.textContent=['version','tag','image','slot'].map(k=>k+': '+d[k]).join('\\n')+'\\nmemory free: '+Math.round(d.internal_free/1024)+' KB (lowest '+Math.round(d.internal_min/1024)+' KB)'}}
else if(d.lines){{out.textContent=d.lines.join('\\n')}}
else out.textContent=d.error||d.summary||''}};
f.append(go,out);return f}}
function peopleSection(id){{const f=document.createElement('fieldset');
const lg=document.createElement('legend');lg.textContent=S['settings.people'];f.append(lg);
const help=document.createElement('p');help.textContent=S['settings.people.help'];f.append(help);
const list=document.createElement('div');f.append(list);
const draw=d=>{{list.replaceChildren();
if(!d.people.length){{const p=document.createElement('p');p.textContent=S['settings.people.none'];list.append(p)}}
for(const p of d.people){{const row=document.createElement('p');
row.textContent=p.name+' ('+p.colour+', '+p.caption_size+(p.wake_phrase?', '+p.wake_phrase:'')+') ';
const use=document.createElement('button');use.textContent=S['settings.people.use'];
use.onclick=()=>call('/api/stackchan/people/'+encodeURIComponent(p.id)+'/use/'+encodeURIComponent(id),{{lang:'{code}'}});
const rm=document.createElement('button');rm.textContent=S['settings.people.remove'];
rm.onclick=async()=>{{const r=await fetch('/api/stackchan/people/'+encodeURIComponent(p.id)+'/remove',{{method:'POST',
headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{lang:'{code}'}})}});if(r.ok)draw(await r.json())}};
row.append(use,' ',rm);list.append(row)}}}};
fetch('/api/stackchan/people?lang={code}').then(r=>r.json()).then(d=>{{if(!d.people)return;draw(d);
const name=field(f,S['settings.people.name'],document.createElement('input'));name.id='person_name';
const col=choice(f,S['settings.people.colour'],d.choices.colour,'none','settings.face.colour.');
const cap=choice(f,S['settings.people.caption'],d.choices.caption_size,'medium','settings.face.caption_size.');
const wake=field(f,S['settings.people.wake'],document.createElement('input'));
const go=document.createElement('button');go.textContent=S['settings.people.save'];
go.onclick=async()=>{{const r=await fetch('/api/stackchan/people',{{method:'POST',headers:{{'Content-Type':'application/json'}},
body:JSON.stringify({{lang:'{code}',name:name.value,colour:col.value,caption_size:cap.value,wake_phrase:wake.value}})}});
const b=await r.json();if(r.ok){{draw(b);status(S['settings.saved'])}}else status(b.error)}};
f.append(go)}}).catch(()=>{{}});return f}}
{pictures_js(code)}
function unitCard(u){{const s=document.createElement('section');
const h=document.createElement('h2');h.textContent=u.name;s.append(h);
const id=document.createElement('p');id.textContent=S['settings.device_id']+': '+u.device_id;s.append(id);
const on=document.createElement('p');
on.textContent=S['settings.online']+': '+(u.online===null?S['settings.online.unknown']:S[u.online?'settings.online.yes':'settings.online.no']);s.append(on);
const w=document.createElement('p');w.textContent=S['settings.wifi']+': '+S['settings.wifi.'+u.wifi];s.append(w);
const fw=document.createElement('p');
fw.textContent=S['settings.firmware']+': '+(u.firmware_version||S['settings.firmware.unknown']);s.append(fw);
const name=field(s,S['settings.unit_name'],Object.assign(document.createElement('input'),{{value:u.name}}));
const persona=field(s,S['settings.persona'],Object.assign(document.createElement('textarea'),{{value:u.persona,rows:4}}));
const url=field(s,S['settings.llm_url'],Object.assign(document.createElement('input'),{{value:u.llm.url||''}}));
const model=field(s,S['settings.llm_model'],Object.assign(document.createElement('input'),{{value:u.llm.model||''}}));
const key=field(s,S['settings.llm_key_env'],Object.assign(document.createElement('input'),{{value:u.llm.api_key_env||''}}));
const cap=field(s,S['settings.volume_cap'],Object.assign(document.createElement('input'),{{type:'number',min:0,max:100,value:u.volume_cap}}));
const speed=field(s,S['settings.speech_speed'],Object.assign(document.createElement('input'),{{id:'speech_speed',type:'number',min:0.75,max:1.5,step:0.05,value:u.speech_speed}}));
const pitch=field(s,S['settings.speech_pitch'],Object.assign(document.createElement('input'),{{id:'speech_pitch',type:'number',min:-12,max:12,step:1,value:u.speech_pitch}}));
const mute=Object.assign(document.createElement('input'),{{type:'checkbox',checked:u.muted}});
mute.style.width='auto';field(s,S['settings.mute'],mute);
const alarms=field(s,S['settings.alarms']+' ('+S['settings.alarm_time']+', '+S['settings.alarm_label']+')',
Object.assign(document.createElement('textarea'),{{rows:3,
value:u.alarms.map(a=>a.time+' '+a.label).join('\\n')}}));
const save=document.createElement('button');save.textContent=S['settings.save'];
save.onclick=()=>call('/api/stackchan/settings/'+encodeURIComponent(u.device_id),{{name:name.value,
persona:persona.value,llm:{{url:url.value,model:model.value,api_key_env:key.value}},
volume_cap:parseInt(cap.value,10),speech_speed:parseFloat(speed.value),speech_pitch:parseFloat(pitch.value),muted:mute.checked,
alarms:alarms.value.split('\\n').filter(x=>x.trim()).map(x=>{{const [time,...rest]=x.trim().split(/\\s+/);
return {{time,label:rest.join(' ')}}}})}});
s.append(faceSection(u.device_id),picSection(u.device_id));
s.append(extrasSection(u.device_id),reactSection(u.device_id),clockSection(u.device_id),
toolSection(u.device_id,S['settings.net'],S['settings.net.run'],'network-test','POST'),
toolSection(u.device_id,S['settings.details'],S['settings.details.show'],'details','GET'),
toolSection(u.device_id,S['settings.games'],S['settings.games.show'],'games','GET'),
peopleSection(u.device_id));
const upd=document.createElement('button');upd.textContent=S['settings.update'];
const upath='/api/stackchan/settings/'+encodeURIComponent(u.device_id)+'/update';
upd.onclick=()=>call(upath,{{lang:'{code}'}});
const go=document.createElement('button');go.textContent=S['settings.update_confirm'];
go.onclick=()=>{{if(confirm(S['settings.update_confirm_ask']))call(upath,{{lang:'{code}',confirm:true}})}};
s.append(save,' ',upd,' ',go);return s}}
async function load(){{const r=await fetch('/api/stackchan/settings?lang={code}');
const d=await r.json();if(!r.ok){{status(d.error);return}}
document.querySelector('#host').textContent=d.host_address;
const box=document.querySelector('#units');box.replaceChildren();
if(!d.units.length)status(S['settings.no_units']);
if(d.units.length<2){{for(const u of d.units)box.append(unitCard(u));return}}
const pick=document.createElement('select');pick.id='unitpick';
for(const u of d.units)pick.append(Object.assign(document.createElement('option'),{{value:u.device_id,textContent:u.name}}));
let keep=null;try{{keep=sessionStorage.getItem('unit')}}catch(e){{}}
pick.value=d.units.some(u=>u.device_id===keep)?keep:d.default_unit;
const show=()=>{{try{{sessionStorage.setItem('unit',pick.value)}}catch(e){{}}box.querySelectorAll('section').forEach(x=>x.remove());
box.append(unitCard(d.units.find(u=>u.device_id===pick.value)))}};
pick.onchange=show;const lab=document.createElement('label');lab.textContent=S['settings.unit_pick'];lab.append(pick);
box.prepend(lab);show()}}
load();
</script></html>"""
    return page.encode("utf-8")
