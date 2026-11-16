# ruff: noqa: E501
"""The core settings page: one small local page, no Home, no household data.

``SettingsBackend`` holds the logic (testable with no server); ``render_page`` makes the HTML.
The dashboard server routes /settings and /api/stackchan/settings* to it, local administrator only.
"""

from __future__ import annotations

import html
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from maipai_body.bodies.stackchan import updater
from maipai_body.i18n import SUPPORTED, catalog, normalize, t
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
    ) -> None:
        self.devices, self.store = devices, store or UnitSettingsStore()
        self.live = live or (lambda _device_id: {})
        self.host_address = host_address
        self.update_source, self.public_key = update_source, public_key
        self.push, self.preset, self.language = push, preset, normalize(language)

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
                    "muted": own.get("muted", bool(live.get("muted", False))),
                    "firmware_version": live.get("firmware_version"),
                }
            )
        return {
            "host_address": self.host_address,
            "language": normalize(lang or self.language),
            "update_source_set": bool(self.update_source),
            "units": units,
        }

    def save(self, device_id: str, values: dict[str, Any]) -> dict[str, Any]:
        if device_id not in self.devices():
            raise SettingsError("That unit is not paired. Pair it first, then open its settings.")
        return self.store.update(device_id, values)

    def update(self, device_id: str, lang: str | None = None, *, dry_run: bool = False) -> str:
        """The Update button: check the signed release, then push it over the air."""
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
function unitCard(u){{const s=document.createElement('section');
const h=document.createElement('h2');h.textContent=u.name;s.append(h);
const id=document.createElement('p');id.textContent=S['settings.device_id']+': '+u.device_id;s.append(id);
const w=document.createElement('p');w.textContent=S['settings.wifi']+': '+S['settings.wifi.'+u.wifi];s.append(w);
const fw=document.createElement('p');
fw.textContent=S['settings.firmware']+': '+(u.firmware_version||S['settings.firmware.unknown']);s.append(fw);
const name=field(s,S['settings.unit_name'],Object.assign(document.createElement('input'),{{value:u.name}}));
const persona=field(s,S['settings.persona'],Object.assign(document.createElement('textarea'),{{value:u.persona,rows:4}}));
const url=field(s,S['settings.llm_url'],Object.assign(document.createElement('input'),{{value:u.llm.url||''}}));
const model=field(s,S['settings.llm_model'],Object.assign(document.createElement('input'),{{value:u.llm.model||''}}));
const key=field(s,S['settings.llm_key_env'],Object.assign(document.createElement('input'),{{value:u.llm.api_key_env||''}}));
const cap=field(s,S['settings.volume_cap'],Object.assign(document.createElement('input'),{{type:'number',min:0,max:100,value:u.volume_cap}}));
const mute=Object.assign(document.createElement('input'),{{type:'checkbox',checked:u.muted}});
mute.style.width='auto';field(s,S['settings.mute'],mute);
const alarms=field(s,S['settings.alarms']+' ('+S['settings.alarm_time']+', '+S['settings.alarm_label']+')',
Object.assign(document.createElement('textarea'),{{rows:3,
value:u.alarms.map(a=>a.time+' '+a.label).join('\\n')}}));
const save=document.createElement('button');save.textContent=S['settings.save'];
save.onclick=()=>call('/api/stackchan/settings/'+encodeURIComponent(u.device_id),{{name:name.value,
persona:persona.value,llm:{{url:url.value,model:model.value,api_key_env:key.value}},
volume_cap:parseInt(cap.value,10),muted:mute.checked,
alarms:alarms.value.split('\\n').filter(x=>x.trim()).map(x=>{{const [time,...rest]=x.trim().split(/\\s+/);
return {{time,label:rest.join(' ')}}}})}});
const upd=document.createElement('button');upd.textContent=S['settings.update'];
upd.onclick=()=>call('/api/stackchan/settings/'+encodeURIComponent(u.device_id)+'/update',{{lang:'{code}'}});
s.append(save,' ',upd);return s}}
async function load(){{const r=await fetch('/api/stackchan/settings?lang={code}');
const d=await r.json();if(!r.ok){{status(d.error);return}}
document.querySelector('#host').textContent=d.host_address;
const box=document.querySelector('#units');box.replaceChildren();
if(!d.units.length)status(S['settings.no_units']);
for(const u of d.units)box.append(unitCard(u))}}
load();
</script></html>"""
    return page.encode("utf-8")
