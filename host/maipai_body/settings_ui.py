# ruff: noqa: E501
"""The look and the behavior of the settings page: styles, the live face drawing and every panel.

``render_page`` in ``settings_page`` fills ``__STRINGS__`` and ``__LANG__`` and adds the picture-face panel. The page
is plain HTML, CSS and JavaScript with no outside file, no font download and no network call except to this host.
Colors are tokens (CSS variables) that follow the browser's light or dark setting or the page's own switch.
"""

from __future__ import annotations

from maipai_body.banner_shapes import banner_js
from maipai_body.face_shapes import face_js
from maipai_body.overlay_shapes import overlay_js
from maipai_body.settings_ui_lock import JS_LOCK
from maipai_body.settings_ui_character import JS_CHARACTER
from maipai_body.settings_ui_family import JS_FAMILY
from maipai_body.settings_ui_link import JS_LINK
from maipai_body.settings_ui_pages import JS_PAGES_FULL
from maipai_body.settings_ui_polish import JS_POLISH

CSS = r"""
:root{color-scheme:light dark;--bg:#f3f4f7;--rail:#ffffff;--card:#ffffff;--card2:#f1f2f6;--line:#dcdfe6;--fg:#15171c;--muted:#5b616e;--accent:#35c79a;--on-accent:#06130e;--ok:#14855f;--warn:#9a6200;--bad:#b3261e;--shadow:0 1px 2px rgba(20,24,40,.06),0 12px 32px -16px rgba(20,24,40,.18);--screen:#000;--r:20px}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0b0c0f;--rail:#101216;--card:#15171c;--card2:#1c1f26;--line:#262a32;--fg:#eceef2;--muted:#9aa1ad;--ok:#5fe0b5;--warn:#f0b64a;--bad:#ff8f86;--shadow:0 1px 2px rgba(0,0,0,.4),0 16px 40px -18px rgba(0,0,0,.7)}}
:root[data-theme=dark]{color-scheme:dark;--bg:#0b0c0f;--rail:#101216;--card:#15171c;--card2:#1c1f26;--line:#262a32;--fg:#eceef2;--muted:#9aa1ad;--ok:#5fe0b5;--warn:#f0b64a;--bad:#ff8f86;--shadow:0 1px 2px rgba(0,0,0,.4),0 16px 40px -18px rgba(0,0,0,.7)}
:root[data-theme=light]{color-scheme:light}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;min-height:100vh}
h1,h2,h3,p{margin:0}
button,input,select,textarea{font:inherit;color:inherit}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.skip{position:absolute;left:-999px;top:8px;background:var(--accent);color:var(--on-accent);padding:8px 14px;border-radius:12px;z-index:50}
.skip:focus{left:8px}
.app{display:grid;grid-template-columns:240px minmax(0,1fr);min-height:100vh}
.rail{position:sticky;top:0;height:100vh;background:var(--rail);border-right:1px solid var(--line);padding:24px 14px;display:flex;flex-direction:column;gap:20px}
.brand{display:flex;align-items:center;gap:12px;padding:0 10px;font-weight:700;font-size:1.05rem;letter-spacing:-.01em}
.logo{width:36px;height:36px;border-radius:12px;background:#000;display:grid;place-items:center;box-shadow:0 0 22px -4px var(--accent)}
.logo i{display:block;width:6px;height:10px;border-radius:3px;background:var(--accent);margin:0 3px;box-shadow:0 0 8px var(--accent)}
.logo{display:flex;align-items:center;justify-content:center}
.nav{display:flex;flex-direction:column;gap:4px}
.nav button{display:flex;align-items:center;gap:12px;min-height:46px;padding:0 14px;border:0;border-radius:14px;background:none;cursor:pointer;color:var(--muted);text-align:left;font-weight:600}
.nav button:hover{background:var(--card2);color:var(--fg)}
.nav button[aria-current=page]{background:color-mix(in srgb,var(--accent) 18%,transparent);color:var(--fg);box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--accent) 60%,transparent)}
.nav svg{width:22px;height:22px;flex:none;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.railfoot{margin-top:auto;display:flex;flex-direction:column;gap:12px;padding:0 6px}
.main{min-width:0;padding:0 clamp(16px,3vw,40px) 64px;max-width:1240px;width:100%}
.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(14px);padding:16px 0 12px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
.chips{display:flex;gap:8px;overflow-x:auto;padding:4px 2px;scrollbar-width:none}
.chip{display:inline-flex;align-items:center;gap:10px;min-height:44px;padding:0 16px 0 12px;border-radius:999px;border:1.5px solid var(--line);background:var(--card);cursor:pointer;font-weight:600;white-space:nowrap}
.chip[aria-selected=true]{border-color:var(--chipc,var(--accent));box-shadow:0 0 0 3px color-mix(in srgb,var(--chipc,var(--accent)) 24%,transparent)}
.dot{width:12px;height:12px;border-radius:50%;background:var(--chipc,var(--accent));flex:none}
.state{font-size:.78rem;font-weight:600;color:var(--muted);display:inline-flex;align-items:center;gap:6px}
.state::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--muted)}
.state.on{color:var(--ok)}.state.on::before{background:var(--ok);box-shadow:0 0 8px var(--ok)}
h1.title{font-size:clamp(1.5rem,3vw,2rem);letter-spacing:-.02em;margin:20px 0 4px}
.sub{color:var(--muted);max-width:68ch}
.panel{display:none;animation:rise .25s ease both}.panel.on{display:block}
@keyframes rise{from{transform:translateY(6px)}to{transform:none}}
.grid{display:grid;gap:18px;margin-top:18px;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));align-items:start}
.two{display:grid;gap:18px;margin-top:18px;grid-template-columns:minmax(0,1fr)}
@media(min-width:1100px){.two{grid-template-columns:minmax(380px,460px) minmax(0,1fr);align-items:start}.two>.sticky{position:sticky;top:84px}}
.stack{display:grid;gap:18px;align-content:start}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:22px;box-shadow:var(--shadow);display:grid;gap:16px;align-content:start;min-width:0}
.card h3{font-size:1.05rem;letter-spacing:-.01em;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.hint{color:var(--muted);font-size:.9rem}
.badge{font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:999px;background:var(--card2);color:var(--muted);border:1px solid var(--line)}
.banner{border-radius:14px;padding:12px 16px;background:color-mix(in srgb,var(--warn) 14%,var(--card));border:1px solid color-mix(in srgb,var(--warn) 40%,transparent);font-size:.92rem}
.banner.bad{background:color-mix(in srgb,var(--bad) 12%,var(--card));border-color:color-mix(in srgb,var(--bad) 40%,transparent)}
.screen{background:var(--screen);border-radius:22px;border:8px solid #23252b;overflow:hidden;line-height:0;box-shadow:0 0 90px -24px color-mix(in srgb,var(--accent) 60%,transparent),0 0 0 1px var(--line)}
.screen canvas{width:100%;height:auto;aspect-ratio:4/3;display:block}
.pv{display:grid;gap:14px}
.seg{display:flex;flex-wrap:wrap;gap:6px;background:var(--card2);padding:5px;border-radius:16px;border:1px solid var(--line)}
.seg button{flex:1 1 auto;min-height:40px;padding:0 14px;border:0;border-radius:12px;background:none;cursor:pointer;font-weight:600;color:var(--muted)}
.seg button[aria-checked=true]{background:var(--card);color:var(--fg);box-shadow:0 1px 3px rgba(0,0,0,.25),inset 0 0 0 1.5px var(--accent)}
.seg button:disabled{opacity:.5;cursor:not-allowed}
.row{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:48px}
.row .lbl{display:grid;gap:2px;min-width:0}
.row .lbl b{font-weight:600}
.row .lbl span{color:var(--muted);font-size:.86rem}
.sw{width:54px;height:32px;border-radius:999px;border:0;background:var(--line);position:relative;cursor:pointer;flex:none;transition:background .2s}
.sw::after{content:"";position:absolute;top:4px;left:4px;width:24px;height:24px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.4);transition:transform .2s}
.sw[aria-checked=true]{background:var(--accent)}.sw[aria-checked=true]::after{transform:translateX(22px)}
.sw:disabled,.off{opacity:.5;cursor:not-allowed}
.slide{display:grid;gap:8px}
.slide .head{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.slide output{font-variant-numeric:tabular-nums;font-weight:700}
.slide .ends{display:flex;justify-content:space-between;color:var(--muted);font-size:.78rem}
input[type=color]{width:56px;height:46px;padding:3px;border-radius:14px;border:1.5px solid var(--line);background:var(--card2);cursor:pointer}
input[type=range]{width:100%;height:32px;accent-color:var(--accent);background:none;margin:0}
input[type=text],input[type=password],input[type=number],input[type=time],select,textarea{width:100%;min-height:46px;padding:10px 14px;border-radius:14px;border:1.5px solid var(--line);background:var(--card2);outline-offset:0}
textarea{resize:vertical;min-height:96px}
input:focus,select:focus,textarea:focus{border-color:var(--accent)}
label.f{display:grid;gap:6px;font-size:.88rem;color:var(--muted);font-weight:600}
.btn{min-height:46px;padding:0 20px;border-radius:14px;border:1.5px solid var(--line);background:var(--card2);cursor:pointer;font-weight:600;display:inline-flex;align-items:center;justify-content:center;gap:8px}
.btn:hover:not(:disabled){border-color:var(--accent)}
.btn.pri{background:var(--accent);color:var(--on-accent);border-color:transparent}
.btn.bad{border-color:color-mix(in srgb,var(--bad) 60%,transparent);color:var(--bad)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btns{display:flex;flex-wrap:wrap;gap:10px}
.tiles{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(112px,1fr))}
.tile{background:var(--card2);border:1.5px solid var(--line);border-radius:16px;padding:8px 8px 10px;cursor:pointer;display:grid;gap:6px;text-align:center;font-weight:600;font-size:.84rem}
.tile .screen{border-width:3px;border-radius:10px;box-shadow:none}
.tile[aria-checked=true]{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 25%,transparent)}
.tile:disabled{opacity:.45;cursor:not-allowed}
.sws{display:flex;flex-wrap:wrap;gap:10px}
.swatch{width:44px;height:44px;border-radius:50%;border:3px solid var(--card);box-shadow:0 0 0 1.5px var(--line);cursor:pointer;padding:0;position:relative}
.swatch[aria-checked=true]{box-shadow:0 0 0 3px var(--fg)}
.swatch.none{background:repeating-conic-gradient(#f4f4f4 0 25%,#9a9a9a 0 50%) 0 0/12px 12px}
.pills{display:flex;flex-wrap:wrap;gap:8px}
.pill{min-height:40px;padding:0 14px;border-radius:999px;border:1.5px solid var(--line);background:var(--card2);cursor:pointer;font-weight:600}
.pill[aria-pressed=true]{background:var(--accent);color:var(--on-accent);border-color:transparent}
.pill.ovp{display:inline-flex;flex-direction:column;align-items:center;gap:4px;padding:6px 6px 8px;border-radius:14px;min-width:108px}
.ovthumb{width:96px;height:72px;border-radius:8px;background:#000;display:block}
.kv{display:grid;grid-template-columns:minmax(110px,40%) 1fr;gap:8px 16px;font-size:.95rem}
.kv dt{color:var(--muted)}.kv dd{margin:0;overflow-wrap:anywhere;font-weight:600}
.stat{display:grid;gap:4px;padding:16px;border-radius:16px;background:var(--card2);border:1px solid var(--line)}
.stat b{font-size:1.5rem;letter-spacing:-.02em}.stat span{color:var(--muted);font-size:.84rem}
.stats{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.meter{height:10px;border-radius:99px;background:var(--card2);overflow:hidden;border:1px solid var(--line)}.meter i{display:block;height:100%;background:var(--accent);border-radius:99px}
.list{display:grid;gap:10px}
.item{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:12px;border-radius:16px;background:var(--card2);border:1px solid var(--line)}
.item>.grow{flex:1 1 160px;min-width:0}
.steps{display:grid;gap:8px;margin:0;padding:0;list-style:none}
.steps li{display:flex;gap:10px;align-items:center}
.steps li::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--ok);flex:none}
.steps li.warn::before{background:var(--warn)}.steps li.fail::before{background:var(--bad)}
.empty{border:1.5px dashed var(--line);border-radius:16px;padding:22px;text-align:center;color:var(--muted)}
.hrs{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(110px,1fr))}
.rx{display:grid;gap:8px;grid-template-columns:minmax(120px,1.4fr) repeat(4,minmax(86px,1fr)) auto;align-items:end}
.rx.h{align-items:center;color:var(--muted);font-size:.8rem;font-weight:700}
@media(max-width:860px){.rx{grid-template-columns:1fr 1fr}.rx.h{display:none}.rx>:first-child{grid-column:1/-1}}
.days{display:flex;gap:4px;flex-wrap:wrap}
.days button{min-width:44px;min-height:40px;border-radius:12px}
.toasts{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);display:grid;gap:8px;z-index:60;width:min(92vw,460px);pointer-events:none}
.toast{pointer-events:auto;background:var(--fg);color:var(--bg);border-radius:16px;padding:12px 18px;box-shadow:var(--shadow);font-weight:600;animation:rise .2s ease both}
.toast.bad{background:var(--bad);color:#fff}.toast.warn{background:var(--warn);color:#fff}
dialog{border:1px solid var(--line);border-radius:22px;background:var(--card);color:var(--fg);padding:24px;max-width:min(92vw,440px);box-shadow:var(--shadow)}
dialog::backdrop{background:rgba(0,0,0,.55)}
dialog p{margin-bottom:18px}
.big{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.bigb{min-height:96px;border-radius:20px;border:1.5px solid var(--line);background:var(--card2);cursor:pointer;display:grid;place-items:center;gap:6px;padding:14px 10px;font-weight:700;text-align:center;position:relative}
.bigb svg{width:28px;height:28px;stroke:var(--accent);fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.bigb:hover:not(:disabled){border-color:var(--accent)}
.bigb:active:not(:disabled),.bigb[aria-pressed=true]{background:color-mix(in srgb,var(--accent) 22%,var(--card2));border-color:var(--accent)}
.bigb:disabled{opacity:.5;cursor:not-allowed}
.busy{pointer-events:none}
.busy::after{content:"";position:absolute;top:10px;right:10px;width:16px;height:16px;border-radius:50%;border:3px solid var(--line);border-top-color:var(--accent);animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.pad{position:relative;width:min(100%,300px);aspect-ratio:4/3;margin:0 auto;border-radius:20px;background:var(--card2);border:1.5px solid var(--line);touch-action:none;cursor:crosshair;background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px);background-size:50% 50%;background-position:center}
.pad i{position:absolute;width:28px;height:28px;margin:-14px;border-radius:50%;background:var(--accent);box-shadow:0 0 18px var(--accent);pointer-events:none}
.arrows{display:grid;grid-template-columns:repeat(3,56px);grid-template-rows:repeat(3,48px);gap:6px;justify-content:center}
.arrows .btn{padding:0}
.photo{width:100%;border-radius:16px;border:1px solid var(--line);display:block}
a.lnk{color:var(--fg);font-weight:600;text-underline-offset:3px;text-decoration-color:var(--accent)}
ol.how{margin:0;padding-left:22px;display:grid;gap:8px}
.tabs{display:none}
@media(max-width:959px){
 .app{display:block}
 .rail{position:fixed;inset:auto 0 0 0;top:auto;height:auto;z-index:40;flex-direction:row;padding:6px 8px calc(6px + env(safe-area-inset-bottom));border-right:0;border-top:1px solid var(--line);gap:0}
 .rail .brand,.rail .railfoot{display:none}
 .nav{flex-direction:row;gap:2px;width:100%;overflow-x:auto;scrollbar-width:none;justify-content:space-between}
 .nav button{flex-direction:column;gap:2px;min-height:56px;padding:6px 2px;font-size:.6rem;line-height:1.15;min-width:0;flex:1 1 0;justify-content:center;text-align:center}
 .main{padding-bottom:120px}
 .toasts{bottom:92px}
 .tabs{display:flex;gap:8px;align-items:center}
 .card{padding:18px}
 .big{grid-template-columns:repeat(2,minmax(0,1fr))}
 .bigb{min-height:84px}
 .nav button{overflow:hidden;font-size:.56rem;letter-spacing:-.02em}
}
@media(max-width:430px){.nav button{font-size:.5rem;letter-spacing:-.03em}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

JS = r"""
const BASE={lang:'__LANG__'},LANG='__LANG__';
try{const th=localStorage.getItem('theme');if(th&&th!=='auto')document.documentElement.setAttribute('data-theme',th)}catch(e){}
const T=k=>S['settings.ui.'+k]||k;
const $=(s,r)=>(r||document).querySelector(s);
const ICO={packs:'M4 7l8-4 8 4v10l-8 4-8-4zM4 7l8 4 8-4M12 11v10',home:'M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10',remote:'M12 2v4M12 18v4M2 12h4M18 12h4M12 8l-3 3 3 3 3-3z',look:'M12 3a9 9 0 100 18 9 9 0 000-18zM9 10v2M15 10v2M9 15c1.5 1.4 4.5 1.4 6 0',voice:'M12 3a3 3 0 013 3v6a3 3 0 01-6 0V6a3 3 0 013-3zM5 11a7 7 0 0014 0M12 18v3',network:'M2 9a15 15 0 0120 0M5 12.5a10 10 0 0114 0M8.5 16a5 5 0 017 0M12 19.5h.01',behavior:'M4 6h16M4 12h16M4 18h16M8 4v4M16 10v4M10 16v4',play:'M6 12h4M8 10v4M15 11h.01M18 13h.01M17 7H7a5 5 0 00-4.9 6l.7 3.6A2.5 2.5 0 007.3 17.8l.9-1.3h7.6l.9 1.3a2.5 2.5 0 004.5-1.2l.7-3.6A5 5 0 0017 7z',system:'M12 8a4 4 0 100 8 4 4 0 000-8zM12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1'};
function h(tag,props,...kids){const el=document.createElement(tag);
 for(const k in props||{}){const v=props[k];if(v==null||v===false)continue;
  if(k==='class')el.className=v;else if(k.startsWith('on'))el.addEventListener(k.slice(2),v);
  else if(k==='value'||k==='checked'||k==='disabled'||k==='selected'||k==='textContent')el[k]=v;
  else el.setAttribute(k,v===true?'':v)}
 const add=c=>{if(c==null||c===false)return;if(Array.isArray(c))c.forEach(add);else el.append(c instanceof Node?c:document.createTextNode(String(c)))};
 kids.forEach(add);return el}
