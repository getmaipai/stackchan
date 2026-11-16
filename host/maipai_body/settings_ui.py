# ruff: noqa: E501
"""The look and the behaviour of the settings page: styles, the live face drawing and every panel.

``render_page`` in ``settings_page`` fills ``__STRINGS__`` and ``__LANG__`` and adds the picture-face panel. The page
is plain HTML, CSS and JavaScript with no outside file, no font download and no network call except to this host.
Colours are tokens (CSS variables) that follow the browser's light or dark setting or the page's own switch.
"""

from __future__ import annotations

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
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

JS = r"""
const BASE={lang:'__LANG__'},LANG='__LANG__';
try{const th=localStorage.getItem('theme');if(th&&th!=='auto')document.documentElement.setAttribute('data-theme',th)}catch(e){}
const T=k=>S['settings.ui.'+k]||k;
const $=(s,r)=>(r||document).querySelector(s);
const ICO={home:'M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10',remote:'M12 2v4M12 18v4M2 12h4M18 12h4M12 8l-3 3 3 3 3-3z',look:'M12 3a9 9 0 100 18 9 9 0 000-18zM9 10v2M15 10v2M9 15c1.5 1.4 4.5 1.4 6 0',voice:'M12 3a3 3 0 013 3v6a3 3 0 01-6 0V6a3 3 0 013-3zM5 11a7 7 0 0014 0M12 18v3',network:'M2 9a15 15 0 0120 0M5 12.5a10 10 0 0114 0M8.5 16a5 5 0 017 0M12 19.5h.01',behaviour:'M4 6h16M4 12h16M4 18h16M8 4v4M16 10v4M10 16v4',play:'M6 12h4M8 10v4M15 11h.01M18 13h.01M17 7H7a5 5 0 00-4.9 6l.7 3.6A2.5 2.5 0 007.3 17.8l.9-1.3h7.6l.9 1.3a2.5 2.5 0 004.5-1.2l.7-3.6A5 5 0 0017 7z',system:'M12 8a4 4 0 100 8 4 4 0 000-8zM12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1'};
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
 for(const c of vals)g.append(h('button',{type:'button',role:'radio','data-v':c,class:'swatch'+(c==='none'?' none':''),style:c==='none'?null:'background:'+PAL[c],title:S['settings.face.colour.'+c]||c,'aria-label':S['settings.face.colour.'+c]||c,onclick:async()=>{const old=val;val=c;draw();const ok=await fn(c);if(ok===false){val=old;draw()}}}));
 draw();g.redraw=v=>{val=v;draw()};return g}
function field(label,el){return h('label',{class:'f'},label,el)}
function ask(text,okLabel){return new Promise(res=>{const d=h('dialog',{},h('p',{},text),h('div',{class:'btns'},
 h('button',{class:'btn bad',type:'button',onclick:()=>{d.close('ok')}},okLabel),h('button',{class:'btn',type:'button',onclick:()=>d.close('no')},T('cancel'))));
 d.addEventListener('close',()=>{res(d.returnValue==='ok');d.remove()});document.body.append(d);d.showModal()})}
function loading(el){el.append(h('div',{class:'empty'},'...'))}

/* ---- the face drawing: same shapes as the unit's styles (320 by 240 screen) ---- */
const PAL={none:'#f4f4f4',mint:'#5fe0b5',sky:'#6cc3ff',amber:'#ffbf47',rose:'#ff8fa3',lilac:'#b48cff',lime:'#b9e65c',coral:'#ff7a5c'};
const colourOf=c=>PAL[c]||(/^#[0-9a-f]{6}$/i.test(c)?c:PAL.none);
const GEO={classic:{ew:56,eh:72,gap:140,ey:94,my:172,mw:74,r:.9},big_eyes:{ew:96,eh:104,gap:170,ey:98,my:200,mw:30,r:1},minimal:{ew:28,eh:40,gap:124,ey:104,my:160,mw:46,r:1},round:{ew:84,eh:84,gap:150,ey:100,my:196,mw:56,r:1},cat:{ew:72,eh:78,gap:150,ey:98,my:190,mw:44,r:1},robot:{ew:68,eh:62,gap:142,ey:100,my:196,mw:90,r:.14},sleepy:{ew:80,eh:70,gap:150,ey:112,my:198,mw:36,r:1},retro_pixel:{ew:64,eh:72,gap:136,ey:96,my:184,mw:72,r:.1},heart_eyes:{ew:80,eh:74,gap:150,ey:100,my:194,mw:56,r:1}};
const ST={neutral:{mc:.2},happy:{cheek:1,mc:1,mo:.3},sad:{slant:-.55,lid:.16,mc:-1,gy:5},angry:{slant:.85,lid:.3,mc:-.6},thinking:{gx:12,gy:-10,lid:.15,mOn:0},sleepy:{lid:.55,gy:3,mc:0},speaking:{mc:.25},love:{heart:1,mc:1,mo:.3}};
const KEYS=['ew','eh','lid','slant','cheek','mc','mo','mOn','heart','gx','gy'];
const HELLO={en:'Hello!',es:'Hola!',fr:'Bonjour!',de:'Hallo!',pt:'Ola!',it:'Ciao!'};
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const rnd=(a,b)=>a+Math.random()*(b-a);
const REDUCED=(()=>{try{return matchMedia('(prefers-reduced-motion: reduce)').matches}catch(e){return false}})();
function rr(c,x,y,w,hh,r){r=Math.min(r,w/2,hh/2);c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+hh,r);c.arcTo(x+w,y+hh,x,y+hh,r);c.arcTo(x,y+hh,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath()}
function heartP(c,x,y,s){c.beginPath();c.moveTo(x,y+s*.48);c.bezierCurveTo(x-s*.95,y-s*.05,x-s*.52,y-s*.72,x,y-s*.22);c.bezierCurveTo(x+s*.52,y-s*.72,x+s*.95,y-s*.05,x,y+s*.48);c.closePath()}
function star(c,x,y,r){const k=.16;c.beginPath();c.moveTo(x,y-r);c.quadraticCurveTo(x+r*k,y-r*k,x+r,y);c.quadraticCurveTo(x+r*k,y+r*k,x,y+r);c.quadraticCurveTo(x-r*k,y+r*k,x-r,y);c.quadraticCurveTo(x-r*k,y-r*k,x,y-r);c.fill()}
const views=new Set();
class Face{constructor(cv,o){this.cv=cv;this.d=cv.getContext('2d');this.w=cv.width;this.hh=cv.height;
 this.o=Object.assign({style:'classic',colour:'none',state:'neutral',mode:'face',captions:false,size:'medium',lang:'en',decor:'none',dim:0,c24:false,cstyle:'digits',live:true},o||{});
 this.st=document.createElement('canvas');this.st.width=640;this.st.height=480;this.sc=this.st.getContext('2d');
 this.lo=document.createElement('canvas');this.lo.width=80;this.lo.height=60;this.lc=this.lo.getContext('2d');
 this.t=rnd(0,5);this.P={};this.snap();this.gx=0;this.gy=0;this.gtx=0;this.gty=0;this.gn=1;this.bl=0;this.bs=-1;this.bn=rnd(1,3);this.v=0;this.vt=0;this.vtg=0;this.vis=true;
 if(this.o.live){views.add(this);if('IntersectionObserver' in window)new IntersectionObserver(e=>{this.vis=e[0].isIntersecting}).observe(cv)}this.draw()}
 set(o){Object.assign(this.o,o);if(!this.o.live)this.drawOnce()}
 target(){const g=GEO[this.o.style]||GEO.classic,s=ST[this.o.state]||ST.neutral,L=this.o.style==='sleepy'?.3:0,T={};
  T.ew=g.ew*(s.heart?1:1);T.eh=g.eh;T.lid=Math.max(s.lid||0,L);T.slant=s.slant||0;T.cheek=s.cheek||0;T.mc=s.mc!==undefined?s.mc:.2;T.mo=s.mo||0;T.mOn=s.mOn!==undefined?s.mOn:1;T.heart=(s.heart||0)||(this.o.style==='heart_eyes'?1:0);T.gx=s.gx||0;T.gy=s.gy||0;
  if(this.o.dim>0)T.lid=Math.max(T.lid,this.o.dim*.5);return T}
 snap(){this.T=this.target();for(const k of KEYS)this.P[k]=this.T[k]}
 step(dt){this.t+=dt;this.T=this.target();const a=1-Math.exp(-dt*14);for(const k of KEYS)this.P[k]+=(this.T[k]-this.P[k])*a;
  if(REDUCED){this.gx=0;this.gy=0;this.bl=0;return}
  if(this.o.state==='speaking'){this.vt-=dt;if(this.vt<=0){if(Math.random()<.22){this.vtg=0;this.vt=rnd(.15,.45)}else{this.vtg=rnd(.35,1);this.vt=rnd(.08,.18)}}this.v+=(this.vtg-this.v)*Math.min(1,dt/.06);this.P.mo=this.v}
  this.gn-=dt;const D=(GEO[this.o.style]||GEO.classic).ew/9;if(this.gn<=0){this.gn=rnd(.8,2.2);this.gtx=rnd(-D,D);this.gty=rnd(-D*.6,D*.6)}
  const ga=Math.min(1,dt/.1);this.gx+=(this.gtx+this.P.gx-this.gx)*ga;this.gy+=(this.gty+this.P.gy-this.gy)*ga;
  if(this.bs<0){this.bn-=dt;if(this.bn<=0&&this.P.heart<.3){this.bs=this.t}}
  if(this.bs>=0){const e=this.t-this.bs;if(e<.06)this.bl=e/.06;else if(e<.15){const u=1-(e-.06)/.09;this.bl=u*u}else{this.bl=0;this.bs=-1;this.bn=rnd(2.5,6)}}}
 paint(c){const o=this.o,P=this.P,g=GEO[o.style]||GEO.classic,col=colourOf(o.colour),t=this.t,br=REDUCED?0:Math.sin(t*1.57)*1.6;
  const L=160-g.gap/2,R=160+g.gap/2,ey=g.ey+br,eh=g.eh*(1-this.bl*.95),ew=g.ew;const ea=1-clamp(P.heart,0,1);
  c.save();c.lineCap='round';c.lineJoin='round';c.fillStyle=col;c.strokeStyle=col;
  const shape=(x,y,w,hh)=>{if(g.r<1){rr(c,x-w/2,y-hh/2,w,hh,Math.min(w,hh)/2*g.r)}else{c.beginPath();c.ellipse(x,y,w/2,hh/2,0,0,6.2832)}};
  if(ea>.02){c.globalAlpha=ea;for(const side of[-1,1]){const cx=(side<0?L:R)+this.gx,cy=ey+this.gy,hh=Math.max(3,eh);
   c.save();shape(cx,cy,ew,hh);c.clip();c.fillStyle=col;c.fillRect(cx-ew/2-2,cy-hh/2-2,ew+4,hh+4);
   if(o.style==='big_eyes'||o.style==='round'||o.style==='cat'){c.fillStyle='#000';const pr=Math.min(ew,hh)*.3;
    if(o.style==='cat'){c.beginPath();c.ellipse(cx+this.gx*.6,cy,pr*.34,hh*.42,0,0,6.2832);c.fill()}else{c.beginPath();c.arc(cx+this.gx*.8,cy+this.gy*.5+hh*.04,pr,0,6.2832);c.fill();c.fillStyle=col;c.beginPath();c.arc(cx+this.gx*.8-pr*.34,cy+this.gy*.5-pr*.3,pr*.28,0,6.2832);c.fill()}}
   if(o.style==='robot'){c.fillStyle='rgba(0,0,0,.35)';c.fillRect(cx-ew/2,cy-3+Math.sin(t*3+side)*hh*.3,ew,5)}
   if(P.lid>.005||Math.abs(P.slant)>.005){const x0=cx-ew/2-3,x1=cx+ew/2+3,top=cy-hh/2,yl=x=>top+P.lid*hh+P.slant*hh*.45*(-side)*((x-cx)/(ew/2));
    c.save();c.globalCompositeOperation='destination-out';c.fillStyle='#000';c.beginPath();c.moveTo(x0,top-8);c.lineTo(x1,top-8);c.lineTo(x1,yl(x1));c.lineTo(x0,yl(x0));c.closePath();c.fill();c.restore()}
   if(P.cheek>.01){c.save();c.globalCompositeOperation='destination-out';c.fillStyle='#000';c.beginPath();c.ellipse(cx,cy+hh*(1.05-.45*P.cheek),ew*.85,hh*.55,0,0,6.2832);c.fill();c.restore()}
   c.restore()}c.globalAlpha=1}
  if(P.heart>.02){c.globalAlpha=clamp(P.heart,0,1);const beat=1+.14*Math.pow(Math.max(0,Math.sin(t*7.5)),3);for(const side of[-1,1]){heartP(c,side<0?L:R,ey+2,Math.min(ew,g.eh)*1.05*beat);c.fill()}c.globalAlpha=1}
  if(g.mw>0&&P.mOn>.02&&o.style!=='sleepy'||o.style==='sleepy'&&P.mOn>.02){const w=g.mw,x0=160-w/2,x1=160+w/2,y=g.my+br*.5,cu=P.mc*14,op=P.mo*30,lw=o.style==='minimal'?4:6;c.globalAlpha=clamp(P.mOn,0,1);c.lineWidth=lw;
   c.beginPath();c.moveTo(x0,y);c.bezierCurveTo(x0+w*.28,y+cu*1.5,x0+w*.72,y+cu*1.5,x1,y);
   if(P.mo>.08){c.bezierCurveTo(x0+w*.72,y+cu*1.5+op*1.5,x0+w*.28,y+cu*1.5+op*1.5,x0,y);c.closePath();c.save();c.fillStyle='rgba(0,0,0,.55)';c.fill();c.restore()}c.stroke();c.globalAlpha=1}
  if(o.state==='thinking'){for(let i=0;i<3;i++){const ph=((t/1.2)-i*.18)%1,b=Math.max(0,Math.sin((ph<0?ph+1:ph)*Math.PI*1.6));c.globalAlpha=.35+.65*b;c.beginPath();c.arc(160+(i-1)*26,g.my-b*8,6.5,0,6.2832);c.fill()}c.globalAlpha=1}
  this.decor(c,col,ey,L,R,ew,eh);c.restore()}
 decor(c,col,ey,L,R,ew,eh){const n=this.o.decor,t=this.t;if(!n||n==='none')return;c.fillStyle=col;c.strokeStyle=col;c.lineWidth=4;
  if(n==='sparkles'||n==='stars'){[[L-ew*.7,ey-eh*.5,0],[R+ew*.7,ey-eh*.3,1.3],[160,ey-eh*.8,2.4]].forEach(([x,y,p])=>star(c,x,y,7+9*(.5+.5*Math.sin(t*3+p))))}
  else if(n==='tears'){for(let i=0;i<2;i++){const ph=((t+i)%2)/2,x=(i?R:L)+ew*.18,y=ey+eh/2+8+ph*40;c.globalAlpha=1-ph*ph;c.beginPath();c.arc(x,y,7,0,6.2832);c.fill()}c.globalAlpha=1}
  else if(n==='anger'){const x=R+ew/2+10,y=ey-eh/2-6;for(let i=0;i<4;i++){c.save();c.translate(x,y);c.rotate(i*Math.PI/2);c.beginPath();c.moveTo(4,-12);c.lineTo(4,-4);c.lineTo(12,-4);c.stroke();c.restore()}}
  else if(n==='zzz'){for(let i=0;i<3;i++){const ph=((t/3)+i/3)%1,sz=8+i*4,x=270+ph*14,y=64-ph*36;c.globalAlpha=Math.sin(ph*Math.PI);c.beginPath();c.moveTo(x-sz/2,y-sz/2);c.lineTo(x+sz/2,y-sz/2);c.lineTo(x-sz/2,y+sz/2);c.lineTo(x+sz/2,y+sz/2);c.stroke()}c.globalAlpha=1}
  else if(n==='heart'){for(let i=0;i<3;i++){const ph=((t/2)+i/3)%1;c.globalAlpha=1-ph;heartP(c,120+i*40,150-ph*90,14);c.fill()}c.globalAlpha=1}
  else if(n==='sweat'){const ph=(t%1.6)/1.6;c.beginPath();c.arc(R+ew*.6,ey-eh*.5+ph*30,8,0,6.2832);c.fill()}
  else if(n==='shy'){c.globalAlpha=.5;for(const x of[L-6,R+6]){c.beginPath();c.ellipse(x,ey+eh*.75,22,9,0,0,6.2832);c.fill()}c.globalAlpha=1}
  else if(n==='dizzy'){for(let i=0;i<4;i++){const a=t*3+i*1.57;c.beginPath();c.arc(160+Math.cos(a)*70,ey-eh*.8+Math.sin(a)*14,6,0,6.2832);c.fill()}}}
 clock(c,col){const d=new Date();let hr=d.getHours();const mn=String(d.getMinutes()).padStart(2,'0');let suf='';
  if(!this.o.c24){suf=hr>=12?' PM':' AM';hr=hr%12||12}const txt=(this.o.c24?String(hr).padStart(2,'0'):String(hr))+':'+mn;
  c.fillStyle=col;c.strokeStyle=col;c.textAlign='center';c.textBaseline='middle';
  if(this.o.cstyle==='ring'){c.lineWidth=12;c.globalAlpha=.25;c.beginPath();c.arc(160,120,88,0,6.2832);c.stroke();c.globalAlpha=1;c.beginPath();c.arc(160,120,88,-1.5708,-1.5708+6.2832*(d.getSeconds()+d.getMilliseconds()/1000)/60);c.stroke();c.font='700 54px system-ui,sans-serif';c.fillText(txt,160,118);if(suf){c.font='600 18px system-ui,sans-serif';c.fillText(suf.trim(),160,158)}}
  else{c.font='700 92px system-ui,sans-serif';c.fillText(txt,160,112);if(suf){c.font='600 26px system-ui,sans-serif';c.fillText(suf.trim(),160,176)}}}
 draw(){const o=this.o,d=this.d;d.setTransform(1,0,0,1,0,0);d.fillStyle='#000';d.fillRect(0,0,this.w,this.hh);
  const sc=this.sc;sc.setTransform(1,0,0,1,0,0);sc.clearRect(0,0,640,480);sc.setTransform(2,0,0,2,0,0);
  if(o.mode==='clock')this.clock(sc,colourOf(o.colour));else this.paint(sc);
  if(o.captions&&o.mode==='face'){const px={small:14,medium:18,large:24}[o.size]||18;sc.fillStyle='rgba(0,0,0,.6)';sc.fillRect(0,240-px*1.9,320,px*1.9);sc.fillStyle=colourOf(o.colour);sc.font='600 '+px+'px system-ui,sans-serif';sc.textAlign='center';sc.textBaseline='middle';sc.fillText(HELLO[o.lang]||HELLO.en,160,240-px*.95)}
  if(o.style==='retro_pixel'&&o.mode==='face'){this.lc.imageSmoothingEnabled=true;this.lc.clearRect(0,0,80,60);this.lc.drawImage(this.st,0,0,80,60);d.imageSmoothingEnabled=false;d.drawImage(this.lo,0,0,this.w,this.hh)}
  else{d.imageSmoothingEnabled=true;d.drawImage(this.st,0,0,this.w,this.hh)}
  if(o.dim>0){d.fillStyle='rgba(0,0,0,'+(o.dim*.45)+')';d.fillRect(0,0,this.w,this.hh)}}
 drawOnce(){this.snap();this.bl=0;this.gx=0;this.gy=0;this.draw()}}
let last=performance.now(),acc=0;
function loop(now){const dt=Math.min(.05,(now-last)/1000);last=now;acc+=dt;
 if(acc>=1/30&&!document.hidden){const s=acc;acc=0;for(const v of views){if(!v.cv.isConnected){views.delete(v);continue}if(!v.vis)continue;v.step(s);v.draw()}}
 requestAnimationFrame(loop)}
requestAnimationFrame(loop);
function bandNow(hours){const hr=new Date().getHours();return hr>=hours[3]||hr<hours[0]?'night':hr>=hours[2]?'evening':hr>=hours[1]?'day':'morning'}

/* ---- the page frame: units, groups, theme, language ---- */
const GROUPS=['home','remote','look','voice','network','behaviour','play','system'];
const NAMEKEY={home:'g.home',remote:'g.remote',look:'g.look',voice:'g.voice',network:'g.network',behaviour:'g.behaviour',play:'g.play',system:'g.system'};
let UNITS=[],UNIT=null,CUR='home',BUILT={};
const panels={};
const lsGet=k=>{try{return localStorage.getItem(k)}catch(e){return null}};
const lsSet=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
function setTheme(v){const r=document.documentElement;if(v==='auto')r.removeAttribute('data-theme');else r.setAttribute('data-theme',v);lsSet('theme',v)}
function accentFor(u){const k=u&&u.colour;return !k||k==='none'?'#35c79a':colourOf(k)}
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
const remote=(id,body)=>save(unitPath(id,'remote'),body,true);
ICO.beep='M11 5L6 9H3v6h3l5 4zM15.5 8.5a5 5 0 010 7M18.5 6a9 9 0 010 12';ICO.flash='M13 2L4 14h7l-1 8 9-12h-7z';ICO.find='M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-5-5';ICO.say='M21 12a8 8 0 01-11.6 7.1L3 21l1.9-6.4A8 8 0 1121 12z';ICO.dance='M9 18V5l12-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0zM21 16a3 3 0 11-6 0 3 3 0 016 0z';ICO.game=ICO.play;ICO.photo='M4 8h3l2-3h6l2 3h3v11H4zM12 11a3.5 3.5 0 100 7 3.5 3.5 0 000-7z';ICO.mute='M11 5L6 9H3v6h3l5 4zM22 9l-6 6M16 9l6 6';ICO.restart='M4 12a8 8 0 108-8M4 4v5h5';ICO.lookaround='M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 100 6 3 3 0 000-6z';ICO.nod='M12 3v14M6 11l6 6 6-6';ICO.shake='M3 12h18M7 7l-5 5 5 5M17 7l5 5-5 5';
async function quickActions(id,reach,muted,onMute){const off=!reach,why=T('rem.offline');let finding=false;
 const fb=bigBtn('find',T('rem.find'),async()=>{const r=await remote(id,{do:'find',on:!finding});if(r.ok){finding=!finding;fb.lastChild.textContent=finding?T('rem.find_stop'):T('rem.find')}else toast(r.d.error,'bad');return r},off,why);
 return [bigBtn('beep',T('rem.beep'),async()=>{const r=await remote(id,{do:'beep'});if(!r.ok)toast(r.d.error,'bad');return r},off,why),
  bigBtn('flash',T('rem.flash'),async()=>{const r=await remote(id,{do:'flash'});if(!r.ok)toast(r.d.error,'bad');return r},off,why),fb]}
BUILDERS.remote=async(p,u)=>{const id=u.device_id,rv=await api(unitPath(id,'remote')),ov=await api(unitPath(id,'overview')),d=rv.ok?rv.d:{reachable:false,dances:[],games:[],limits:{yaw:128,pitch:[5,85]}};
 const reach=!!u.online&&d.reachable!==false,off=!reach,why=T('rem.offline');
 const run=name=>async()=>{const r=await remote(id,Object.assign({do:name}));if(!r.ok)toast(r.d.error,'bad');return r};
 const banner=off?h('div',{class:'banner'},why):null;
 const quick=card(T('rem.quick'),null,banner,h('div',{class:'big'},...(await quickActions(id,reach)),
  bigBtn('lookaround',T('rem.look'),run('look'),off,why),bigBtn('nod',T('rem.nod'),run('nod'),off,why),bigBtn('shake',T('rem.shake'),run('shake'),off,why),
  bigBtn('mute',(ov.ok&&ov.d.privacy&&ov.d.privacy.mute)?T('rem.unmute'):T('rem.mute'),async()=>{const cur=ov.ok&&ov.d.privacy?ov.d.privacy.mute:false;const r=await save(unitPath(id,'device'),{mute:!cur},true);if(r.ok){ov.d.privacy=ov.d.privacy||{};ov.d.privacy.mute=!cur;toast(r.d.message||T('rem.done'));return Object.assign(r,{d:{}})}toast(r.d.error,'bad');return r},off,why),
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
 p.append(h('div',{class:'grid'},quick,say,headc,dance,game,pic))};

/* ---- HOME ---- */
BUILDERS.home=async(p,u)=>{
 const ov=await api(unitPath(u.device_id,'overview')),fv=await faceView(u.device_id);
 const o=ov.ok?ov.d:{reachable:false};const v=fv.values||{};
 const cv=h('canvas',{width:640,height:480,role:'img','aria-label':T('preview')});
 const face=new Face(cv,{style:v.style,colour:v.colour,captions:v.captions,size:v.caption_size,lang:v.lang});
 const pvc=card(T('home.face'),null,h('div',{class:'screen'},cv),h('p',{class:'hint'},(S['settings.face.style.'+v.style]||v.style||'')+', '+(S['settings.face.colour.'+v.colour]||v.colour||'')),h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>go('look')},S['settings.ui.g.look'])));
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
 const face=new Face(cv,{style:v.style,colour:v.colour,captions:v.captions,size:v.caption_size,lang:v.lang,c24:v.clock24,cstyle:v.clock_style});
 const refresh=()=>{face.set({style:v.style,colour:v.colour,captions:v.captions,size:v.caption_size,lang:v.lang,c24:v.clock24,cstyle:v.clock_style,dim:v.tod&&bandNow(v.tod_hours)==='night'?1:0});tiles.forEach(t=>t.set({colour:v.colour}))};
 const put=async patch=>{const old=Object.assign({},v);Object.assign(v,patch);refresh();const r=await save(facePath(id),patch);if(!r.ok){v=old;refresh();return false}if(patch.colour){u.colour=patch.colour;applyAccent();drawChips()}return true};
 const looks=['neutral','happy','sad','angry','thinking','sleepy','speaking','love'];
 const states=seg(T('try_look'),looks.map(s=>({v:s,t:T('state.'+s)})).concat([{v:'clock',t:S['settings.ui.nav.time']}]),'neutral',s=>{if(s==='clock')face.set({mode:'clock'});else face.set({mode:'face',state:s});return true});
 const pv=card(T('preview'),T('preview_note'),h('div',{class:'pv'},h('div',{class:'screen'},cv),states));
 const tiles=[];
 const gallery=h('div',{class:'tiles',role:'radiogroup','aria-label':S['settings.face.style']});
 const gal=[];for(const s of c.style){const tc=h('canvas',{width:160,height:120,'aria-hidden':'true'});const tf=new Face(tc,{style:s,colour:v.colour,live:false});tf.drawOnce();tiles.push(tf);
  const off=!has('packs')&&!['classic','big_eyes','minimal'].includes(s);
  const b=h('button',{type:'button',role:'radio',class:'tile','aria-checked':String(v.style===s),disabled:off,title:off?T('soon'):null,onclick:async()=>{const ok=await put({style:s});if(ok)gal.forEach(x=>x.setAttribute('aria-checked',String(x===b)))}},h('div',{class:'screen'},tc),S['settings.face.style.'+s]||pretty(s));gal.push(b);gallery.append(b)}
 const sw=swatches(S['settings.face.colour'],c.colour,v.colour,s=>put({colour:s}),true);
 const custom=h('input',{type:'color',value:/^#/.test(v.colour)?v.colour:'#40c0ff','aria-label':S['settings.face.colour']+' (custom)',onchange:async e=>{const ok=await put({colour:e.target.value});if(ok)sw.redraw(e.target.value)}});
 const look=card(S['settings.face.style'],null,gallery);
 const colour=card(S['settings.face.colour'],null,sw,field('',custom));
 const caps=card(S['settings.face.captions'],T('face.captions_help'),toggle(S['settings.face.captions'],null,v.captions,on=>put({captions:on}),!has('captions')),
  seg(S['settings.face.caption_size'],c.caption_size.map(s=>({v:s,t:S['settings.face.caption_size.'+s]})),v.caption_size,s=>put({caption_size:s}),!has('packs')),
  field(S['settings.face.lang'],(()=>{const sel=h('select',{onchange:e=>put({screen_lang:e.target.value})});for(const l of c.lang)sel.append(h('option',{value:l,selected:l===v.lang},S['settings.lang.'+l]||l));return sel})()));
 const hrs=h('div',{class:'hrs'});const hv=v.tod_hours.slice();
 ['morning','day','evening','night'].forEach((b,i)=>{const inp=h('input',{type:'number',min:0,max:23,value:hv[i],'aria-label':T('face.band.'+b),onchange:async()=>{const n=hv.slice();n[i]=parseInt(inp.value,10);const ok=await put({tod_hours:n});if(ok)hv[i]=n[i];else inp.value=hv[i]}});hrs.append(field(T('face.band.'+b),inp))});
 const tod=card(S['settings.face.tod'],T('face.tod_help'),toggle(S['settings.face.tod'],null,v.tod,on=>put({tod:on}),!has('tod')),h('p',{class:'hint'},T('face.hours_help')),hrs);
 const think=
  toggle(T('face.thinking_tone'),null,v.thinking_tone,on=>put({thinking_tone:on}),!has('thinking'));
 const fx=card(h('span',{},T('face.effects'),' ',soonBadge()),T('face.effects_help'),h('div',{class:'pills'},['Scanlines','Glow','Tint'].map(x=>h('button',{class:'pill',disabled:true,type:'button'},x))),h('h3',{},T('face.overlays'),' ',soonBadge()),h('p',{class:'hint'},T('face.overlays_help')));
 const reset=h('button',{class:'btn',type:'button',onclick:async()=>{const r=await save(facePath(id)+'/reset',{});if(r.ok){BUILT.look=false;p.querySelectorAll(':scope>:not(h1)').forEach(n=>n.remove());go('look',true)}}},S['settings.face.reset']);
 const banners=[];if(fv.pending)banners.push(h('div',{class:'banner'},S['settings.face.pending']));if(fv.unavailable&&fv.unavailable.length)banners.push(h('div',{class:'banner'},S['settings.face.unavailable']+' '+fv.unavailable.join(', ')));
 /* screen brightness and light ring */
 const dv=await api(unitPath(id,'overview'));const sv=dv.ok?dv.d.saved:{brightness:100,led:'off'};
 const bright=card(T('look.brightness'),T('look.brightness_help'),slider(T('look.brightness'),10,100,5,sv.brightness,x=>x+'%',null,x=>save(unitPath(id,'device'),{brightness:x}),[ '10%','100%']),
  toggle(T('look.auto'),dv.ok&&dv.d.light!=null?T('home.room_light')+': '+Math.round(dv.d.light)+' lux':null,false,()=>false,true),toggle(T('look.night_dim'),null,false,()=>false,true));
 const ledSw=swatches(T('look.led'),['off','mint','sky','amber','rose','lilac','lime','coral'],/^#/.test(sv.led)?'off':sv.led,async n=>{const hex=n==='off'?'off':PAL[n];return (await save(unitPath(id,'device'),{led:hex})).ok},false);
 ledSw.querySelector('[data-v=off]').classList.add('none');ledSw.querySelector('[data-v=off]').title=T('look.led_off');ledSw.querySelector('[data-v=off]').setAttribute('aria-label',T('look.led_off'));
 const led=card(T('look.led'),T('look.led_help'),ledSw,slider(T('look.led_bright'),10,100,5,100,x=>x+'%',null,null,null,true));
 refresh();
 p.append(h('div',{class:'two'},h('div',{class:'stack sticky'},pv,...banners),h('div',{class:'stack'},look,colour,caps,card(null,null,think),tod,bright,led,fx,card(null,null,reset))));
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
  seg(T('Ignore background noise'),[{v:'low',t:T('Low')},{v:'medium',t:T('Medium')},{v:'high',t:T('High')}],u.ignore_noise||'medium',async m=>(await unitSet(id,{ignore_noise:m})).ok),h('p',{class:'help'},T('Higher ignores more fans and hiss, but may miss quiet speech.')),
  toggle(T('face.thinking_tone'),null,v.thinking_tone,async on=>(await save(facePath(id),{thinking_tone:on})).ok,!has('thinking')));
 const wake=card(T('voice.wake'),T('voice.wake_help'),toggle(T('voice.wake'),null,true,()=>false,true),slider(T('voice.wake_sens'),0,100,5,50,x=>x+'%',null,null,null,true),toggle(T('voice.stop_word'),null,true,()=>false,true));
 const lang=card(S['settings.face.lang'],null,(()=>{const sel=h('select',{'aria-label':S['settings.face.lang'],onchange:e=>save(facePath(id),{screen_lang:e.target.value})});for(const l of (fv.choices?fv.choices.lang:LANGS_ALL))sel.append(h('option',{value:l,selected:l===v.lang},S['settings.lang.'+l]||l));return sel})());
 const quiet=card(h('span',{},T('voice.quiet'),' ',soonBadge()),T('voice.quiet_help'),h('div',{class:'hrs off'},field('',h('input',{type:'time',value:'22:00',disabled:true,'aria-label':T('voice.quiet')})),field('',h('input',{type:'time',value:'07:00',disabled:true,'aria-label':T('voice.quiet')}))));
 p.append(h('div',{class:'grid'},vol,speech,lang,wake,quiet))};

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

/* ---- BEHAVIOUR ---- */
BUILDERS.behaviour=async(p,u)=>{const id=u.device_id,ov=await api(unitPath(id,'overview')),sv=ov.ok?ov.d.saved:{idle_motion:true},pr=ov.ok?ov.d.privacy:null;
 const body=card(T('beh.head'),null,seg(T('Idle movement'),[{v:'off',t:T('Off')},{v:'calm',t:T('Calm')},{v:'lively',t:T('Lively')}],sv.idle_movement||'off',async m=>(await save(unitPath(id,'device'),{idle_movement:m})).ok),h('p',{class:'help'},T('Off keeps the head still until it is spoken to. Calm and lively let it look around when nobody is talking.')),
  toggle(T('Look toward the speaker'),T('Turns or glances toward you when you start talking.'),!!sv.look_speaker,async on=>(await save(unitPath(id,'device'),{look_speaker:on})).ok),
  toggle(T('Look for faces'),T('Searches the room with the camera when something moves. Needs the camera on.'),!!sv.look_faces,async on=>(await save(unitPath(id,'device'),{look_faces:on})).ok),
  toggle(T('beh.sleep'),T('beh.sleep_help'),false,()=>false,true));
 const priv=card(S['settings.ui.nav.privacy'],T('privacy.lead'),toggle(T('beh.vision'),T('beh.vision_help'),pr?pr.vision_off:false,async on=>(await save(unitPath(id,'device'),{vision_off:on})).ok,!pr),
  toggle(T('beh.quiet_mode'),T('beh.quiet_mode_help'),pr?pr.quiet:false,async on=>(await save(unitPath(id,'device'),{quiet:on})).ok,!pr),
  toggle(T('voice.mic_mute'),T('voice.mute_help'),pr?pr.mute:u.muted,async on=>(await save(unitPath(id,'device'),{mute:on})).ok,!pr));
 p.append(h('div',{class:'grid'},body,priv),h('div',{class:'stack',style:'margin-top:18px'},await timeCard(u),await alarmCard(u),await reactCard(u),await peopleCard(u)))};
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
 const one=(person)=>{const p=Object.assign({id:'',name:'',colour:'none',caption_size:'medium',wake_phrase:''},person);
  const name=h('input',{type:'text',value:p.name,maxlength:24}),wake=h('input',{type:'text',value:p.wake_phrase,maxlength:24});
  const sw=swatches(S['settings.people.colour'],d.choices.colour,p.colour,x=>{p.colour=x});
  const sz=seg(S['settings.people.caption'],d.choices.caption_size.map(s=>({v:s,t:S['settings.face.caption_size.'+s]})),p.caption_size,x=>{p.caption_size=x});
  const row=h('div',{class:'item',style:'display:grid;gap:12px'},h('div',{class:'hrs'},field(S['settings.people.name'],name),field(S['settings.people.wake'],wake)),sw,sz,h('div',{class:'btns'},
   h('button',{class:'btn pri',type:'button',onclick:async()=>{const k=await save('/api/stackchan/people',{id:p.id,name:name.value,colour:p.colour,caption_size:p.caption_size,wake_phrase:wake.value});if(k.ok){d=k.d;draw()}}},S['settings.people.save']),
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
 const decor=card(S['settings.extra'],null);let pickd=null;
 const view=window.__faceviews||(window.__faceviews={});
 if(fv.choices){const cv=h('canvas',{width:640,height:480,role:'img','aria-label':T('preview')});const v=fv.values;const face=new Face(cv,{style:v.style,colour:v.colour});
  const pills=h('div',{class:'pills'});for(const n of fv.choices.decorators){const b=h('button',{class:'pill',type:'button','aria-pressed':'false',onclick:async()=>{pills.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));face.set({decor:n});save(unitPath(id,'decorate'),{name:n,seconds:6},true)}},S['settings.decor.'+n]||pretty(n));pills.append(b)}
  decor.append(h('div',{class:'screen'},cv),pills,h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:()=>{pills.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed','false'));face.set({decor:'none'});save(unitPath(id,'decorate'),{name:'none'},true)}},S['settings.extra.stop'])))}
 else decor.append(h('div',{class:'banner'},fv.error||T('net_error')));
 p.append(h('div',{class:'grid'},games,decor))};

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
 const about=card(T('sys.about'),T('sys.source_note'),kv([[S['settings.firmware'],u.firmware_version||S['settings.firmware.unknown']],[T('sys.host_version'),HOSTV],[T('sys.licence'),'GNU AGPL-3.0']]),
  h('div',{class:'list'},h('div',{},lk(T('sys.source'),'https://github.com/getmaipai/stackchan')),h('div',{},lk(T('sys.docs'),'https://github.com/getmaipai/stackchan/tree/main/docs/user'))));
 p.append(h('div',{class:'grid'},unit,det,upd,about,rst,reset))};
"""

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
