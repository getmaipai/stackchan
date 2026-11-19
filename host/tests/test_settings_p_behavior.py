# ruff: noqa: E501
"""The Behavior page in the new dashboard look: the keys are in the page script, the script parses in every language, the front view keeps six rows before the fold, and the rows save through the calls the old builder made."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import i18n
from maipai_body.settings_page import render_page
from maipai_body.settings_ui_p_behavior import JS

KEYS = [
    "more/behavior",
    "more/behavior-look",
    "more/behavior-clock",
    "more/behavior-timers",
    "more/behavior-alarms",
    "more/behavior-people",
    "more/behavior-person",
    "more/behavior-pages",
    "more/behavior-react",
]
EM = chr(0x2014)
NODE = shutil.which("node")

HARNESS = r"""
const fs=require('fs');const src=fs.readFileSync(process.argv[2],'utf8');
const calls=[];const kinds=o=>o;
const h=(tag,props,...k)=>{const e={tag,props:props||{},kids:k.flat(9),append(...a){this.kids.push(...a)},replaceChildren(...a){this.kids=a}};return e};
const SVG=()=>({}),IC={back:'b',chev:'c'},T=s=>s,S=new Proxy({},{get:(_,k)=>String(k)});
const add=(el,...a)=>{el.kids=el.kids||[];el.kids.push(...a.flat(9).filter(x=>x!=null&&x!==false))};
const detailHead=()=>[{kind:'head'}],grp=(t,...rows)=>({kind:'grp',rows:rows.filter(Boolean)}),rowEl=o=>({kind:'row',o}),
 swRow=(l,on,fn,o)=>({kind:'row',sw:true,l,fn}),sgRow=(l,it,val,fn)=>({kind:'row',sg:true,l,fn}),slRow=(l,a,b,c,val,fmt,fn)=>({kind:'row',sl:true,l,fn}),
 moreFold=(...rows)=>({kind:'fold',rows:rows.filter(Boolean)}),need=()=>({kind:'need'});
const nav=(p,d)=>calls.push(['nav',p,d]),toast=(m,k)=>calls.push(['toast',m,k]);
let ok=true;
const reply=()=>({ok,d:{}});
const dev=async b=>{calls.push(['dev',b]);return reply()},save=async(p,b)=>{calls.push(['save',p,b]);return reply()},unitSet=async(id,b)=>{calls.push(['unitSet',b]);return reply()};
const unitPath=(id,w)=>'unit/'+w,facePath=id=>'face';
const FIX={'/api/stackchan/people':{people:[{id:'a',name:'Ann',wake_phrase:'hi'}],choices:{color:['none','mint'],caption_size:['small','medium']}},
 'unit/clock':{zone:'UTC',zones:[{id:'UTC',label:'UTC'}]},'unit/prefs':{values:{turn_to_faces:'off'},features:{look:true},look:null}};
const api=async p=>({ok:true,d:FIX[p]||{}});
const CXD={o:{saved:{idle_movement:'calm'}}};
const cx=async()=>CXD;CXD.fv={values:{clock24:false,clock_style:'digits',clock_idle_s:0},features:null};
const UNIT={device_id:'u1',alarms:[{time:'07:00',label:'x',days:['mon']}]};
const swatches=()=>({}),ask=async()=>true,swipePagesCard=async()=>({}),reactCard=async()=>({});
const DETAIL={};
eval(src);
(async()=>{const out={rows:{}};
 for(const k of Object.keys(DETAIL)){const v={kids:[]};await DETAIL[k](v);out.rows[k]=v.kids.map(x=>x.kind||x.tag)}
 const v={kids:[]};await DETAIL['more/behavior'](v);const g=v.kids.find(x=>x.kind==='grp'),f=v.kids.find(x=>x.kind==='fold');
 out.front=g.rows.length;out.fold=f?f.rows.length:0;out.foldLast=v.kids[v.kids.length-1]===f;
 await g.rows[0].fn('lively');await g.rows[1].fn(true);ok=false;out.failed=await g.rows[1].fn(true);ok=true;
 await g.rows[2].o.go();
 const a={kids:[]};await DETAIL['more/behavior-alarms'](a);
 out.calls=calls;console.log(JSON.stringify(out))})().catch(e=>{console.error(e);process.exit(1)});
"""


def test_the_script_sets_every_key_and_has_no_em_dash() -> None:
    for key in KEYS:
        assert f"DETAIL['{key}']=" in JS, key
    assert EM not in JS
    for code in i18n.SUPPORTED:
        page = render_page(code).decode()
        for key in KEYS:
            assert f"DETAIL['{key}']=" in page, (code, key)


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_the_whole_page_script_parses_in_every_language() -> None:
    for code in i18n.SUPPORTED:
        page = render_page(code).decode()
        script = re.search(r"<script>([\s\S]*)</script>", page)
        assert script is not None
        result = subprocess.run([NODE, "--check", "/dev/stdin"], input=script.group(1), capture_output=True, text=True)
        assert result.returncode == 0, (code, result.stderr)


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_the_front_view_has_six_rows_then_one_fold_and_the_rows_save(tmp_path: Path) -> None:
    (tmp_path / "p.js").write_text(JS)
    (tmp_path / "run.js").write_text(HARNESS)
    result = subprocess.run([NODE, str(tmp_path / "run.js"), str(tmp_path / "p.js")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["front"] == 6
    assert out["fold"] >= 1 and out["foldLast"]
    assert set(out["rows"]) == set(KEYS)
    assert out["failed"] is False
    calls = out["calls"]
    assert ["dev", {"idle_movement": "lively"}] in calls
    assert ["dev", {"look_speaker": True}] in calls
    assert ["nav", "more", "behavior-clock"] in calls