function ico(name){const s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('viewBox','0 0 24 24');s.setAttribute('aria-hidden','true');
 const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',ICO[name]);s.append(p);return s}
function toast(msg,kind){if(!msg)return;const box=$('#toasts');const t=h('div',{class:'toast'+(kind?' '+kind:'')},msg);box.append(t);setTimeout(()=>t.remove(),kind==='bad'?7000:3200)}
async function api(path,body){try{
 const url=body===undefined?path+(path.includes('?')?'&':'?')+'lang='+LANG:path;
 const r=await fetch(url,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({},BASE,body))});
 let d={};try{d=await r.json()}catch(e){}return{ok:r.ok,d,status:r.status}}
 catch(e){return{ok:false,d:{error:T('net_error')}}}}
async function save(path,body,quiet){const r=await api(path,body);
 if(r.ok){if(r.d.pushed===false)toast(r.d.message,'warn');else if(!quiet)toast(r.d.message||S['settings.saved'])}
 else toast(r.d.error||T('net_error'),'bad');return r}
const unitPath=(id,w)=>'/api/stackchan/unit/'+encodeURIComponent(id)+'/'+w;
const facePath=id=>'/api/stackchan/faces/'+encodeURIComponent(id);
const setPath=id=>'/api/stackchan/settings/'+encodeURIComponent(id);
const pretty=v=>v==='none'?T('react.none'):String(v).replace(/_/g,' ').replace(/^./,c=>c.toUpperCase());
let seq=0;const uid=()=>'f'+(++seq);
function card(title,desc,...kids){return h('section',{class:'card'},title?h('h3',{},title):null,desc?h('p',{class:'hint'},desc):null,...kids)}
function soonBadge(){return h('span',{class:'badge'},T('soon'))}
function toggle(label,help,on,fn,off){const id=uid();let v=!!on;
 const b=h('button',{type:'button',role:'switch',class:'sw','aria-checked':String(v),'aria-labelledby':id,disabled:!!off,onclick:async()=>{if(off)return;const nv=!v;b.setAttribute('aria-checked',String(nv));const ok=await fn(nv);if(ok===false)b.setAttribute('aria-checked',String(v));else v=nv}});
 return h('div',{class:'row'+(off?' off':'')},h('div',{class:'lbl'},h('b',{id},label,off?[' ',soonBadge()]:null),help?h('span',{},help):null),b)}
function seg(label,items,val,fn,off){const g=h('div',{class:'seg',role:'radiogroup','aria-label':label});
 const draw=()=>g.querySelectorAll('button').forEach(b=>b.setAttribute('aria-checked',String(b.dataset.v===String(val))));
 for(const it of items)g.append(h('button',{type:'button',role:'radio','data-v':it.v,disabled:!!off||!!it.off,title:it.off?T('soon'):null,onclick:async()=>{const old=val;val=it.v;draw();const ok=await fn(it.v);if(ok===false){val=old;draw()}},
  onkeydown:e=>{const bs=[...g.querySelectorAll('button:not(:disabled)')],i=bs.indexOf(e.target);if(e.key==='ArrowRight'||e.key==='ArrowDown'){e.preventDefault();bs[(i+1)%bs.length].focus();bs[(i+1)%bs.length].click()}if(e.key==='ArrowLeft'||e.key==='ArrowUp'){e.preventDefault();bs[(i+bs.length-1)%bs.length].focus();bs[(i+bs.length-1)%bs.length].click()}}},it.t));
 draw();return g}
function slider(label,min,max,step,val,fmt,live,done,ends,off){const id=uid();const out=h('output',{for:id},fmt(val));
 const inp=h('input',{id,type:'range',min,max,step,value:val,disabled:!!off,'aria-valuetext':fmt(val)});
 inp.addEventListener('input',()=>{const v=Number(inp.value);out.textContent=fmt(v);inp.setAttribute('aria-valuetext',fmt(v));if(live)live(v)});
 inp.addEventListener('change',()=>done&&done(Number(inp.value)));
 return h('div',{class:'slide'+(off?' off':'')},h('div',{class:'head'},h('label',{for:id,class:'f'},label,off?[' ',soonBadge()]:null),out),inp,ends?h('div',{class:'ends'},h('span',{},ends[0]),h('span',{},ends[1])):null)}
function swatches(label,vals,val,fn,withNone){const g=h('div',{class:'sws',role:'radiogroup','aria-label':label});
 const draw=()=>g.querySelectorAll('button').forEach(b=>b.setAttribute('aria-checked',String(b.dataset.v===val)));
 for(const c of vals)g.append(h('button',{type:'button',role:'radio','data-v':c,class:'swatch'+(c==='none'?' none':''),style:c==='none'?null:'background:'+PAL[c],title:S['settings.face.color.'+c]||c,'aria-label':S['settings.face.color.'+c]||c,onclick:async()=>{const old=val;val=c;draw();const ok=await fn(c);if(ok===false){val=old;draw()}}}));
 draw();g.redraw=v=>{val=v;draw()};return g}
function field(label,el){return h('label',{class:'f'},label,el)}
function ask(text,okLabel){return new Promise(res=>{const d=h('dialog',{},h('p',{},text),h('div',{class:'btns'},
 h('button',{class:'btn bad',type:'button',onclick:()=>{d.close('ok')}},okLabel),h('button',{class:'btn',type:'button',onclick:()=>d.close('no')},T('cancel'))));
 d.addEventListener('close',()=>{res(d.returnValue==='ok');d.remove()});document.body.append(d);d.showModal()})}
function loading(el){el.append(h('div',{class:'empty'},'...'))}

/* ---- the face drawing: same shapes as the unit's styles (320 by 240 screen) ---- */
const PAL={none:'#f4f4f4',mint:'#5fe0b5',sky:'#6cc3ff',amber:'#ffbf47',rose:'#ff8fa3',lilac:'#b48cff',lime:'#b9e65c',coral:'#ff7a5c'};
const ledName=v=>Object.keys(PAL).find(k=>k!=='none'&&PAL[k]===String(v).toLowerCase())||'off';
const colorOf=c=>PAL[c]||(/^#[0-9a-f]{6}$/i.test(c)?c:PAL.none);
/*__FACE_SHAPES__*/
/* the stock skin as shipped: its own look rows from the table of the core (the other styles are the shape model above) */
const GEO={stock:{d:20,x:70,y:-8,my:46,mo:2,mw:90,mt:6,stock:1}};
const LK={};FT.emotions.forEach((e,i)=>{const k=FT.looks[i],m=k.stock.mouth;LK[e]={l:k.stock.lid,b:k.stock.from_bottom,r:k.stock.tilt,s:k.stock.scale,m:m,t:k.tint}});
const STL={neutral:'neutral',happy:'happy',sad:'sad',angry:'angry',thinking:'doubt',sleepy:'sleepy',speaking:'neutral',love:'love',surprised:'surprised',tired:'tired',sleeping:'sleeping'};
const KEYS=['l','r','s','w','bend','mt','wob','split','mtilt','cr','cg','cb'];
const FWPAL={mint:[127,224,184],sky:[127,196,240],amber:[242,178,74],rose:[240,143,176],lilac:[184,156,240],lime:[180,224,90],coral:[242,132,108]};
const bgOf=c=>{if(!c||c==='none')return'#000';if(FWPAL[c])return'rgb('+FWPAL[c].map(x=>Math.round(x*.26)).join(',')+')';return/^#[0-9a-f]{6}$/i.test(c)?c:'#000'};
const rgbOf=h=>{const m=/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(h);return m?[parseInt(m[1],16),parseInt(m[2],16),parseInt(m[3],16)]:[244,244,244]};
const TINTS={red:[255,118,98],blue:[128,170,255],pink:[255,150,195]};
function tinted(rgb,t,amt){if(!t||amt<=0)return rgb;if(t==='dim'){const k=1-.38*amt;return rgb.map(x=>x*k)}const T=TINTS[t],lum=(.3*rgb[0]+.59*rgb[1]+.11*rgb[2])/255;return rgb.map((x,i)=>x+(T[i]*lum-x)*amt)}
function mouthPts(m,ph){const s=clamp(m.split,0,1),ca=Math.cos(m.tilt*Math.PI/180),sa=Math.sin(m.tilt*Math.PI/180),out=[];for(let i=0;i<17;i++){const u=i/16,ux=u*2-1,x1=ux*m.w/2,y1=m.bend*(.5-ux*ux),half=u<.5?u*2:(u-.5)*2,hx=half*2-1,x2=(u<.5?-.25:.25)*m.w+hx*m.w/4,y2=m.bend*(.5-hx*hx);let x=x1+(x2-x1)*s,y=y1+(y2-y1)*s;if(m.wob>.01)y+=m.wob*Math.sin(6.2832*(ux*1.25+ph));out.push([x*ca-y*sa,x*sa+y*ca])}return out}
const HELLO={en:'Hello!',es:'Hola!',fr:'Bonjour!',de:'Hallo!',pt:'Ola!',it:'Ciao!'};
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const ease01=x=>{x=clamp(x,0,1);return x*x*(3-2*x)};
const rnd=(a,b)=>a+Math.random()*(b-a);
const REDUCED=(()=>{try{return matchMedia('(prefers-reduced-motion: reduce)').matches}catch(e){return false}})();
function rr(c,x,y,w,hh,r){r=Math.min(r,w/2,hh/2);c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+hh,r);c.arcTo(x+w,y+hh,x,y+hh,r);c.arcTo(x,y+hh,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath()}
function rr2(c,x,y,w,hh,r){rr(c,x,y,w,hh,Math.max(0,r))}
function heartP(c,x,y,s){c.beginPath();c.moveTo(x,y+s*.48);c.bezierCurveTo(x-s*.95,y-s*.05,x-s*.52,y-s*.72,x,y-s*.22);c.bezierCurveTo(x+s*.52,y-s*.72,x+s*.95,y-s*.05,x,y+s*.48);c.closePath()}
function star(c,x,y,r){const k=.16;c.beginPath();c.moveTo(x,y-r);c.quadraticCurveTo(x+r*k,y-r*k,x+r,y);c.quadraticCurveTo(x+r*k,y+r*k,x,y+r);c.quadraticCurveTo(x-r*k,y+r*k,x-r,y);c.quadraticCurveTo(x-r*k,y-r*k,x,y-r);c.fill()}
const views=new Set();
class Face{constructor(cv,o){this.cv=cv;this.d=cv.getContext('2d');this.w=cv.width;this.hh=cv.height;
 this.o=Object.assign({style:'big_eyes',color:'none',background:'none',tint:true,state:'neutral',mode:'face',captions:false,size:'medium',lang:'en',decor:'none',dim:0,c24:false,cstyle:'digits',live:true},o||{});
 this.st=document.createElement('canvas');this.st.width=640;this.st.height=480;this.sc=this.st.getContext('2d');
 this._state=this.o.state;this.st0=0;this.t=rnd(0,5);this.P={};this.snap();this.gx=0;this.gy=0;this.gtx=0;this.gty=0;this.gn=1;this.bl=0;this.bs=-1;this.bn=rnd(1,3);this.v=0;this.vt=0;this.vtg=0;this.vis=true;
 if(this.o.live){views.add(this);if('IntersectionObserver' in window)new IntersectionObserver(e=>{this.vis=e[0].isIntersecting}).observe(cv)}this.draw()}
 set(o){const ch=o.style&&o.style!==this.o.style;if(o.state&&o.state!==this._state){this._state=o.state;this.st0=this.t;this.lid0=this.lidv}Object.assign(this.o,o);if(ch)this.snap();if(!this.o.live)this.drawOnce()}
 shutPct(d){return Math.max(6,Math.max(3,d*.125)/d*100)}
 /* patch UI06: the sleepy look nods off and fights to stay awake: hold, droop, shut, snap open, settle, a half droop; random step lengths */
 nodLid(base,sh){const N=this.nod||(this.nod={n:0,s:this.t,len:1.2}),R=[[.9,1.9],[1,1.5],[.3,.8],[.14,.14],[.5,1.2],[.7,1]];
  if(this.t-N.s>=N.len){N.n++;N.s=this.t;const r=R[N.n%6];N.len=r[0]+Math.random()*(r[1]-r[0])}
  const st=N.n%6,k=ease01((this.t-N.s)/N.len),held=base+22,nod=sh+3;
  return st===0?held:st===1?held+(nod-held)*k:st===2?sh:st===3?95:st===4?95+(held-95)*k:held+(base-held)*(k<.55?k/.55:(1-k)/.45)}
 snoreOf(t){const ph=(t*1000)%3400;return ph<1100?ph/1100:ph<1400?1:ph<2700?1-(ph-1400)/1300:0}
 lookOf(){return Object.assign({},LK[STL[this.o.state]||'neutral'])}
 target(){const o=this.o,g=GEO.stock,l=this.lookOf(),T={},sh=this.shutPct(g.d);let lid=l.l;
  if(o.state==='sleeping'){const e=clamp((this.t-this.st0)/1.5,0,1);lid=50+(sh-50)*(e*e*(3-2*e))}
  if(o.dim>0)lid=Math.min(lid,100-o.dim*28);
  T.l=lid;T.r=(l.r||0)+(l.b?180:0);T.s=l.s;const m=l.m;T.w=m[0]*g.mw/36;T.bend=m[1];T.mt=m[2]*(.5+.5*g.mt/8);T.wob=m[3];T.split=m[4];T.mtilt=m[5];
  const rgb=rgbOf(colorOf(o.color)),c=tinted(rgb,(o.tint!==false&&!g.stock)?l.t:'',.6);T.cr=c[0];T.cg=c[1];T.cb=c[2];return T}

 isArt(){return !(FST[this.o.style]||FST.big_eyes).stock}
 emoOf(){const s=this.o.state;return s==='thinking'||s==='speaking'?'neutral':(FEMO[s]!==undefined?s:'neutral')}
 tgtArt(){const st=FST[this.o.style]||FST.big_eyes;return FT.pose[st.name][this.emoOf()+(this.o.state==='thinking'?'+thinking':'')]}
 colTarget(){const o=this.o,e=this.emoOf();return tinted(rgbOf(colorOf(o.color)),o.tint!==false?FT.looks[FEMO[e]].tint:'',.6)}
 snapArt(){const T=this.tgtArt(),st=FST[this.o.style]||FST.big_eyes;this.sp=newSpring(T);this.mo=T[MP.MOPEN];this.mc=mouthTarget(st,FEMO[this.emoOf()],false,false,0,0);this.lidv=(1-T[MP.LID])*100;this.lid0=this.lidv;this.col=this.colTarget();this.bf=0;this.bk=0;this.sp.x[MP.GX]=T[MP.GX];this.sp.x[MP.GY]=T[MP.GY]}
 stepArt(dt){const st=FST[this.o.style]||FST.big_eyes,e=this.emoOf(),T=this.tgtArt(),state=this.o.state;this.t+=dt;
  springStep(this.sp,T,dt);const ct=this.colTarget(),ca=1-Math.exp(-dt/.22);this.col=this.col.map((x,i)=>x+(ct[i]-x)*ca);
  const shut=Math.max(6,Math.max(3,st.eye_d*.125)/st.eye_d*100);
  let openT=(1-T[MP.LID])*100;if(this.o.dim>0)openT=Math.min(openT,100-this.o.dim*28);if(state==='thinking')openT=Math.min(openT,82);
  if(state==='sleeping'){const k=clamp((this.t-this.st0)/1.5,0,1);openT=this.lid0+(shut-this.lid0)*(k*k*(3-2*k))}
  if(REDUCED){this.gx=0;this.gy=0;this.bf=0}
  else{
   let dip=false;
   if(state==='sleeping'){this.bf=0;this.bs=-1}
   else{const sleepy=false;
    if(this.bs<0){this.bn-=dt;if(this.bn<=0){this.bs=this.t}}
    if(this.bs>=0){const el=(this.t-this.bs)*1000,len=sleepy?Math.min(1400,360+this.bk*140):140;
     if(el<len){if(sleepy){dip=true;this.bf=0}else this.bf=blinkFactor(el)}
     else{this.bs=-1;this.bf=0;this.bk=sleepy?this.bk+1:0;this.bn=sleepy?3.2:rnd(2.6,5.2)}}}
   if(state==='sleepy'){openT=this.nodLid(Math.min(openT,45),shut)}
   else if(dip)openT=shut+6;
   const amp=Math.round(st.drift*FT.drift_scale[FEMO[e]]);
   this.gn-=dt;if(this.gn<=0){this.gn=rnd(.7,2.2);this.gtx=Math.round(rnd(-amp-.5,amp+.5));this.gty=Math.round(rnd(-amp-.5,amp+.5))*.7}
   if(!(amp>0&&this.lidv>40)){this.gtx=0;this.gty=0}
   const ga=1-Math.exp(-dt/.26);this.gx+=(this.gtx-this.gx)*ga;this.gy+=(this.gty-this.gy)*ga}
  this.lidv+=(openT-this.lidv)*(1-Math.exp(-dt/(openT<this.lidv?.028:.085)));if(Math.abs(openT-this.lidv)<.4)this.lidv=openT;
  let want=T[MP.MOPEN];
  if(state==='speaking'){this.vt-=dt;if(this.vt<=0){if(Math.random()<.22){this.vtg=0;this.vt=rnd(.15,.45)}else{this.vtg=rnd(.35,1);this.vt=rnd(.08,.18)}}want=this.vtg}
  if(state==='sleeping'){want=.5*this.snoreOf(this.t)}
  if(state==='tired'){const k=((this.t*1000)%6000)/6000,x=(k-.1)/.5;if(x>0&&x<1){const y=Math.sin(Math.PI*x);want=y*y*.6}}
  this.mo+=(want-this.mo)*(1-Math.exp(-dt/(want>this.mo?.038:.105)));
  const sp=state==='speaking',open=sp&&this.vtg>0?.08+.82*this.vtg:0,tg=mouthTarget(st,FEMO[e],false,sp,open,this.t*1000);if(!this.mc)this.mc=tg;this.mc=mouthFollow(this.mc,tg,dt*1000,mouthTauFor(this.mc,tg,sp,open))}
 paintArt(c){const o=this.o,st=FST[o.style]||FST.big_eyes,P=this.sp.x,t=this.t,br=REDUCED?0:Math.sin(t*1.57)*1.2;
  const fg='rgb('+this.col.map(x=>Math.round(clamp(x,0,255))).join(',')+')',bg=bgOf(o.background);
  c.save();c.lineCap='round';c.lineJoin='round';
  const speaking=o.state==='speaking',beat=1+.14*Math.pow(Math.max(0,Math.sin(t*6.2832*1.2)),3);
  for(const side of[-1,1]){
   const es=side>0?P[MP.RSCALE]:1,ew=P[MP.EW]*es,eh=P[MP.EH]*es,gx=this.gx+P[MP.GX],gy=this.gy+P[MP.GY];
   const ox=Math.round(gx),oy=Math.round(P[MP.DY]+gy+(side>0?P[MP.RLIFT]:0)+br);
   const eye=eyeShapes(st,{side:side,ew:ew,eh:eh,lid:1-this.lidv/100,slant:P[MP.SLANT],cheek:P[MP.CHEEK],blink:this.bf,heart:P[MP.HEART],beat:beat,closed:f01((26-this.lidv)/12),gx:gx,gy:gy,voice:speaking?this.mo:0});
   paintShapes(c,eye,160+side*st.eye_x+ox,ZC+st.eye_y+oy,fg,bg);
   paintShapes(c,browShapes(st,side,P[MP.EW]*es,P[MP.EH]*es,es,gx,side>0?P[MP.RLIFT]:0,P[MP.BR],P[MP.BROW],P[MP.BLIFT],P[MP.BTILT]),160+side*st.eye_x,ZC+st.eye_y+br,fg,bg)}
  if(st.mouth===1&&this.mc)paintShapes(c,mouthShapes(this.mc,(t%2.4)/2.4,P[MP.MON]),160,ZC+st.mouth_y+br*.5,fg,bg);
  if(o.state==='sleeping'&&!REDUCED){const ph=(t*1000)%3400,pk=ph>1400&&ph<2700?(ph-1400)/1300:0,dc=((t*1000)%11000)/1000;c.fillStyle=fg;
   if(pk>0){c.globalAlpha=.78*(1-pk);c.beginPath();c.arc(160+34+10*pk+5,ZC+st.mouth_y-6-16*pk+5,5,0,6.2832);c.fill()}
   if(dc<1.6){c.globalAlpha=.86-.59*dc/1.6;c.beginPath();c.arc(160-30+3,ZC+st.mouth_y+10+16*dc/1.6+3,3,0,6.2832);c.fill()}c.globalAlpha=1}
  if(o.state==='thinking'&&o.dots!==false){c.fillStyle=fg;for(let i=0;i<3;i++){const d=dotOf(st,i,(t-this.st0)*1000);c.globalAlpha=d[3]/255;c.beginPath();c.arc(160+d[0],ZC+d[1],d[2]/2,0,6.2832);c.fill()}c.globalAlpha=1}
  this.decor(c,fg,ZC+st.eye_y,160-st.eye_x,160+st.eye_x,st.ew,st.eh);c.restore()}
 snap(){if(this.isArt()){this.snapArt();return}this.T=this.target();for(const k of KEYS)this.P[k]=this.T[k]}
 bannerNow(o){const strip=[];if(o.topbar==='always')strip.push('battery','wifi');let b=o.banner;if(!b&&o.capmode==='banner'&&o.state==='speaking')b={text:HELLO[o.lang]||HELLO.en,icon:'speech',kind:'msg'};
  return Object.assign({text:'',icon:'none',kind:'msg',fg:colorOf(o.color),fade:this.bo==null?1:this.bo},b||{},{strip:strip.concat((b&&b.strip)||[])})}
 subNow(o){const on=(o.capmode||(o.style==='stock'?'subtitles':'off'))==='subtitles'&&o.state==='speaking';return{text:HELLO[o.lang]||HELLO.en,opa:on?1:(this.so||0)}}
 step(dt){{const o=this.o,want=o.mode==='face'&&!!(o.banner||(o.capmode==='banner'&&o.state==='speaking'));this.bo=mbFadeStep(Math.round((this.bo||0)*255),want,Math.round(dt*1000))/255;const sub=(o.capmode||(o.style==='stock'?'subtitles':'off'))==='subtitles'&&o.state==='speaking'&&o.mode==='face';this.so=mbFadeStep(Math.round((this.so||0)*255),sub,Math.round(dt*1000))/255}if(this.isArt()){this.stepArt(dt);return}this.t+=dt;this.T=this.target();const a=1-Math.exp(-dt*14),am=1-Math.exp(-dt/.09);for(const k of KEYS)this.P[k]+=(this.T[k]-this.P[k])*(k==='l'||k==='r'||k==='s'||k[0]==='c'?a:am);
  if(REDUCED){this.gx=0;this.gy=0;this.bl=0;return}
  if(this.o.state==='speaking'){this.vt-=dt;if(this.vt<=0){if(Math.random()<.22){this.vtg=0;this.vt=rnd(.15,.45)}else{this.vtg=rnd(.35,1);this.vt=rnd(.08,.18)}}this.v+=(this.vtg-this.v)*Math.min(1,dt/.06)}else this.v+=(0-this.v)*Math.min(1,dt/.1);
  this.gn-=dt;const D=(GEO.stock).d/6;if(this.gn<=0){this.gn=rnd(.8,2.2);this.gtx=rnd(-D,D);this.gty=rnd(-D*.6,D*.6)}
  const ga=Math.min(1,dt/.1);this.gx+=(this.gtx-this.gx)*ga;this.gy+=(this.gty-this.gy)*ga;
  const sl=this.o.state==='sleepy';
  if(this.bs<0){this.bn-=dt;if(this.bn<=0&&this.o.state!=='sleeping'){this.bs=this.t}}
  if(this.bs>=0){const e=this.t-this.bs,len=sl?.55:.14;if(e<len){const x=e/len;this.bl=x<.4?x/.4:(1-x)/.6}else{this.bl=0;this.bs=-1;this.bn=sl?rnd(2.6,3.6):rnd(2.5,6)}}}
 paint(c){if(this.isArt()){this.paintArt(c);return}const o=this.o,P=this.P,g=GEO.stock,t=this.t,br=REDUCED?0:Math.sin(t*1.57)*1.2;
  const col='rgb('+[P.cr,P.cg,P.cb].map(x=>Math.round(clamp(x,0,255))).join(',')+')';
  c.save();c.lineCap='round';c.lineJoin='round';c.fillStyle=col;c.strokeStyle=col;
  const sh=this.shutPct(g.d);
  for(const side of[-1,1]){const lid=P.l*(1-this.bl)+sh*this.bl,rr=g.d*P.s/2,edge=rr*(1-lid/50),lift=lid<30?-(30-Math.max(0,lid))/30*g.d*P.s/2*.95:0,rot=P.r*(side<0?1:-1);
   c.save();c.translate(160+side*g.x+this.gx*.6,ZC+g.y+this.gy*.6+br+lift);c.rotate(rot*Math.PI/180);c.beginPath();c.arc(0,0,rr,0,6.2832);c.clip();c.fillStyle=col;c.fillRect(-rr-2,edge,2*rr+4,2*rr-edge+4);c.restore()}
  const my=ZC+g.my+br*.5;
  if(o.state==='thinking'&&o.dots!==false){for(let i=0;i<3;i++){const ph=((t/1.2)-i*.33)%1,u=Math.abs(((ph<0?ph+1:ph)*2)%2-1),k=1-u;c.globalAlpha=(90+165*k)/255;c.beginPath();c.arc(160+(i-1)*24,my-k*5,(8+4*k)/2,0,6.2832);c.fill()}c.globalAlpha=1}
  else if(g.mo===2){const op=clamp(this.v*.9,0,1),w=90-30*op,hh=6+44*op;c.beginPath();rr2(c,160-w/2,my-hh/2,w,hh,16*op);c.fill()}
  else if(g.mo===1){const m={w:P.w,bend:P.bend,mt:P.mt,wob:P.wob,split:P.split,tilt:P.mtilt},op=this.v,flat=Math.min(1,op*2.2),sc=g.mw/46,mm={w:m.w+op*(12*sc-m.w),bend:m.bend*(1-flat),mt:m.mt+op*(34*sc-m.mt),wob:m.wob*(1-flat),split:m.split*(1-flat),tilt:m.tilt},pts=mouthPts(mm,(t%2.4)/2.4),xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]),tt=Math.max(2,mm.mt);
   if(Math.max(...xs)-Math.min(...xs)<tt/3&&Math.max(...ys)-Math.min(...ys)<tt/3){c.beginPath();c.arc(160+(Math.min(...xs)+Math.max(...xs))/2,my+(Math.min(...ys)+Math.max(...ys))/2,tt/2,0,6.2832);c.fill()}
   else{c.lineWidth=tt;c.beginPath();pts.forEach((p,i)=>i?c.lineTo(160+p[0],my+p[1]):c.moveTo(160+p[0],my+p[1]));c.stroke()}}
  this.decor(c,col,ZC+g.y,160-g.x,160+g.x,g.d,g.d);c.restore()}
 decor(c,col,ey,L,R,ew,eh){const n=this.o.decor,t=this.t;if(!n||n==='none')return;c.fillStyle=col;c.strokeStyle=col;c.lineWidth=4;
  if(n==='sparkles'||n==='stars'){[[L-ew*.7,ey-eh*.5,0],[R+ew*.7,ey-eh*.3,1.3],[160,ey-eh*.8,2.4]].forEach(([x,y,p])=>star(c,x,y,7+9*(.5+.5*Math.sin(t*3+p))))}
  else if(n==='tears'){for(let i=0;i<2;i++){const ph=((t+i)%2)/2,x=(i?R:L)+ew*.18,y=ey+eh/2+8+ph*40;c.globalAlpha=1-ph*ph;c.beginPath();c.arc(x,y,7,0,6.2832);c.fill()}c.globalAlpha=1}
  else if(n==='anger'){const x=R+ew/2+10,y=ey-eh/2-6;for(let i=0;i<4;i++){c.save();c.translate(x,y);c.rotate(i*Math.PI/2);c.beginPath();c.moveTo(4,-12);c.lineTo(4,-4);c.lineTo(12,-4);c.stroke();c.restore()}}
  else if(n==='zzz'){for(let i=0;i<3;i++){const ph=((t/3)+i/3)%1,sz=8+i*4,x=270+ph*14,y=64-ph*36;c.globalAlpha=Math.sin(ph*Math.PI);c.beginPath();c.moveTo(x-sz/2,y-sz/2);c.lineTo(x+sz/2,y-sz/2);c.lineTo(x-sz/2,y+sz/2);c.lineTo(x+sz/2,y+sz/2);c.stroke()}c.globalAlpha=1}
  else if(n==='heart'){for(let i=0;i<3;i++){const ph=((t/2)+i/3)%1;c.globalAlpha=1-ph;heartP(c,120+i*40,150-ph*90,14);c.fill()}c.globalAlpha=1}
  else if(n==='dizzy'){for(let i=0;i<4;i++){const a=t*3+i*1.57;c.beginPath();c.arc(160+Math.cos(a)*70,ey-eh*.8+Math.sin(a)*14,6,0,6.2832);c.fill()}}}
 clock(c,col){const d=new Date();let hr=d.getHours();const mn=String(d.getMinutes()).padStart(2,'0');let suf='';
  if(!this.o.c24){suf=hr>=12?' PM':' AM';hr=hr%12||12}const txt=(this.o.c24?String(hr).padStart(2,'0'):String(hr))+':'+mn;
  c.fillStyle=col;c.strokeStyle=col;c.textAlign='center';c.textBaseline='middle';
  if(this.o.cstyle==='ring'){c.lineWidth=12;c.globalAlpha=.25;c.beginPath();c.arc(160,120,88,0,6.2832);c.stroke();c.globalAlpha=1;c.beginPath();c.arc(160,120,88,-1.5708,-1.5708+6.2832*(d.getSeconds()+d.getMilliseconds()/1000)/60);c.stroke();c.font='700 54px system-ui,sans-serif';c.fillText(txt,160,118);if(suf){c.font='600 18px system-ui,sans-serif';c.fillText(suf.trim(),160,158)}}
  else{c.font='700 92px system-ui,sans-serif';c.fillText(txt,160,112);if(suf){c.font='600 26px system-ui,sans-serif';c.fillText(suf.trim(),160,176)}}}
 ov(name,level,secs){this.o.overlay={name,intensity:level,t0:this.t,until:this.t+secs}}
 ovClear(){this.o.overlay=null}
 draw(){const o=this.o,d=this.d;d.setTransform(1,0,0,1,0,0);d.fillStyle='#000';d.fillRect(0,0,this.w,this.hh);
  const sc=this.sc;sc.setTransform(1,0,0,1,0,0);sc.fillStyle=bgOf(o.background);sc.fillRect(0,0,640,480);sc.setTransform(2,0,0,2,0,0);
  const bn=o.mode==='face'?this.bannerNow(o):null,sub=o.mode==='face'?this.subNow(o):null;
  if(o.mode==='face'&&o.overlay&&this.t<o.overlay.until){const y0=bn&&(bn.text||bn.strip.length)&&bn.fade>0?BT.zones.face[0]:0,y1=sub&&sub.opa>0?BT.zones.subtitles[0]:BT.screen_h;sc.save();sc.beginPath();sc.rect(0,y0,BT.screen_w,y1-y0);sc.clip();drawOv(sc,o.overlay,this.t);sc.restore()} /* the overlay is behind the face and leaves the banner row and the subtitle strip alone while they show, as on the unit */
  if(o.mode==='clock')this.clock(sc,colorOf(o.color));
  else{sc.save();sc.beginPath();sc.rect(0,BT.zones.face[0],BT.screen_w,BT.zones.face[1]-BT.zones.face[0]);sc.clip();this.paint(sc);sc.restore()} /* the face lives in its own zone and is clipped to it, as on the unit */
  if(bn&&(bn.text||bn.strip.length)&&bn.fade>0)paintBanner(sc,bn,this.t,bn.fade);
  if(sub&&sub.opa>0)paintSubtitles(sc,sub.text,colorOf(o.color),sub.opa);
  if(false){const px={small:14,medium:18,large:24}[o.size]||18;sc.fillStyle='rgba(0,0,0,.6)';sc.fillRect(0,240-px*1.9,320,px*1.9);sc.fillStyle=colorOf(o.color);sc.font='600 '+px+'px system-ui,sans-serif';sc.textAlign='center';sc.textBaseline='middle';sc.fillText(HELLO[o.lang]||HELLO.en,160,240-px*.95)}
  d.imageSmoothingEnabled=true;const fx=o.fx||{};
  if(fx.glow){d.save();d.filter='blur(9px) brightness(1.5)';d.globalAlpha=.55;d.drawImage(this.st,0,0,this.w,this.hh);d.restore()}
  d.save();if(fx.mode&&FXM[fx.mode])d.filter=FXM[fx.mode];d.drawImage(this.st,0,0,this.w,this.hh);d.restore();
  if(fx.crt){d.fillStyle='rgba(0,0,0,.34)';for(let y=1;y<this.hh;y+=3)d.fillRect(0,y,this.w,1);const g=d.createRadialGradient(this.w/2,this.hh/2,this.hh*.35,this.w/2,this.hh/2,this.hh*.85);g.addColorStop(0,'rgba(0,0,0,0)');g.addColorStop(1,'rgba(0,0,0,.45)');d.fillStyle=g;d.fillRect(0,0,this.w,this.hh)}
  if(fx.night){d.fillStyle='rgba(40,16,0,.36)';d.fillRect(0,0,this.w,this.hh)}
  if(false){const bw=this.w*.7,bh=this.hh*.17,bx=(this.w-bw)/2,by=this.hh*.03;d.fillStyle='rgba(255,255,255,.92)';rr(d,bx,by,bw,bh,bh/2);d.fill();d.fillStyle='#222';d.font='600 '+Math.round(bh*.5)+'px system-ui,sans-serif';d.textAlign='center';d.textBaseline='middle';d.fillText(HELLO[o.lang]||HELLO.en,this.w/2,by+bh/2)}
  if(o.dim>0){d.fillStyle='rgba(0,0,0,'+(o.dim*.45)+')';d.fillRect(0,0,this.w,this.hh)}}
 drawOnce(){this.snap();this.bl=0;this.gx=0;this.gy=0;if(this.isArt())this.bf=0;this.draw()}}
let last=performance.now(),acc=0;
function loop(now){const dt=Math.min(.05,(now-last)/1000);last=now;acc+=dt;
 if(acc>=1/30&&!document.hidden){const s=acc;acc=0;for(const v of views){if(!v.cv.isConnected){views.delete(v);continue}if(!v.vis)continue;v.step(s);v.draw()}}
 requestAnimationFrame(loop)}
requestAnimationFrame(loop);
function bandNow(hours){const hr=new Date().getHours();return hr>=hours[3]||hr<hours[0]?'night':hr>=hours[2]?'evening':hr>=hours[1]?'day':'morning'}

/* ---- the page frame: units, groups, theme, language ---- */
const GROUPS=['home','remote','look','voice','packs','network','behavior','security','play','system'];
const NAMEKEY={home:'g.home',remote:'g.remote',look:'g.look',voice:'g.voice',packs:'g.packs',network:'g.network',behavior:'g.behavior',security:'g.security',play:'g.play',system:'g.system'};
let UNITS=[],UNIT=null,CUR='home',BUILT={};
const panels={};
const lsGet=k=>{try{return localStorage.getItem(k)}catch(e){return null}};
const lsSet=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
function setTheme(v){const r=document.documentElement;if(v==='auto')r.removeAttribute('data-theme');else r.setAttribute('data-theme',v);lsSet('theme',v)}
function accentFor(u){const k=u&&u.color;return !k||k==='none'?'#35c79a':colorOf(k)}
function applyAccent(){document.documentElement.style.setProperty('--accent',accentFor(UNIT))}
function shell(){
 const nav=h('nav',{class:'nav','aria-label':T('nav.label')});
 for(const g of GROUPS)nav.append(h('button',{type:'button','data-g':g,onclick:()=>go(g)},ico(g),S['settings.ui.'+NAMEKEY[g]]));
 const mkLang=()=>{const l=h('select',{'aria-label':S['settings.language'],onchange:e=>{location.href='/settings?lang='+e.target.value}});for(const c of LANGS_ALL)l.append(h('option',{value:c,selected:c===LANG},S['settings.lang.'+c]||c));return l};
 const lang=mkLang();
 const theme=seg(T('theme.label'),[{v:'auto',t:T('theme.auto')},{v:'light',t:T('theme.light')},{v:'dark',t:T('theme.dark')}],lsGet('theme')||'auto',v=>{setTheme(v)});
 const rail=h('aside',{class:'rail'},h('div',{class:'brand'},h('span',{class:'logo','aria-hidden':'true'},h('i'),h('i')),S['settings.title']),nav,h('div',{class:'railfoot'},field(S['settings.language'],lang),theme));
 const main=h('main',{class:'main',id:'main'},h('div',{class:'top'},h('div',{class:'chips',role:'tablist','aria-label':T('units_label'),id:'chips'}),h('div',{class:'tabs'},field('',mkLang()))),h('div',{id:'panels'}),h('div',{id:'toasts',class:'toasts',role:'status','aria-live':'polite'}));
 const sk=h('a',{class:'skip',href:'#main'},T('skip'));
 document.body.append(sk,h('div',{class:'app'},rail,main));
 for(const g of GROUPS){const p=h('section',{class:'panel',id:'p-'+g,'aria-labelledby':'t-'+g},h('h1',{class:'title',id:'t-'+g},S['settings.ui.'+NAMEKEY[g]]));main.querySelector('#panels').append(p);panels[g]=p}}
const LANGS_ALL=['en','es','fr','de','pt','it'];
function drawChips(){const box=$('#chips');box.replaceChildren();
 for(const u of UNITS)box.append(h('button',{type:'button',role:'tab',class:'chip','aria-selected':String(UNIT&&u.device_id===UNIT.device_id),style:'--chipc:'+accentFor(u),onclick:()=>pick(u.device_id)},h('span',{class:'dot'}),u.name,h('span',{class:'state'+(u.online?' on':'')},S[u.online?'settings.online.yes':'settings.online.no'])))}
function pick(id){UNIT=UNITS.find(u=>u.device_id===id)||UNITS[0];try{sessionStorage.setItem('unit',UNIT.device_id)}catch(e){}applyAccent();drawChips();BUILT={};for(const g of GROUPS)panels[g].querySelectorAll(':scope>:not(h1)').forEach(n=>n.remove());go(CUR,true)}
function go(g,force){if(!GROUPS.includes(g))g='home';CUR=g;if(location.hash!=='#'+g)history.replaceState(null,'','#'+g);
 document.querySelectorAll('.nav button').forEach(b=>{if(b.dataset.g===g)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});
 for(const k of GROUPS)panels[k].classList.toggle('on',k===g);
 if(!BUILT[g]&&UNIT){BUILT[g]=true;Promise.resolve(BUILDERS[g](panels[g],UNIT)).catch(e=>{toast(T('net_error'),'bad');console.error(e)})}window.scrollTo({top:0})}
function whenUnits(p){p.append(h('div',{class:'empty'},S['settings.no_units']))}
const BUILDERS={};
async function main(){shell();const r=await api('/api/stackchan/settings');
 if(!r.ok){toast(r.d.error||T('net_error'),'bad');return}
 UNITS=r.d.units;HOST=r.d.host_address;HOSTV=r.d.host_version||'';if(!UNITS.length){for(const g of GROUPS)whenUnits(panels[g]);go('home');return}
 let keep=null;try{keep=sessionStorage.getItem('unit')}catch(e){}
 UNIT=UNITS.find(u=>u.device_id===keep)||UNITS.find(u=>u.device_id===r.d.default_unit)||UNITS[0];
 applyAccent();drawChips();go((location.hash||'#home').slice(1))}
let HOST='',HOSTV='';
addEventListener('hashchange',()=>{const g=(location.hash||'#home').slice(1);if(g!==CUR)go(g)});

/* ---- shared helpers for panels ---- */
async function faceView(id){const r=await api(facePath(id));return r.ok?r.d:{error:r.d.error}}
function unitSet(id,body,quiet){return save(setPath(id),body,quiet)}
function simpleList(items){return h('ul',{class:'steps'},items.map(([cls,t])=>h('li',{class:cls},t)))}
function kv(rows){const d=h('dl',{class:'kv'});for(const[k,v]of rows){if(v==null||v==='')continue;d.append(h('dt',{},k),h('dd',{},v))}return d}
function soonCard(title,help,...kids){return card(h('span',{},title),help,...kids)}
const bytesWord=n=>n>=1048576?(n/1048576).toFixed(1)+' MB':Math.round(n/1024)+' KB';


/* ---- Remote: buttons that act on the selected unit now ---- */
async function press(btn,fn,quiet){if(btn.classList.contains('busy'))return;btn.classList.add('busy');btn.setAttribute('aria-pressed','true');btn.setAttribute('aria-busy','true');
 try{const r=await fn();if(r&&r.ok&&!quiet)toast(r.d.message||T('rem.done'));return r}finally{btn.classList.remove('busy');btn.removeAttribute('aria-busy');btn.setAttribute('aria-pressed','false')}}
function bigBtn(icon,label,fn,off,why){const b=h('button',{type:'button',class:'bigb','aria-pressed':'false',disabled:!!off,title:off?why:null},ico(icon),label);b.addEventListener('click',()=>press(b,fn));return b}
const remote=async(id,body)=>{const r=await save(unitPath(id,'remote'),body,true);document.dispatchEvent(new Event('remote-acted'));return r};
ICO.beep='M11 5L6 9H3v6h3l5 4zM15.5 8.5a5 5 0 010 7M18.5 6a9 9 0 010 12';ICO.flash='M13 2L4 14h7l-1 8 9-12h-7z';ICO.find='M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-5-5';ICO.say='M21 12a8 8 0 01-11.6 7.1L3 21l1.9-6.4A8 8 0 1121 12z';ICO.dance='M9 18V5l12-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0zM21 16a3 3 0 11-6 0 3 3 0 016 0z';ICO.game=ICO.play;ICO.photo='M4 8h3l2-3h6l2 3h3v11H4zM12 11a3.5 3.5 0 100 7 3.5 3.5 0 000-7z';ICO.mute='M11 5L6 9H3v6h3l5 4zM22 9l-6 6M16 9l6 6';ICO.restart='M4 12a8 8 0 108-8M4 4v5h5';ICO.lookaround='M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 100 6 3 3 0 000-6z';ICO.nod='M12 3v14M6 11l6 6 6-6';ICO.shake='M3 12h18M7 7l-5 5 5 5M17 7l5 5-5 5';
async function quickActions(id,reach,muted,onMute){const off=!reach,why=T('rem.offline');let finding=false;
 const fb=bigBtn('find',T('rem.find'),async()=>{const r=await remote(id,{do:'find',on:!finding});if(r.ok){finding=!finding;fb.lastChild.textContent=finding?T('rem.find_stop'):T('rem.find')}else toast(r.d.error,'bad');return r},off,why);
 return [bigBtn('beep',T('rem.beep'),async()=>{const r=await remote(id,{do:'beep'});if(!r.ok)toast(r.d.error,'bad');return r},off,why),
  bigBtn('flash',T('rem.flash'),async()=>{const r=await remote(id,{do:'flash'});if(!r.ok)toast(r.d.error,'bad');return r},off,why),fb]}
BUILDERS.remote=async(p,u)=>{const id=u.device_id,rv=await api(unitPath(id,'remote')),ov=await api(unitPath(id,'overview')),d=rv.ok?rv.d:{reachable:false,dances:[],games:[],limits:{yaw:128,pitch:[5,85]}};
 const reach=!!u.online&&d.reachable!==false,off=!reach,why=T('rem.offline');
 const run=name=>async()=>{const r=await remote(id,Object.assign({do:name}));if(!r.ok)toast(r.d.error,'bad');return r};
 const banner=off?h('div',{class:'banner'},why):(d.cue===false?h('div',{class:'banner'},T('ra.cue_none')):null);
 const mb=bigBtn('mute',(ov.ok&&ov.d.privacy&&ov.d.privacy.mute)?T('rem.unmute'):T('rem.mute'),async()=>{const cur=ov.ok&&ov.d.privacy?!!ov.d.privacy.mute:false;const r=await remote(id,{do:'mute',on:!cur});if(r.ok){ov.d.privacy=ov.d.privacy||{};ov.d.privacy.mute=!!r.d.muted;mb.lastChild.textContent=r.d.muted?T('rem.unmute'):T('rem.mute')}else toast(r.d.error,'bad');return r},off,why);
 const quick=card(T('rem.quick'),null,banner,h('div',{class:'big'},...(await quickActions(id,reach)),
  bigBtn('lookaround',T('rem.look'),run('look'),off,why),bigBtn('nod',T('rem.nod'),run('nod'),off,why),bigBtn('shake',T('rem.shake'),run('shake'),off,why),
  mb,
  bigBtn('restart',T('rem.restart'),()=>{},true,T('soon'))));
 /* say something */
 const txt=h('textarea',{maxlength:200,rows:3,'aria-label':T('rem.say_label'),disabled:off});
 const sayB=h('button',{type:'button',class:'btn pri',disabled:off,title:off?why:null,'aria-pressed':'false'},T('rem.say_go'));sayB.addEventListener('click',()=>press(sayB,async()=>{const r=await remote(id,{do:'say',text:txt.value});if(!r.ok)toast(r.d.error,'bad');return r}));
 const say=card(T('rem.say'),null,field(T('rem.say_label'),txt),h('div',{class:'btns'},sayB));
 /* head pad */
 const L=d.limits,yawMax=L.yaw,pMin=L.pitch[0],pMax=L.pitch[1];let yaw=0,pitch=pMin+10;
 const dot=h('i'),pad=h('div',{class:'pad',tabindex:off?-1:0,role:'group','aria-label':T('rem.pad')+'. '+T('rem.limits')},dot);
 const place=()=>{dot.style.left=((yaw+yawMax)/(2*yawMax)*100)+'%';dot.style.top=((pMax-pitch)/(pMax-pMin)*100)+'%'};place();
 let sending=false,again=false;const send=async()=>{if(off)return;if(sending){again=true;return}sending=true;const r=await remote(id,{do:'head',yaw:Math.round(yaw),pitch:Math.round(pitch)});sending=false;if(!r.ok){toast(r.d.error,'bad');return}if(again){again=false;send()}};
 const fromEvent=e=>{const b=pad.getBoundingClientRect();const x=clamp((e.clientX-b.left)/b.width,0,1),y=clamp((e.clientY-b.top)/b.height,0,1);yaw=Math.round(-yawMax+x*2*yawMax);pitch=Math.round(pMax-y*(pMax-pMin));place()};
 let drag=false,tick=0;pad.addEventListener('pointerdown',e=>{if(off)return;drag=true;pad.setPointerCapture(e.pointerId);fromEvent(e);send()});
 pad.addEventListener('pointermove',e=>{if(!drag)return;fromEvent(e);const n=Date.now();if(n-tick>250){tick=n;send()}});
 pad.addEventListener('pointerup',()=>{if(drag){drag=false;send()}});
 const step=(dy,dp)=>{yaw=clamp(yaw+dy,-yawMax,yawMax);pitch=clamp(pitch+dp,pMin,pMax);place();send()};
 pad.addEventListener('keydown',e=>{const m={ArrowLeft:[-10,0],ArrowRight:[10,0],ArrowUp:[0,10],ArrowDown:[0,-10]}[e.key];if(m){e.preventDefault();step(m[0],m[1])}});
 const ab=(t,a,dy,dp)=>h('button',{type:'button',class:'btn','aria-label':a,disabled:off,onclick:()=>step(dy,dp)},t);
 const cen=h('button',{type:'button',class:'btn',disabled:off,onclick:async()=>{yaw=0;pitch=pMin;place();const r=await remote(id,{do:'center'});if(!r.ok)toast(r.d.error,'bad');else toast(T('rem.done'))}},T('rem.center'));
 const arrows=h('div',{class:'arrows'},h('span'),ab('▲','Up',0,10),h('span'),ab('◀','Left',-10,0),cen,ab('▶','Right',10,0),h('span'),ab('▼','Down',0,-10),h('span'));
 const headc=card(T('rem.pad'),T('rem.limits'),pad,arrows);
 /* dance and game */
 const dsel=h('select',{'aria-label':T('rem.dance'),disabled:off||!d.dances.length});for(const x of d.dances)dsel.append(h('option',{value:x.name},pretty(x.name)+(x.seconds?' ('+x.seconds+' s)':'')));
 const dgo=h('button',{type:'button',class:'btn pri',disabled:off||!d.dances.length},T('rem.dance_go'));dgo.addEventListener('click',()=>press(dgo,async()=>{const r=await remote(id,{do:'dance',name:dsel.value});if(!r.ok)toast(r.d.error,'bad');return r}));
 const dstop=h('button',{type:'button',class:'btn',disabled:off},T('rem.dance_stop'));dstop.addEventListener('click',()=>press(dstop,async()=>{const r=await remote(id,{do:'stop_dance'});if(!r.ok)toast(r.d.error,'bad');return r}));
 const dance=card(T('rem.dance'),null,dsel,h('div',{class:'btns'},dgo,dstop));
 const gsel=h('select',{'aria-label':T('rem.game'),disabled:off});for(const x of d.games)gsel.append(h('option',{value:x.id},x.title));
 const ggo=h('button',{type:'button',class:'btn pri',disabled:off},T('rem.game_go'));ggo.addEventListener('click',()=>press(ggo,async()=>{const r=await remote(id,{do:'game',name:gsel.value});if(!r.ok)toast(r.d.error,'bad');return r}));
 const game=card(T('rem.game'),null,gsel,h('div',{class:'btns'},ggo));
 /* picture */
 const shot=h('div',{});const cam=!off&&d.photo;
 const pb=h('button',{type:'button',class:'btn pri',disabled:!cam,title:!d.photo?T('rem.photo_need'):(off?why:null)},T('rem.photo'),!d.photo?[' ',h('span',{class:'badge'},T('rem.photo_need'))]:null);
 pb.addEventListener('click',()=>press(pb,async()=>{const r=await remote(id,{do:'photo'});if(r.ok&&r.d.image)shot.replaceChildren(h('img',{class:'photo',src:r.d.image,alt:T('rem.photo_alt')}));else toast(r.d.error,'bad');return r},true));
 const pic=card(T('rem.photo'),null,h('div',{class:'btns'},pb),shot);
 p.append(h('div',{class:'grid'},quick,say,headc,dance,game,overlayCard(id,off,why,null,'pol.ov.title'),pic,...(await accessCards())))};

/* ---- Remote access and Remote activity ---- */
const RA='/api/stackchan/remote-access';
async function accessCards(){
 const r=await api(RA);if(!r.ok)return[card(T('ra.title'),null,h('div',{class:'banner bad'},r.d.error||T('net_error')))];
 const a=r.d;let last10=true,who='',what='';
 const put=async patch=>{const x=await save(RA,patch,true);if(x.ok)Object.assign(a,x.d);return x.ok};
 const list=h('div',{class:'list'});const kindWord=k=>{const w=T('ra.k.'+k);return w==='ra.k.'+k?pretty(k):w};
 const drawC=()=>list.replaceChildren(...(a.controllers.length?a.controllers.map(c=>h('div',{class:'item'},
  h('div',{class:'grow'},h('b',{},c.label),h('div',{class:'hint'},T(c.status==='paired'?'ra.paired':'ra.waiting')+' · '+String(c.paired||c.asked||'').slice(0,16).replace('T',' '))),
  c.status==='paired'?null:h('button',{class:'btn pri',type:'button',onclick:async()=>{const x=await save(RA+'/allow',{id:c.id},true);if(x.ok){a.controllers=x.d.controllers;drawC()}}},T('ra.allow')),
  h('button',{class:'btn bad',type:'button',onclick:async()=>{const x=await save(RA+'/revoke',{id:c.id},true);if(x.ok){a.controllers=x.d.controllers;drawC()}}},T('ra.revoke')))):[h('p',{class:'hint'},T('ra.none'))]));
 drawC();
 const sets=card(T('ra.title'),T('ra.help'),
  toggle(T('ra.enabled'),T('ra.enabled_help'),a.enabled,async on=>put({enabled:on})),
  h('div',{class:'f'},h('b',{},T('ra.speaking')),h('p',{class:'hint'},T('ra.speaking_help')),
   seg(T('ra.speaking'),[{v:'off',t:T('ra.sp_off')},{v:'ask',t:T('ra.sp_ask')},{v:'on',t:T('ra.sp_on')}],a.speaking,v=>put({speaking:v}))),
  toggle(T('ra.nocue'),T('ra.nocue_help'),a.allow_without_cue,async on=>put({allow_without_cue:on})),
  h('h3',{},T('ra.controllers')),list);
 const rows=h('div',{class:'list'}),whoSel=h('select',{'aria-label':T('ra.f_who'),onchange:()=>{who=whoSel.value;drawA()}}),whatSel=h('select',{'aria-label':T('ra.f_what'),onchange:()=>{what=whatSel.value;drawA()}});
 const modeBtn=h('button',{class:'btn',type:'button',onclick:()=>{last10=!last10;drawA()}},T('ra.last10'));
 const fill=(sel,any,vals,cur)=>{sel.replaceChildren(h('option',{value:''},any),...vals.map(v=>h('option',{value:v[0]},v[1])));sel.value=cur};
 function drawA(){
  fill(whoSel,T('ra.f_any'),[...new Set(a.activity.map(x=>x.controller))].map(v=>[v,v]),who);
  fill(whatSel,T('ra.f_anything'),[...new Set(a.activity.map(x=>x.action))].map(v=>[v,kindWord(v)]),what);
  let xs=a.activity.filter(x=>(!who||x.controller===who)&&(!what||x.action===what));if(last10)xs=xs.slice(0,10);
  modeBtn.textContent=last10?T('ra.last10'):T('ra.all');modeBtn.setAttribute('aria-pressed',String(last10));
  rows.replaceChildren(...(xs.length?xs.map(x=>h('div',{class:'item'},
   h('div',{class:'grow'},h('b',{},(kindWord(x.action))+' · '+x.controller),
    x.text?h('div',{style:'overflow-wrap:anywhere'},'“'+x.text+'”'):null,h('div',{class:'hint'},String(x.time).slice(0,19).replace('T',' ')+(x.note?' · '+x.note:''))),
   h('span',{class:'badge'},T('ra.r.'+x.result)))):[h('p',{class:'hint'},T('ra.empty'))]))}
 const reload=async()=>{const x=await api(RA);if(x.ok){Object.assign(a,x.d);drawC();drawA()}};
 document.addEventListener('remote-acted',reload);
 drawA();
 const act=card(T('ra.act'),T('ra.act_help'),h('div',{class:'btns'},whoSel,whatSel,modeBtn,h('button',{class:'btn',type:'button',onclick:reload},T('ra.refresh'))),rows);
 return[sets,act]}

/* ---- HOME ---- */
BUILDERS.home=async(p,u)=>{
 const ov=await api(unitPath(u.device_id,'overview')),fv=await faceView(u.device_id);
 const o=ov.ok?ov.d:{reachable:false};const v=fv.values||{};
 const cv=h('canvas',{width:640,height:480,role:'img','aria-label':T('preview')});
 const face=new Face(cv,{style:v.style,color:v.color,background:v.background,tint:v.emotion_tint,captions:v.captions,size:v.caption_size,lang:v.lang});
 const pvc=card(T('home.face'),null,h('div',{class:'screen'},cv),h('p',{class:'hint'},(S['settings.face.style.'+v.style]||v.style||'')+', '+(S['settings.face.color.'+v.color]||v.color||'')),h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>go('look')},S['settings.ui.g.look'])));
 const stats=h('div',{class:'stats'});
 stats.append(h('div',{class:'stat'},h('b',{},u.online?S['settings.online.yes']:S['settings.online.no']),h('span',{},S['settings.online'])));
 stats.append(h('div',{class:'stat'},h('b',{},o.battery?o.battery.percent+'%':'-'),h('span',{},T('home.battery')+(o.battery&&o.battery.charging?', '+T('home.charging'):''))));
 stats.append(h('div',{class:'stat'},h('b',{},'Wi-Fi'),h('span',{},S['settings.wifi.'+u.wifi]||'')));
 stats.append(h('div',{class:'stat'},h('b',{},u.firmware_version||S['settings.firmware.unknown']),h('span',{},S['settings.firmware'])));
 const sum=card(u.name,o.reachable===false?T('unit_offline'):null,stats,
  o.privacy?toggle(T('voice.mic_mute'),T('voice.mute_help'),o.privacy.mute,async on=>{const r=await save(unitPath(u.device_id,'device'),{mute:on});return r.ok}):null);
 const list=card(T('units_label'),null,h('div',{class:'list'},UNITS.map(x=>h('div',{class:'item'},h('span',{class:'dot',style:'--chipc:'+accentFor(x)}),h('div',{class:'grow'},h('b',{},x.name),h('div',{class:'hint'},x.device_id)),h('span',{class:'state'+(x.online?' on':'')},S[x.online?'settings.online.yes':'settings.online.no']),h('button',{class:'btn',type:'button',onclick:()=>pick(x.device_id)},x.name)))),h('p',{class:'hint'},T('net.pair_help')));
 const qa=card(T('rem.quick'),null,h('div',{class:'big'},...(await quickActions(u.device_id,!!u.online&&o.reachable!==false))),h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>go('remote')},S['settings.ui.g.remote'])));
 p.append(h('div',{class:'grid'},sum,qa,pvc,list))};

/* ---- LOOK ---- */
BUILDERS.look=async(p,u)=>{
 const id=u.device_id,fv=await faceView(id);
 if(fv.error||!fv.values){p.append(card(S['settings.face'],null,h('div',{class:'banner bad'},fv.error||T('net_error')),h('button',{class:'btn',onclick:()=>{BUILT.look=false;p.querySelectorAll(':scope>:not(h1)').forEach(n=>n.remove());go('look',true)}},T('retry'))));return}
 let v=Object.assign({},fv.values);const c=fv.choices;const feats=fv.features;const has=f=>feats==null||feats.includes(f);
 const cv=h('canvas',{width:640,height:480,role:'img','aria-label':T('preview')});
 const face=new Face(cv,{style:v.style,color:v.color,background:v.background,tint:v.emotion_tint,captions:v.captions,size:v.caption_size,lang:v.lang,c24:v.clock24,cstyle:v.clock_style});
 const refresh=()=>{face.set({style:v.style,color:v.color,background:v.background,tint:v.emotion_tint,captions:v.captions,size:v.caption_size,lang:v.lang,c24:v.clock24,cstyle:v.clock_style,dim:v.tod&&bandNow(v.tod_hours)==='night'?1:0});tiles.forEach(t=>t.set({color:v.color,background:v.background,tint:v.emotion_tint}))};
 const put=async patch=>{const old=Object.assign({},v);Object.assign(v,patch);refresh();const r=await save(facePath(id),patch);if(!r.ok){v=old;refresh();return false}if(patch.color){u.color=patch.color;applyAccent();drawChips()}return true};
 const looks=['neutral','happy','sad','angry','surprised','thinking','sleepy','sleeping','tired','speaking','love'];
 const states=seg(T('try_look'),looks.map(s=>({v:s,t:T('state.'+s)})).concat([{v:'clock',t:S['settings.ui.nav.time']}]),'neutral',s=>{if(s==='clock')face.set({mode:'clock'});else face.set({mode:'face',state:s});return true});
 const pv=card(T('preview'),T('preview_note'),h('div',{class:'pv'},h('div',{class:'screen'},cv),states));
 const tiles=[];
 const gallery=h('div',{class:'tiles',role:'radiogroup','aria-label':S['settings.face.style']});
 const gal=[];for(const s of c.style){const tc=h('canvas',{width:160,height:120,'aria-hidden':'true'});const tf=new Face(tc,{style:s,color:v.color,background:v.background,tint:v.emotion_tint,live:false});tf.drawOnce();tiles.push(tf);
  const off=!has('looks')&&['eyes_only','stock'].includes(s);
  const b=h('button',{type:'button',role:'radio',class:'tile','aria-checked':String(v.style===s),disabled:off,title:off?T('soon'):null,onclick:async()=>{const ok=await put({style:s});if(ok)gal.forEach(x=>x.setAttribute('aria-checked',String(x===b)))}},h('div',{class:'screen'},tc),S['settings.face.style.'+s]||pretty(s));gal.push(b);gallery.append(b)}
 const sw=swatches(S['settings.face.color'],c.color,v.color,s=>put({color:s}),true);
 const custom=h('input',{type:'color',value:/^#/.test(v.color)?v.color:'#40c0ff','aria-label':S['settings.face.color']+' (custom)',onchange:async e=>{const ok=await put({color:e.target.value});if(ok)sw.redraw(e.target.value)}});
 const look=card(S['settings.face.style'],null,gallery);
 const color=card(S['settings.face.color'],null,sw,field('',custom));
 const bsw=swatches(S['settings.face.background'],c.background||c.color,v.background||'none',s=>put({background:s}),true);
 const bcustom=h('input',{type:'color',value:/^#/.test(v.background||'')?v.background:'#102030','aria-label':S['settings.face.background']+' (custom)',onchange:async e=>{const ok=await put({background:e.target.value});if(ok)bsw.redraw(e.target.value)}});
 const bgcard=card(S['settings.face.background'],null,bsw,field('',bcustom));
 const tintcard=card(S['settings.face.tint'],S['settings.face.tint_help'],toggle(S['settings.face.tint'],null,v.emotion_tint!==false,on=>put({emotion_tint:on}),!has('tint')));
 const caps=card(S['settings.face.captions'],T('face.captions_help'),toggle(S['settings.face.captions'],null,v.captions,on=>put({captions:on}),!has('captions')),
  seg(S['settings.face.caption_size'],c.caption_size.map(s=>({v:s,t:S['settings.face.caption_size.'+s]})),v.caption_size,s=>put({caption_size:s}),!has('packs')),
  field(S['settings.face.lang'],(()=>{const sel=h('select',{onchange:e=>put({screen_lang:e.target.value})});for(const l of c.lang)sel.append(h('option',{value:l,selected:l===v.lang},S['settings.lang.'+l]||l));return sel})()));
 const hrs=h('div',{class:'hrs'});const hv=v.tod_hours.slice();
 ['morning','day','evening','night'].forEach((b,i)=>{const inp=h('input',{type:'number',min:0,max:23,value:hv[i],'aria-label':T('face.band.'+b),onchange:async()=>{const n=hv.slice();n[i]=parseInt(inp.value,10);const ok=await put({tod_hours:n});if(ok)hv[i]=n[i];else inp.value=hv[i]}});hrs.append(field(T('face.band.'+b),inp))});
 const tod=card(S['settings.face.tod'],T('face.tod_help'),toggle(S['settings.face.tod'],null,v.tod,on=>put({tod:on}),!has('tod')),h('p',{class:'hint'},T('face.hours_help')),hrs);
  const reset=h('button',{class:'btn',type:'button',onclick:async()=>{const r=await save(facePath(id)+'/reset',{});if(r.ok){BUILT.look=false;p.querySelectorAll(':scope>:not(h1)').forEach(n=>n.remove());go('look',true)}}},S['settings.face.reset']);
 const banners=[];if(fv.pending)banners.push(h('div',{class:'banner'},S['settings.face.pending']));if(fv.unavailable&&fv.unavailable.length)banners.push(h('div',{class:'banner'},S['settings.face.unavailable']+' '+fv.unavailable.join(', ')));
 /* screen brightness and light ring */
 const dv=await api(unitPath(id,'overview'));const sv=dv.ok?dv.d.saved:{brightness:100,led:'off'};
 const bright=card(T('look.brightness'),T('look.brightness_help'),slider(T('look.brightness'),10,100,5,sv.brightness,x=>x+'%',null,x=>save(unitPath(id,'device'),{brightness:x}),[ '10%','100%']),
  toggle(T('look.auto'),dv.ok&&dv.d.light!=null?T('home.room_light')+': '+Math.round(dv.d.light)+' lux':null,false,()=>false,true),toggle(T('look.night_dim'),null,false,()=>false,true));
 const ledSw=swatches(T('look.led'),['off','mint','sky','amber','rose','lilac','lime','coral'],ledName(sv.led),async n=>{const hex=n==='off'?'off':PAL[n];return (await save(unitPath(id,'device'),{led:hex})).ok},false);
 ledSw.querySelector('[data-v=off]').classList.add('none');ledSw.querySelector('[data-v=off]').title=T('look.led_off');ledSw.querySelector('[data-v=off]').setAttribute('aria-label',T('look.led_off'));
 const led=card(T('look.led'),T('look.led_help'),ledSw,slider(T('look.led_bright'),10,100,5,100,x=>x+'%',null,null,null,true));
 refresh();const pol=await lookCards(id,u,v,has,face);
 p.append(h('div',{class:'two'},h('div',{class:'stack sticky'},pv,...banners),h('div',{class:'stack'},look,pol.cards[2],color,bgcard,tintcard,pol.cards[0],pol.cards[1],pol.cards[3],pol.cards[4],pol.cards[5],pol.cards[6],caps,tod,bright,led,card(null,null,reset))));
 const pics=picSection(u.device_id);p.append(h('div',{class:'stack',style:'margin-top:18px'},pics))};

/* ---- VOICE AND SOUND ---- */
BUILDERS.voice=async(p,u)=>{const id=u.device_id,ov=await api(unitPath(id,'overview')),sv=ov.ok?ov.d.saved:{volume:70};const pr=ov.ok?ov.d.privacy:null;
 const fv=await faceView(id);const v=fv.values||{lang:'en'};const feats=fv.features;const has=f=>feats==null||feats.includes(f);
 const vol=card(T('voice.volume_now'),null,slider(T('voice.volume_now'),0,100,5,sv.volume,x=>x+'%',null,x=>save(unitPath(id,'device'),{volume:x}),['0%','100%']),
  slider(T('voice.volume'),0,100,5,u.volume_cap,x=>x+'%',null,x=>unitSet(id,{volume_cap:x}),['0%','100%']),
  toggle(T('voice.mic_mute'),T('voice.mute_help'),pr?pr.mute:u.muted,async on=>(await save(unitPath(id,'device'),{mute:on})).ok),toggle(T('voice.speaker_mute'),null,false,()=>false,true));
 const speech=card(S['settings.ui.nav.voice'],null,slider(T('voice.speed'),.75,1.5,.05,u.speech_speed,x=>x.toFixed(2)+'x',null,x=>unitSet(id,{speech_speed:x}),[T('voice.slow'),T('voice.fast')]),
  slider(T('voice.pitch'),-12,12,1,u.speech_pitch,x=>(x>0?'+':'')+x,null,x=>unitSet(id,{speech_pitch:x}),['-12',(+12)+'']),
  seg(T('Wait after you stop talking'),[{v:'quick',t:T('Quick')},{v:'normal',t:T('Normal')},{v:'patient',t:T('Patient')}],u.wait_after_talking||'quick',async m=>(await unitSet(id,{wait_after_talking:m})).ok),h('p',{class:'help'},T('How long it waits in silence before it answers. Patient suits slow talkers.')),
  seg(T('Ignore background noise'),[{v:'low',t:T('Low')},{v:'medium',t:T('Medium')},{v:'high',t:T('High')}],u.ignore_noise||'medium',async m=>(await unitSet(id,{ignore_noise:m})).ok),h('p',{class:'help'},T('Higher ignores more fans and hiss, but may miss quiet speech.')),null);
 const wake=card(T('voice.wake'),T('voice.wake_help'),toggle(T('voice.wake'),null,true,()=>false,true),slider(T('voice.wake_sens'),0,100,5,50,x=>x+'%',null,null,null,true),toggle(T('voice.stop_word'),null,true,()=>false,true));
 const lang=card(S['settings.face.lang'],null,(()=>{const sel=h('select',{'aria-label':S['settings.face.lang'],onchange:e=>save(facePath(id),{screen_lang:e.target.value})});for(const l of (fv.choices?fv.choices.lang:LANGS_ALL))sel.append(h('option',{value:l,selected:l===v.lang},S['settings.lang.'+l]||l));return sel})());
 const quiet=card(h('span',{},T('voice.quiet'),' ',soonBadge()),T('voice.quiet_help'),h('div',{class:'hrs off'},field('',h('input',{type:'time',value:'22:00',disabled:true,'aria-label':T('voice.quiet')})),field('',h('input',{type:'time',value:'07:00',disabled:true,'aria-label':T('voice.quiet')}))));
 const vc=await voiceCards(id,u,v);p.append(h('div',{class:'grid'},vol,speech,...vc,lang,wake,quiet))};

/* ---- NETWORK ---- */
BUILDERS.network=async(p,u)=>{const id=u.device_id;
 const net=card(h('span',{},'Wi-Fi'),null);const nt=await api(unitPath(id,'network-test'),{});const steps=nt.ok&&nt.d.steps?nt.d.steps:[];
 const wl=steps.find(s=>/wifi/i.test(s.step||''));
 net.append(kv([[T('net.current'),S['settings.wifi.'+u.wifi]],[T('net.signal'),wl?wl.line.replace(/^Wi-Fi:\s*/i,''):null],[S['settings.online'],S[u.online?'settings.online.yes':'settings.online.no']]]),
  h('div',{class:'row off'},h('div',{class:'lbl'},h('b',{},T('net.join'),' ',soonBadge()),h('span',{},T('net.join_help'))),h('button',{class:'btn',disabled:true,type:'button'},T('net.join'))));
 const tr=await tsCard(p,u);
 const test=card(S['settings.net'],T('system.net_help'));const out=h('div',{});test.append(out,h('button',{class:'btn pri',type:'button',onclick:async()=>{out.replaceChildren(h('p',{class:'hint'},'...'));const r=await api(unitPath(id,'network-test'),{});const d=r.d;
  out.replaceChildren(d.steps&&d.steps.length?simpleList(d.steps.map(s=>[s.state==='ok'?'':s.state==='warn'?'warn':'fail',s.line])):'',h('p',{},d.summary||d.error||''),d.fix?h('p',{class:'hint'},d.fix):null)}},S['settings.net.run']));
 const pair=card(T('net.paired'),T('net.pair_help'),kv([[T('system.host'),HOST],[S['settings.device_id'],id]]));
 p.append(h('div',{class:'grid'},net,tr,test,pair))};


async function tsCard(p,u){const id=u.device_id,tv=await api(unitPath(id,'travel')),c=card(T('units.travel'),T('units.travel_help'));
 const again=()=>{BUILT.network=false;p.querySelectorAll(':scope>:not(h1)').forEach(n=>n.remove());go('network',true)};
 c.append(h('ol',{class:'how'},h('li',{},T('ts.step1'),' ',h('a',{class:'lnk',href:'https://login.tailscale.com/admin/settings/keys',target:'_blank',rel:'noopener noreferrer'},T('ts.step1_link'))),h('li',{},T('ts.step2')),h('li',{},T('ts.step3'))),
  h('h3',{},T('ts.happens')),h('ul',{class:'steps'},['h1','h2','h3','h4'].map(k=>h('li',{},T('ts.'+k)))));
 const about=h('details',{},h('summary',{style:'cursor:pointer;font-weight:600;min-height:44px;display:flex;align-items:center'},T('ts.about')),h('p',{class:'hint'},T('ts.about_body')),h('p',{},h('a',{class:'lnk',href:'https://github.com/getmaipai/stackchan/blob/main/docs/user/use-it-anywhere.md',target:'_blank',rel:'noopener noreferrer'},T('ts.guide'))));
 if(!(tv.ok&&tv.d.available)){c.append(h('div',{class:'banner'},tv.ok?(tv.d.error||T('ts.err.not_compiled')):(tv.d.error||T('net_error'))),h('span',{class:'badge'},T('soon')),about);return c}
 const d=tv.d;const errText={refusal:T('ts.err.refusal'),key:T('ts.err.bad_key'),error:T('ts.err.bad_key')}[d.last_error]||'';
 c.append(h('h3',{},T('units.travel_state')),kv([[T('units.travel_state'),T('ts.state.'+d.phase)],[T('ts.addr'),d.ip||''],[T('ts.route'),d.route==='private'?T('ts.route.private'):T('ts.route.home')],[T('ts.last_error'),errText]]));
 c.append(toggle(T('net.private_on'),null,!!d.enabled,async on=>(await save(unitPath(id,'travel'),{enabled:on})).ok));
 const key=h('input',{type:'password',autocomplete:'off',spellcheck:'false','aria-label':T('units.travel_key'),name:'ts-'+uid()});
 const peer=h('input',{type:'text',inputmode:'decimal',autocomplete:'off',value:d.peer||'','aria-label':T('net.hub_addr'),name:'ts-'+uid()});
 c.append(field(T('units.travel_key'),key),h('p',{class:'hint'},T('units.travel_hidden')),
  h('div',{class:'btns'},h('button',{class:'btn pri',type:'button',onclick:async()=>{const r=await save(unitPath(id,'travel'),{key:key.value});if(r.ok){key.value='';again()}}},T('units.travel_send'))),
  field(T('net.hub_addr'),peer),h('p',{class:'hint'},d.peer_saved?S['settings.saved']:''),
  h('div',{class:'btns'},h('button',{class:'btn pri',type:'button',onclick:async()=>{const r=await save(unitPath(id,'travel'),{peer:peer.value});if(r.ok)again()}},T('ts.peer_save'))));
 const out=h('p',{role:'status'});
 c.append(h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:async e=>{const b=e.currentTarget;b.disabled=true;const r=await api(unitPath(id,'travel'));b.disabled=false;const x=r.d;
   out.textContent=!r.ok||!x.available?(x.error||T('net_error')):x.phase==='connected'?T('ts.test.ok'):!x.ready_to_use?T('ts.test.nokey'):x.last_error?errOf(x):T('ts.test.ready')}},T('ts.test')),
  h('button',{class:'btn bad',type:'button',onclick:async()=>{if(await ask(T('units.travel_forget')+'?',T('units.travel_forget'))){const r=await save(unitPath(id,'travel'),{forget:true});if(r.ok)again()}}},T('units.travel_forget'))),out,about);
 function errOf(x){return {refusal:T('ts.err.refusal'),key:T('ts.err.bad_key'),error:T('ts.err.bad_key')}[x.last_error]||''}
 return c}

/* ---- BEHAVIOR ---- */
BUILDERS.behavior=async(p,u)=>{const id=u.device_id,ov=await api(unitPath(id,'overview')),sv=ov.ok?ov.d.saved:{idle_motion:true},pr=ov.ok?ov.d.privacy:null;
 const body=card(T('beh.head'),null,seg(T('Idle movement'),[{v:'off',t:T('Off')},{v:'calm',t:T('Calm')},{v:'lively',t:T('Lively')}],sv.idle_movement||'off',async m=>(await save(unitPath(id,'device'),{idle_movement:m})).ok),h('p',{class:'help'},T('Off keeps the head still until it is spoken to. Calm and lively let it look around when nobody is talking.')),
  toggle(T('Look toward the speaker'),T('Turns or glances toward you when you start talking.'),!!sv.look_speaker,async on=>(await save(unitPath(id,'device'),{look_speaker:on})).ok),
  toggle(T('wake_look'),T('wake_look_help'),sv.look_on_wake!==false,async on=>(await save(unitPath(id,'device'),{look_on_wake:on})).ok),
  toggle(T('Look for faces'),T('Searches the room with the camera when something moves. Needs the camera on.'),!!sv.look_faces,async on=>(await save(unitPath(id,'device'),{look_faces:on})).ok),
  toggle(T('beh.sleep'),T('beh.sleep_help'),false,()=>false,true));
 const seek=await lookSeekCard(id,sv);
 const swipe=await swipePagesCard(id);
 const priv=card(S['settings.ui.nav.privacy'],T('privacy.lead'),toggle(T('beh.vision'),T('beh.vision_help'),pr?pr.vision_off:false,async on=>(await save(unitPath(id,'device'),{vision_off:on})).ok,!pr),
  toggle(T('beh.quiet_mode'),T('beh.quiet_mode_help'),pr?pr.quiet:false,async on=>(await save(unitPath(id,'device'),{quiet:on})).ok,!pr),
  toggle(T('voice.mic_mute'),T('voice.mute_help'),pr?pr.mute:u.muted,async on=>(await save(unitPath(id,'device'),{mute:on})).ok,!pr));
 p.append(h('div',{class:'grid'},body,seek,priv,musicCard(id,sv)),h('div',{class:'stack',style:'margin-top:18px'},...(swipe?[swipe]:[]),await timeCard(u),await alarmCard(u),await reactCard(u),await peopleCard(u)))};
/* Dance to music: the unit measures sound levels and tempo only; the host turns the dance controller on (off until chosen). */
function musicCard(id,sv){const st=h('p',{class:'hint',role:'status'},T('pol.dance.status.'+(sv.dance_status||'off')));
 const c=card(T('pol.dance.title'),T('pol.dance.privacy'),toggle(T('pol.dance.toggle'),T('pol.dance.help'),!!sv.dance_to_music,async on=>{const r=await save(unitPath(id,'device'),{dance_to_music:on});if(r.ok&&r.d.status)st.textContent=T('pol.dance.status.'+r.d.status);return r.ok}),st);return c}
async function timeCard(u){const id=u.device_id,cv=await api(unitPath(id,'clock')),fv=await faceView(id),v=fv.values||{},has=f=>fv.features==null||(fv.features||[]).includes(f);
 const c=card(S['settings.clock'],T('time.zone_help'));
 if(cv.ok&&cv.d.zones){const sel=h('select',{'aria-label':S['settings.clock.zone'],onchange:e=>save(unitPath(id,'clock'),{zone:e.target.value})});for(const z of cv.d.zones)sel.append(h('option',{value:z.id,selected:z.id===cv.d.zone},z.label));
  c.append(field(S['settings.clock.zone'],sel),h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>save(unitPath(id,'clock'),{sync:true})},S['settings.clock.sync'])))}
 else c.append(h('div',{class:'banner'},(cv.d&&cv.d.error)||T('net_error')));
 if(fv.values){c.append(toggle(T('face.clock24'),null,v.clock24,async on=>(await save(facePath(id),{clock24:on})).ok,!has('clock')),
  seg(T('face.clock_style'),[{v:'digits',t:T('face.clock_digits')},{v:'ring',t:T('face.clock_ring')}],v.clock_style,async s=>(await save(facePath(id),{clock_style:s})).ok,!has('clock')),
  slider(T('face.clock_idle'),0,3600,30,v.clock_idle_s,x=>x===0?T('face.never'):x+' '+T('face.seconds'),null,x=>save(facePath(id),{clock_idle_s:x}),null,!has('clock')))}
 c.append(h('h3',{},T('time.timers')),h('p',{class:'hint'},T('time.timers_help')));return c}
async function alarmCard(u){const id=u.device_id;let rows=(u.alarms||[]).map(a=>({time:a.time,label:a.label||'',days:a.days||['mon','tue','wed','thu','fri','sat','sun']}));
 const c=card(S['settings.alarms'],T('time.alarms_help'));const list=h('div',{class:'list'});
 const DAYS=['mon','tue','wed','thu','fri','sat','sun'];
 const persist=()=>unitSet(id,{alarms:rows.filter(r=>/^\d\d:\d\d$/.test(r.time)&&r.days.length)});
 const draw=()=>{list.replaceChildren();if(!rows.length)list.append(h('div',{class:'empty'},T('time.no_alarms')));
  rows.forEach((r,i)=>list.append(h('div',{class:'item'},h('input',{type:'time',value:r.time,style:'width:130px','aria-label':S['settings.alarm_time'],onchange:e=>{r.time=e.target.value;persist()}}),
   h('input',{type:'text',value:r.label,maxlength:60,class:'grow','aria-label':S['settings.alarm_label'],style:'flex:1 1 140px;width:auto',onchange:e=>{r.label=e.target.value;persist()}}),
   h('div',{class:'days'},DAYS.map(d=>h('button',{type:'button',class:'pill','aria-pressed':String(r.days.includes(d)),onclick:e=>{r.days=r.days.includes(d)?r.days.filter(x=>x!==d):DAYS.filter(x=>x===d||r.days.includes(x));e.target.setAttribute('aria-pressed',String(r.days.includes(d)));persist()}},T('day.'+d)))),
   h('button',{class:'btn',type:'button',onclick:()=>{rows.splice(i,1);draw();persist()}},T('time.remove')))))};
 draw();c.append(list,h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>{rows.push({time:'07:30',label:'',days:DAYS.slice()});draw();persist()}},S['settings.alarm_add'])));return c}
async function reactCard(u){const id=u.device_id,r=await api(unitPath(id,'reactions')),c=card(S['settings.react'],S['settings.react.help']);
 if(!r.ok){c.append(h('div',{class:'banner'},r.d.error||T('net_error')));return c}
 let rows=r.d.rows.map(x=>Object.assign({},x));const ch=r.d.choices;let dirty=false;
 const list=h('div',{class:'list'});const saveB=h('button',{class:'btn pri',type:'button',disabled:true,onclick:async()=>{const k=await save(unitPath(id,'reactions'),{rows});if(k.ok){dirty=false;saveB.disabled=true;note.hidden=true}}},S['settings.react.save']);
 const note=h('p',{class:'hint',hidden:!r.d.builtin},S['settings.react.builtin']);const mark=()=>{dirty=true;saveB.disabled=false};
 const sel=(row,key,vals,lab)=>field(lab,(()=>{const s=h('select',{onchange:e=>{row[key]=e.target.value;mark()}});for(const v of vals)s.append(h('option',{value:v,selected:v===row[key]},key==='decor'&&v!=='none'?S['settings.decor.'+v]:pretty(v)));return s})());
 const draw=()=>{list.replaceChildren(h('div',{class:'rx h','aria-hidden':'true'},h('span',{},T('react.words')),h('span',{},T('react.face')),h('span',{},T('react.sound')),h('span',{},T('react.extra')),h('span',{},T('react.dance')),h('span',{})));
  rows.forEach((row,i)=>list.append(h('div',{class:'rx'},field(T('react.words'),h('input',{type:'text',value:row.say,maxlength:23,onchange:e=>{row.say=e.target.value;mark()}})),sel(row,'face',ch.face,T('react.face')),sel(row,'sound',ch.sound,T('react.sound')),sel(row,'decor',ch.decor,T('react.extra')),sel(row,'dance',ch.dance,T('react.dance')),h('button',{class:'btn',type:'button','aria-label':T('time.remove')+' '+row.say,onclick:()=>{rows.splice(i,1);draw();mark()}},'×'))))};
 draw();c.append(note,h('div',{class:'list',style:'max-height:520px;overflow:auto;padding-right:4px'},list),h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>{rows.push({say:'',face:'happy',sound:'none',decor:'none',dance:'none'});draw();mark()}},T('react.add')),saveB,
  h('button',{class:'btn',type:'button',onclick:async()=>{const k=await save(unitPath(id,'reactions')+'/reset',{});if(k.ok){const n=await api(unitPath(id,'reactions'));rows=n.d.rows;note.hidden=false;dirty=false;saveB.disabled=true;draw()}}},S['settings.react.reset'])));return c}
async function peopleCard(u){const id=u.device_id,r=await api('/api/stackchan/people'),c=card(S['settings.people'],T('people.empty_help'));
 if(!r.ok){c.append(h('div',{class:'banner'},r.d.error||T('net_error')));return c}
 let d=r.d;const list=h('div',{class:'list'});
 const one=(person)=>{const p=Object.assign({id:'',name:'',color:'none',caption_size:'medium',wake_phrase:''},person);
  const name=h('input',{type:'text',value:p.name,maxlength:24}),wake=h('input',{type:'text',value:p.wake_phrase,maxlength:24});
  const sw=swatches(S['settings.people.color'],d.choices.color,p.color,x=>{p.color=x});
  const sz=seg(S['settings.people.caption'],d.choices.caption_size.map(s=>({v:s,t:S['settings.face.caption_size.'+s]})),p.caption_size,x=>{p.caption_size=x});
  const row=h('div',{class:'item',style:'display:grid;gap:12px'},h('div',{class:'hrs'},field(S['settings.people.name'],name),field(S['settings.people.wake'],wake)),sw,sz,h('div',{class:'btns'},
   h('button',{class:'btn pri',type:'button',onclick:async()=>{const k=await save('/api/stackchan/people',{id:p.id,name:name.value,color:p.color,caption_size:p.caption_size,wake_phrase:wake.value});if(k.ok){d=k.d;draw()}}},S['settings.people.save']),
   p.id?h('button',{class:'btn',type:'button',onclick:()=>save('/api/stackchan/people/'+encodeURIComponent(p.id)+'/use/'+encodeURIComponent(id),{})},S['settings.people.use']):null,
   p.id?h('button',{class:'btn bad',type:'button',onclick:async()=>{const k=await api('/api/stackchan/people/'+encodeURIComponent(p.id)+'/remove',{});if(k.ok){d=k.d;draw()}}},S['settings.people.remove']):null));return row};
 const draw=()=>{list.replaceChildren();if(!d.people.length)list.append(h('div',{class:'empty'},S['settings.people.none']));for(const x of d.people)list.append(one(x))};
 draw();const add=h('div',{});c.append(list,h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>{add.replaceChildren(one({}));add.scrollIntoView({block:'nearest'})}},T('people.add'))),add);return c}

/* ---- GAMES AND FUN ---- */
BUILDERS.play=async(p,u)=>{const id=u.device_id,g=await api(unitPath(id,'games')),fv=await faceView(id);
 const games=card(S['settings.games'],null);
 if(g.ok&&g.d.games){if(g.d.playing)games.append(h('div',{class:'banner'},T('games.playing')));
  const L=h('div',{class:'list'});for(const x of g.d.games)L.append(h('div',{class:'item'},h('div',{class:'grow'},h('b',{},x.title)),h('div',{class:'pills'},x.scores.length?x.scores.map((s,i)=>h('span',{class:'badge',title:T('games.best')},(i===0?T('games.best')+' ':'')+s+(x.unit?' '+x.unit:''))):h('span',{class:'hint'},T('games.empty')))));games.append(L)}
 else games.append(h('div',{class:'banner'},(g.d&&g.d.error)||T('net_error')),h('span',{class:'badge'},T('soon')));
 const tk=g.d&&g.d.talk,talkCard=tk?card(tk.title,tk.help,h('div',{class:'list'},...tk.games.map(x=>h('div',{class:'item'},h('div',{class:'grow'},h('b',{},x.title),h('div',{class:'hint'},x.hint)))))):null;
 const decor=card(S['settings.extra'],null);let pickd=null;
 const view=window.__faceviews||(window.__faceviews={});
 if(fv.choices){const cv=h('canvas',{width:640,height:480,role:'img','aria-label':T('preview')});const v=fv.values;const face=new Face(cv,{style:v.style,color:v.color,background:v.background,tint:v.emotion_tint});
  const pills=h('div',{class:'pills'});for(const n of fv.choices.decorators){const b=h('button',{class:'pill',type:'button','aria-pressed':'false',onclick:async()=>{pills.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));face.set({decor:n});save(unitPath(id,'decorate'),{name:n,seconds:6},true)}},S['settings.decor.'+n]||pretty(n));pills.append(b)}
  decor.append(h('div',{class:'screen'},cv),pills,h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>{pills.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed','false'));face.set({decor:'none'});save(unitPath(id,'decorate'),{name:'none'},true)}},S['settings.extra.stop'])))}
 else decor.append(h('div',{class:'banner'},fv.error||T('net_error')));
 p.append(h('div',{class:'grid'},games,...(talkCard?[talkCard]:[]),decor))};

/* ---- SYSTEM ---- */
BUILDERS.system=async(p,u)=>{const id=u.device_id;
 const name=h('input',{type:'text',value:u.name,maxlength:40,onchange:async e=>{const r=await unitSet(id,{name:e.target.value});if(r.ok){u.name=e.target.value;drawChips()}}});
 const persona=h('textarea',{value:u.persona,maxlength:2000,onchange:e=>unitSet(id,{persona:e.target.value})});
 const url=h('input',{type:'text',value:u.llm.url||''}),model=h('input',{type:'text',value:u.llm.model||''}),key=h('input',{type:'text',value:u.llm.api_key_env||''});
 const llmSave=()=>unitSet(id,{llm:{url:url.value,model:model.value,api_key_env:key.value}});[url,model,key].forEach(i=>i.addEventListener('change',llmSave));
 const unit=card(S['settings.unit'],null,field(S['settings.unit_name'],name),field(S['settings.persona'],persona),h('p',{class:'hint'},T('units.persona_help')),
  h('details',{},h('summary',{style:'cursor:pointer;font-weight:600;min-height:44px;display:flex;align-items:center'},S['settings.llm']),h('div',{class:'list',style:'margin-top:10px'},field(S['settings.llm_url'],url),field(S['settings.llm_model'],model),field(S['settings.llm_key_env'],key))));
 const det=card(S['settings.details'],null);const dd=await api(unitPath(id,'details'));
 if(dd.ok&&dd.d.version){const d=dd.d,free=d.internal_free||0,low=d.internal_min||0;det.append(kv([[S['settings.firmware'],d.version],['Tag',d.tag],[T('sys.storage'),d.image+', '+d.slot],[T('sys.memory'),bytesWord(free)+' '+T('sys.free')+', '+bytesWord(low)+' '+T('sys.lowest')]]),
  h('div',{class:'meter','aria-hidden':'true'},h('i',{style:'width:'+clamp(free/1000/1.2,2,100)+'%'})))}
 else det.append(h('div',{class:'banner'},(dd.d&&dd.d.error)||T('net_error')));
 const upd=card(T('nav.system'),T('system.update_help'));const out=h('p',{role:'status'});
 upd.append(kv([[S['settings.firmware'],u.firmware_version||S['settings.firmware.unknown']]]),out,h('div',{class:'btns'},h('button',{class:'btn pri',type:'button',onclick:async()=>{const r=await api(setPath(id)+'/update',{});out.textContent=r.ok?(r.d.message||''):(r.d.error||'')}},T('system.check')),
  h('button',{class:'btn',type:'button',onclick:async()=>{if(await ask(S['settings.update_confirm_ask'],S['settings.update_confirm'])){const r=await api(setPath(id)+'/update',{confirm:true});out.textContent=r.ok?(r.d.message||''):(r.d.error||'');if(!r.ok)toast(r.d.error,'bad')}}},S['settings.update_confirm'])));
 const rst=card(T('sys.restart'),T('sys.restart_help'),h('div',{class:'btns'},h('button',{class:'btn',disabled:true,type:'button'},T('sys.restart'),' ',soonBadge())));
 const word=h('input',{type:'text',autocomplete:'off','aria-label':T('sys.reset_type')});
 const reset=card(T('sys.reset'),T('sys.reset_help'),field(T('sys.reset_type'),word),h('div',{class:'btns'},h('button',{class:'btn bad',type:'button',onclick:async()=>{if(word.value!=='RESET'){toast(T('sys.reset_type'),'bad');return}if(await ask(T('sys.reset_help'),T('sys.reset_go'))){const r=await save(unitPath(id,'reset'),{confirm_word:word.value});if(r.ok)word.value=''}}},T('sys.reset_go'))));
 const lk=(t,u2)=>h('a',{class:'lnk',href:u2,target:'_blank',rel:'noopener noreferrer'},t);
 const about=card(T('sys.about'),T('sys.source_note'),kv([[S['settings.firmware'],u.firmware_version||S['settings.firmware.unknown']],[T('sys.host_version'),HOSTV],[T('sys.license'),'GNU AGPL-3.0']]),
  h('div',{class:'list'},h('div',{},lk(T('sys.source'),'https://github.com/getmaipai/stackchan')),h('div',{},lk(T('sys.docs'),'https://github.com/getmaipai/stackchan/tree/main/docs/user'))));
 p.append(h('div',{class:'grid'},unit,det,upd,about,rst,reset))};
"""

JS = JS.replace("/*__FACE_SHAPES__*/", face_js() + banner_js() + overlay_js()) + JS_POLISH + JS_PAGES_FULL + JS_LOCK + JS_LINK + JS_FAMILY + JS_CHARACTER

PAGE = r"""<!doctype html><html lang='__CODE__'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<meta name='color-scheme' content='light dark'>
<title>__TITLE__</title>
<style>__CSS__</style>
</head><body>
<noscript>__TITLE__</noscript>
<script>
const S=__STRINGS__;
__JS__
__PICS__
main();
</script></body></html>"""
