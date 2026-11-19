# ruff: noqa: E501
"""The settings page shell (owner request 2026-11-19, docs/plan/settings-simplification.md): five sidebar items, a wide search field on top,
one column of rounded groups, drill-in detail views. Home, Robot and Safety are the reference pages; every older page stays reachable under
More until it is moved. The front pages are budgeted by ``FRONT`` below: ``scripts/dashboard-words-check.py`` fails when a page has too many
controls or words, so the page text lives here, in one place, and the script reads it."""

from __future__ import annotations

import json

from maipai_body.shell_style import CSS as SHELL_CSS, NAV

# Front page text. A page has a title, at most one help sentence of 12 words or fewer, at most 6 controls (labels of 1 to 3 words), and at
# most 60 words in all. "more" lists the controls behind the page's More settings fold (not counted: they are not on the front page).
FRONT: dict[str, dict] = {
    "home": {
        "title": "Home",
        "help": "",
        "controls": ["Wi-Fi", "Look and feel", "Remote control", "Quiet now"],
        "text": ["Get started", "Pair your robot", "Connect to Wi-Fi", "Choose a brain", "Pick a look", "Away from home", "Add a robot", "Online", "Offline", "Battery"],
        "more": [],
    },
    "robot": {
        "title": "Robot",
        "help": "Make it yours.",
        "controls": ["Look and feel", "Volume", "Screen brightness", "Wi-Fi", "Remote control", "Voice and listening"],
        "text": [],
        "more": ["Behavior", "Packs", "Games", "Pictures"],
    },
    "brain": {
        "title": "Brain",
        "help": "Where your robot thinks.",
        "controls": ["Choose a brain", "Test it"],
        "text": ["Using your own model", "Using MaiPai Home", "No brain yet"],
        "more": ["Speech and voice", "Leave hosted"],
    },
    "safety": {
        "title": "Safety",
        "help": "Quiet, privacy and locks.",
        "controls": ["Quiet now", "Quiet hours", "Microphone off", "Camera off", "Lock", "Remote access"],
        "text": [],
        "more": ["Activity log", "Reset"],
    },
    "more": {
        "title": "More",
        "help": "Everything else.",
        "controls": ["Packs", "Games", "Network", "Updates", "About", "System"],
        "text": [],
        "more": ["Advanced"],
    },
}
BANNED = ("psk", "token", "namespace", "firmware", "codec", "jitter", "passphrase", "endpoint", "json")

CSS = (
    SHELL_CSS
    + r"""
:root:root:root{--card:var(--grp);--card2:var(--grp2);--line:var(--sep);--muted:var(--mut);--accent:var(--ac);--on-accent:var(--on-ac);--r:14px}
.bar .pick{flex:none;display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 14px;border:0;border-radius:12px;background:var(--grp);color:var(--fg);font:500 15px/1 var(--font);cursor:pointer;box-shadow:0 0 0 1px var(--sep) inset}
.bar .pick .dot{width:10px;height:10px;border-radius:50%;background:var(--chipc,var(--ac))}
.bar .pick .st{color:var(--mut);font-weight:400}
.bar .menu{position:absolute;right:0;top:54px;min-width:260px;background:var(--grp);border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.28),0 0 0 1px var(--sep);padding:6px;z-index:40}
.bar .menu button{display:flex;align-items:center;gap:10px;width:100%;min-height:44px;padding:0 12px;border:0;border-radius:10px;background:none;color:var(--fg);font:500 16px/1 var(--font);text-align:left;cursor:pointer}
.bar .menu button:hover{background:var(--hover)}
.bar .wrap{position:relative;flex:none}
.lt{font:700 34px/1.1 var(--font);letter-spacing:-.025em;margin:18px 0 6px}
.dt{display:flex;align-items:center;gap:6px;margin:12px 0 0}
.dt .back{display:inline-flex;align-items:center;gap:2px;min-height:44px;padding:0 10px 0 0;border:0;background:none;color:var(--ac);font:500 17px/1 var(--font);cursor:pointer}
.dt .back svg{width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.sub{color:var(--mut);font-size:17px;margin:0 0 20px}
.stl{display:flex;align-items:center;gap:10px;font-size:17px;margin:0 0 4px}
.stl .dotl{width:10px;height:10px;border-radius:50%;background:var(--mut)}.stl.on .dotl{background:var(--ok)}
.grp{margin:0 0 28px}
.gt{font:600 13px/1.2 var(--font);color:var(--mut);text-transform:uppercase;letter-spacing:.04em;margin:0 0 8px 16px}
.rows{background:var(--grp);border-radius:14px;overflow:hidden}
.r{position:relative;display:flex;align-items:center;gap:12px;min-height:52px;padding:8px 16px;width:100%;box-sizing:border-box;border:0;background:none;color:var(--fg);font:400 17px/1.25 var(--font);text-align:left}
.rows>.r+.r,.rows>.rw+.r,.rows>.r+.rw,.rows>.rw+.rw{box-shadow:0 -1px 0 var(--sep)}
.r.go{cursor:pointer;transition:background .15s}.r.go:hover{background:var(--hover)}
.r .ri{width:30px;height:30px;border-radius:8px;background:var(--ac);color:var(--on-ac);display:grid;place-items:center;flex:none}
.r .ri svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.r .rl{flex:1 1 auto;min-width:0;white-space:nowrap}
a.r{text-decoration:none;color:var(--fg)}
.r input.tx{flex:0 1 55%}
.r .rv{color:var(--mut);flex:none}
.r .chev{width:18px;height:18px;stroke:var(--mut);fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;flex:none;opacity:.7}
.r.sl{display:grid;gap:8px;padding:12px 16px}.r.sl .rtop{display:flex;justify-content:space-between;gap:12px}
.r.sl input[type=range]{width:100%;margin:0;accent-color:var(--ac);height:28px}
.r.col2{display:grid;gap:10px;padding:12px 16px}
.rw .rh{padding:0 16px 12px;color:var(--mut);font-size:14px;line-height:1.35}
.info{flex:none;width:24px;height:24px;border-radius:50%;border:0;background:var(--hover);color:var(--mut);font:600 13px/1 var(--font);cursor:pointer}
.sw2{position:relative;flex:none;width:51px;height:31px;border-radius:999px;border:0;background:#78788033;cursor:pointer;transition:background .2s;padding:0}
.sw2::after{content:"";position:absolute;top:2px;left:2px;width:27px;height:27px;border-radius:50%;background:#fff;box-shadow:0 2px 4px rgba(0,0,0,.3);transition:transform .2s}
.sw2[aria-checked=true]{background:var(--ok)}.sw2[aria-checked=true]::after{transform:translateX(20px)}
.sg{display:flex;gap:2px;padding:2px;border-radius:9px;background:var(--hover)}
.sg button{flex:1 1 0;min-height:32px;border:0;border-radius:7px;background:none;color:var(--fg);font:500 14px/1 var(--font);cursor:pointer;padding:0 10px;transition:background .15s}
.sg button[aria-checked=true]{background:var(--pill);box-shadow:0 1px 3px rgba(0,0,0,.25)}
.tiles4{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:0 0 28px}
.big{display:flex;flex-direction:column;align-items:flex-start;gap:14px;min-height:104px;padding:16px;border:0;border-radius:18px;background:var(--grp);color:var(--fg);font:600 17px/1.2 var(--font);text-align:left;cursor:pointer;transition:transform .15s,background .15s}
.big:hover{background:color-mix(in srgb,var(--grp) 92%,var(--ac))}.big:active{transform:scale(.98)}
.big .ri{width:36px;height:36px;border-radius:10px}.big .ri svg{width:20px;height:20px}
.big .ri{background:var(--ac);color:var(--on-ac);display:grid;place-items:center}.big .ri svg{stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.big[aria-pressed=true]{background:var(--ac);color:var(--on-ac)}.big[aria-pressed=true] .ri{background:var(--on-ac);color:var(--ac)}
.meter2{height:8px;border-radius:99px;background:var(--hover);overflow:hidden;width:140px}.meter2 i{display:block;height:100%;background:var(--ok);border-radius:99px;transition:width .3s}
.step{display:flex;align-items:center;gap:12px;min-height:48px;padding:6px 16px}
.step .tick{width:22px;height:22px;border-radius:50%;border:2px solid var(--sep);flex:none;display:grid;place-items:center;font-size:13px;color:var(--on-ac)}
.step.done .tick{background:var(--ok);border-color:var(--ok)}.step.done .rl{color:var(--mut)}
.more{margin:0 0 28px}.more>summary{list-style:none;cursor:pointer;min-height:44px;display:flex;align-items:center;gap:8px;color:var(--ac);font:500 17px/1 var(--font);padding:0 16px}
.more>summary::-webkit-details-marker{display:none}.more[open]>summary{margin-bottom:12px}
.ok2{display:flex;gap:10px;align-items:center;padding:14px 16px;border-radius:14px;background:color-mix(in srgb,var(--ok) 14%,var(--grp));color:var(--fg);margin:0 0 12px}
.next{margin:0 0 28px}
.empty2{padding:28px 16px;text-align:center;color:var(--mut)}
.legacy .panel{display:block;animation:none}.legacy h1.title{display:none}
.legacy .grid,.legacy .two{grid-template-columns:minmax(0,1fr)!important}
.legacy .card{border-radius:14px;box-shadow:none;border:0}
#hits .grp:first-child{margin-top:14px}
.pv2{border-radius:18px;overflow:hidden;background:#000;margin:0 auto 20px;max-width:340px;line-height:0}.pv2 canvas{width:100%;height:auto;aspect-ratio:4/3;display:block}
input.tx{border:0;background:none;color:var(--fg);font:400 17px/1.2 var(--font);text-align:right;min-width:0;flex:1 1 auto;outline:0}
"""
)

JS = r"""
/* ---- the new shell (settings_ui_shell.py) ---- */
const NAV2=__NAV__,FRONT=__FRONT__;
const SVG=(d,cls)=>{const s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('viewBox','0 0 24 24');s.setAttribute('aria-hidden','true');if(cls)s.setAttribute('class',cls);const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',d);s.append(p);return s};
const IC={brain:'M9 4a3 3 0 00-3 3 3 3 0 00-2 5 3 3 0 002 5 3 3 0 003 3h1V4zM15 4a3 3 0 013 3 3 3 0 012 5 3 3 0 01-2 5 3 3 0 01-3 3h-1V4z',chev:'M9 6l6 6-6 6',back:'M15 6l-6 6 6 6',search:'M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-5-5',wifi:'M2 9a15 15 0 0120 0M5 13a10 10 0 0114 0M8.5 16.5a5 5 0 017 0M12 20h.01',face:'M12 3a9 9 0 100 18 9 9 0 000-18zM9 10v2M15 10v2M9 15c1.5 1.4 4.5 1.4 6 0',
 remote:'M12 2v4M12 18v4M2 12h4M18 12h4M12 8l-3 3 3 3 3-3z',moon:'M20 14A8 8 0 0110 4a8 8 0 1010 10z',vol:'M4 9v6h4l5 4V5L8 9zM16 9a4 4 0 010 6',sun:'M12 8a4 4 0 100 8 4 4 0 000-8zM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5',
 mic:'M12 3a3 3 0 013 3v6a3 3 0 01-6 0V6a3 3 0 013-3zM5 11a7 7 0 0014 0M12 18v3',cam:'M3 7h4l2-3h6l2 3h4v13H3zM12 17a4 4 0 100-8 4 4 0 000 8z',lock:'M7 11V8a5 5 0 0110 0v3M6 11h12v9H6z',key:'M15 7a4 4 0 11-3.5 6L4 20.5V17h3v-3h3l1.5-1.5A4 4 0 0115 7z',
 talk:'M4 5h16v11H9l-5 4z',box:'M4 7l8-4 8 4v10l-8 4-8-4zM4 7l8 4 8-4M12 11v10',game:'M6 9h12a3 3 0 013 3v3a3 3 0 01-5 2l-1-1H9l-1 1a3 3 0 01-5-2v-3a3 3 0 013-3zM8 11v3M6.5 12.5h3',info:'M12 3a9 9 0 100 18 9 9 0 000-18zM12 11v5M12 8h.01',gear:'M12 8a4 4 0 100 8 4 4 0 000-8zM3 12h2M19 12h2M12 3v2M12 19v2',plus:'M12 5v14M5 12h14',check:'M5 12l5 5 9-10',people:'M9 11a3 3 0 100-6 3 3 0 000 6zM3 19a6 6 0 0112 0M17 11a3 3 0 100-6M21 19a5 5 0 00-4-5'};
const LEG={home:['home',''],remote:['robot','remote'],look:['robot','look'],voice:['robot','voice'],network:['more','network'],behavior:['more','behavior'],play:['more','games'],system:['more','system'],packs:['more','packs'],security:['safety','lock']};
function nav(page,detail){const t='#'+page+(detail?'/'+detail:'');if(location.hash!==t)location.hash=t;else render()}
function go(g){const m=LEG[g];if(m)nav(m[0],m[1])}
function applyAccent(){document.documentElement.style.removeProperty('--accent');if(UNIT)document.documentElement.style.setProperty('--chipc',accentFor(UNIT))}
function drawChips(){drawPick()}
function loc(){const[a,b]=(location.hash||'#home').slice(1).split('/');return{page:NAV2.some(n=>n[0]===a)?a:'home',detail:b||''}}
/* rows */
function chev(){return SVG(IC.chev,'chev')}
function rowEl(o){const ctl=o.control&&!(o.control instanceof Node)?h('span',{style:'display:flex;gap:8px;align-items:center;flex:1 1 auto;justify-content:flex-end'},...o.control):o.control;o=Object.assign({},o,{control:ctl});const tag=o.go?'button':'div';
 const el=h(tag,{class:'r'+(o.go?' go':''),type:o.go?'button':null,onclick:o.go||null,'aria-label':o.go?o.label:null},
  o.icon?h('span',{class:'ri'},SVG(IC[o.icon]||o.icon)):null,h('span',{class:'rl'},o.label),o.value!=null&&o.value!==''?h('span',{class:'rv'},o.value):null,o.control||null,o.go?chev():null);
 if(!o.help||o.go)return el;const hp=h('div',{class:'rh',hidden:true},o.help);const i=h('button',{type:'button',class:'info','aria-label':T('More about')+' '+o.label,onclick:()=>{hp.hidden=!hp.hidden}},'i');el.insertBefore(i,o.control||null);
 return h('div',{class:'rw'},el,hp)}
function swRow(label,on,fn,o){o=o||{};let v=!!on;const b=h('button',{type:'button',role:'switch',class:'sw2','aria-checked':String(v),'aria-label':label,disabled:!!o.off,onclick:async()=>{const nv=!v;b.setAttribute('aria-checked',String(nv));const ok=await fn(nv);if(ok===false)b.setAttribute('aria-checked',String(v));else v=nv}});
 return rowEl({label,icon:o.icon,control:b,help:o.help})}
function slRow(label,min,max,step,val,fmt,done,o){o=o||{};const out=h('span',{class:'rv'},fmt(val));const inp=h('input',{type:'range',min,max,step,value:val,'aria-label':label,oninput:()=>{out.textContent=fmt(+inp.value)},onchange:()=>done(+inp.value)});
 return h('div',{class:'r sl'},h('div',{class:'rtop'},h('span',{class:'rl'},o.icon?[h('span',{class:'ri',style:'display:inline-grid;margin-right:12px;vertical-align:middle'},SVG(IC[o.icon])),label]:label),out),inp)}
function sgRow(label,items,val,fn){const g=h('div',{class:'sg',role:'radiogroup','aria-label':label});const draw=()=>g.querySelectorAll('button').forEach(b=>b.setAttribute('aria-checked',String(b.dataset.v===String(val))));
 for(const it of items)g.append(h('button',{type:'button',role:'radio','data-v':it.v,onclick:async()=>{const old=val;val=it.v;draw();const ok=await fn(it.v);if(ok===false){val=old;draw()}}},it.t));draw();return h('div',{class:'r col2'},h('span',{class:'rl'},label),g)}
function grp(title,...rows){return h('section',{class:'grp'},title?h('h2',{class:'gt'},title):null,h('div',{class:'rows'},...rows.filter(Boolean)))}
function moreFold(...rows){return h('details',{class:'more'},h('summary',{},T('More settings')),grp(null,...rows))}
function statLine(u,o){const on=!!u.online;return h('p',{class:'stl'+(on?' on':'')},h('span',{class:'dotl'}),u.name+' '+(on?T('is online'):T('is offline')))}
/* data for the rows (one read, shared by the pages and the search) */
const CXD={};
async function cx(force){const id=UNIT.device_id;if(!force&&CXD.id===id&&CXD.t>Date.now()-4000)return CXD;
 const[ov,fv]=await Promise.all([api(unitPath(id,'overview')),faceView(id)]);Object.assign(CXD,{id,t:Date.now(),o:ov.ok?ov.d:{reachable:false},v:fv.values||{},fv});return CXD}
const dev=body=>save(unitPath(UNIT.device_id,'device'),body);
/* the setting list: one entry per setting, used by the pages and by search (plain words and synonyms) */
const SET=[
 {id:'look',page:'robot',label:'Look and feel',words:'face style eyes color theme appearance name picture mood',row:()=>rowEl({label:T('Look and feel'),icon:'face',go:()=>nav('robot','look')})},
 {id:'volume',page:'robot',label:'Volume',words:'sound loud louder quieter speaker audio',row:c=>slRow(T('Volume'),0,100,5,(c.o.saved||{}).volume??70,x=>x+'%',x=>dev({volume:x}),{icon:'vol'})},
 {id:'brightness',page:'robot',label:'Screen brightness',words:'dim bright light display screen',row:c=>slRow(T('Screen brightness'),10,100,5,(c.o.saved||{}).brightness??100,x=>x+'%',x=>dev({brightness:x}),{icon:'sun'})},
 {id:'wifi',page:'robot',label:'Wi-Fi',words:'wifi network internet connect connection offline router',row:()=>rowEl({label:'Wi-Fi',icon:'wifi',go:()=>nav('robot','wifi')})},
 {id:'remote',page:'robot',label:'Remote control',words:'drive move say talk speak look around control browser dance',row:()=>rowEl({label:T('Remote control'),icon:'remote',go:()=>nav('robot','remote')})},
 {id:'voice',page:'robot',label:'Voice and listening',words:'wake word microphone speech speed pitch listen language noise',row:()=>rowEl({label:T('Voice and listening'),icon:'mic',go:()=>nav('robot','voice')})},
 {id:'quietnow',page:'safety',label:'Quiet now',words:'quiet silent sleep mute hush do not disturb',row:c=>swRow(T('Quiet now'),(c.o.saved||{}).quiet_now,async on=>(await dev({quiet_now:on})).ok,{icon:'moon',help:T('Holds until you turn it off. Alarms and timers you set still ring.')})},
 {id:'quiethours',page:'safety',label:'Quiet hours',words:'quiet schedule night sleep bedtime hours do not disturb',row:()=>rowEl({label:T('Quiet hours'),icon:'moon',go:()=>nav('safety','quiet')})},
 {id:'mic',page:'safety',label:'Microphone off',words:'mute microphone mic listening privacy',row:c=>swRow(T('Microphone off'),c.o.privacy?c.o.privacy.mute:UNIT.muted,async on=>(await dev({mute:on})).ok,{icon:'mic',help:T('The robot stops listening, even for its wake word.')})},
 {id:'camera',page:'safety',label:'Camera off',words:'camera vision privacy see watch photo',row:c=>swRow(T('Camera off'),c.o.privacy?c.o.privacy.vision_off:false,async on=>(await dev({vision_off:on})).ok,{icon:'cam',off:!c.o.privacy,help:T('The robot cannot see anything while this is on.')})},
 {id:'lock',page:'safety',label:'Lock',words:'passcode code pin lock screen kids parent',row:()=>rowEl({label:T('Lock'),icon:'lock',go:()=>nav('safety','lock')})},
 {id:'access',page:'safety',label:'Remote access',words:'who can control paired controllers access phone away travel tailscale',row:()=>rowEl({label:T('Remote access'),icon:'key',go:()=>nav('safety','access')})},
 {id:'brain',page:'brain',label:'Choose a brain',words:'model llm ai hosted own server home openai ollama think',row:()=>rowEl({label:T('Choose a brain'),icon:'brain',go:()=>{location.href='/brain'}})},
 {id:'behavior',page:'more',label:'Behavior',words:'head movement idle turn faces sleep timers alarms clock people reactions dance',row:()=>rowEl({label:T('Behavior'),icon:'gear',go:()=>nav('more','behavior')})},
 {id:'packs',page:'more',label:'Packs',words:'languages look packs character pack pictures overlays download',row:()=>rowEl({label:T('Packs'),icon:'box',go:()=>nav('more','packs')})},
 {id:'games',page:'more',label:'Games',words:'game play scores jokes riddles trivia fun',row:()=>rowEl({label:T('Games'),icon:'game',go:()=>nav('more','games')})},
 {id:'network',page:'more',label:'Network',words:'wifi tailscale away travel private address test connection',row:()=>rowEl({label:T('Network'),icon:'wifi',go:()=>nav('more','network')})},
 {id:'update',page:'more',label:'Updates',words:'update upgrade version new release install',row:()=>rowEl({label:T('Updates'),icon:'plus',go:()=>nav('more','system')})},
 {id:'system',page:'more',label:'System',words:'restart reset about version license support details unit name',row:()=>rowEl({label:T('System'),icon:'info',go:()=>nav('more','system')})},
 {id:'name',page:'robot',label:'Robot name',words:'name call rename',row:()=>rowEl({label:T('Robot name'),icon:'face',go:()=>nav('robot','look')})},
];
/* search: a wide field on top; results are the settings themselves */
let SQ='';
function score(e,q){const l=e.label.toLowerCase(),w=(l+' '+e.words+' '+e.page).toLowerCase();let s=0;for(const t of q.split(/\s+/).filter(Boolean)){if(l.startsWith(t))s+=4;else if(l.includes(t))s+=3;else if(w.split(/\s+/).some(x=>x.startsWith(t)))s+=2;else if(w.includes(t))s+=1;else return 0}return s}
async function showHits(q){SQ=q;const view=$('#view'),hits=$('#hits');if(q.length<2){hits.hidden=true;view.hidden=false;hits.replaceChildren();return}
 const found=SET.map(e=>[score(e,q.toLowerCase()),e]).filter(x=>x[0]>0).sort((a,b)=>b[0]-a[0]).slice(0,8).map(x=>x[1]);
 view.hidden=true;hits.hidden=false;hits.replaceChildren();if(UNIT){const c=await cx();if(q!==SQ)return;
  if(!found.length)hits.append(h('p',{class:'empty2'},T('No setting matches that')));
  else{const live=found.map(e=>e.row(c));hits.append(grp(T('Settings'),...live))}}}
/* chrome: sidebar, bar, picker */
function drawPick(){const b=$('#pick');if(!b)return;b.replaceChildren();if(!UNIT){b.append(h('span',{},T('Add a robot')));return}
 b.append(h('span',{class:'dot'}),h('span',{},UNIT.name),h('span',{class:'st'},UNIT.online?T('Online'):T('Offline')))}
function pickMenu(){const m=$('#menu');if(!m.hidden){m.hidden=true;return}m.replaceChildren();for(const u of UNITS)m.append(h('button',{type:'button',style:'--chipc:'+accentFor(u),onclick:()=>{m.hidden=true;pick(u.device_id)}},h('span',{class:'dot',style:'width:10px;height:10px;border-radius:50%;background:var(--chipc)'}),u.name,h('span',{style:'margin-left:auto;color:var(--mut);font-weight:400;font-size:14px'},u.online?T('Online'):T('Offline'))));
 m.append(h('button',{type:'button',onclick:()=>{m.hidden=true;nav('robot','pair')}},SVG(IC.plus),T('Add a robot')));m.hidden=false}
function pick(id){UNIT=UNITS.find(u=>u.device_id===id)||UNITS[0];try{sessionStorage.setItem('unit',UNIT.device_id)}catch(e){}applyAccent();drawPick();BUILT={};BUILDP={};FIND=null;for(const g of GROUPS){const p=panels[g];if(p)p.querySelectorAll(':scope>:not(h1)').forEach(n=>n.remove())}CXD.id='';render()}
function shell(){document.body.classList.add('a2');
 const side=h('nav',{class:'side','aria-label':T('Sections')},h('a',{class:'brand',href:'#home'},h('img',{class:'lt',src:'/assets/brand/maipai-bot-icon-light.png',alt:'',width:30,height:30}),h('img',{class:'dk',src:'/assets/brand/maipai-bot-icon-dark.png',alt:'',width:30,height:30}),'MaiPai for StackChan'),
  h('div',{class:'nv'},NAV2.map(n=>h('a',{href:n[2],'data-nav':n[0],onclick:e=>{if(n[2].startsWith('/settings#')){e.preventDefault();nav(n[0],'')}}},SVG(n[3]),T(n[1])))),
  h('div',{class:'foot'},T('Support this project: '),h('a',{href:'https://github.com/sponsors/JesseWebDotCom',target:'_blank',rel:'noopener noreferrer'},'GitHub Sponsors'),'.'));
 const input=h('input',{type:'search',id:'q',name:'q','aria-label':T('Search settings'),placeholder:T('Search settings'),autocomplete:'off',oninput:e=>showHits(e.target.value.trim()),onkeydown:e=>{if(e.key==='Escape'){e.target.value='';showHits('')}}});
 const find=h('div',{class:'find',role:'search'},SVG(IC.search),input);
 const bar=h('div',{class:'bar'},find,h('div',{class:'wrap'},h('button',{type:'button',class:'pick',id:'pick','aria-haspopup':'true',onclick:pickMenu}),h('div',{class:'menu',id:'menu',hidden:true})));
 const bottom=h('nav',{class:'bottom','aria-label':T('Sections')},NAV2.map(n=>h('a',{href:n[2],'data-nav':n[0],onclick:e=>{if(n[2].startsWith('/settings#')){e.preventDefault();nav(n[0],'')}}},SVG(n[3]),T(n[1]))));
 const pane=h('main',{class:'pane',id:'main'},h('div',{class:'col'},bar,h('div',{id:'hits',hidden:true}),h('div',{id:'view'}),h('div',{class:'foot2'},T('Support this project: '),h('a',{href:'https://github.com/sponsors/JesseWebDotCom',target:'_blank',rel:'noopener noreferrer'},'GitHub Sponsors'),'.'),h('div',{id:'toasts',class:'toasts',role:'status','aria-live':'polite'})));
 document.body.append(h('a',{class:'skip',href:'#main'},T('skip')),h('div',{class:'app'},side,pane),bottom,h('div',{id:'store',hidden:true}));
 document.addEventListener('click',e=>{if(!e.target.closest('.wrap'))$('#menu').hidden=true});
 for(const g of GROUPS){const p=h('section',{class:'panel on',id:'p-'+g},h('h1',{class:'title'},S['settings.ui.'+NAMEKEY[g]]));panels[g]=p;$('#store').append(p)}
 const q=new URLSearchParams(location.search).get('q');if(q){input.value=q;setTimeout(()=>showHits(q.trim()),400)}}
function setNav(page){document.querySelectorAll('[data-nav]').forEach(a=>{if(a.dataset.nav===page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')})}
/* pages */
const add=(el,...a)=>el.append(...a.flat(9).filter(x=>x!=null&&x!==false));
const lt=(t,sub)=>[h('h1',{class:'lt'},t),sub?h('p',{class:'sub'},sub):null];
function detailHead(title,page){return[h('div',{class:'dt'},h('button',{type:'button',class:'back',onclick:()=>nav(page,'')},SVG(IC.back),T(FRONT[page].title))),h('h1',{class:'lt'},title)]}
function need(){return h('div',{class:'rows'},h('p',{class:'empty2'},T('Add your first robot to begin.')),h('div',{class:'r go',onclick:()=>nav('robot','pair')},h('span',{class:'rl'},T('Pair your robot')),chev()))}
const PAGE2={
 async home(v){const f=FRONT.home;if(!UNIT){add(v,...lt(f.title),need());return}const c=await cx();const o=c.o;
  const bat=o.battery?o.battery.percent:null;
  const tvh=await api(unitPath(UNIT.device_id,'travel'));const awayOn=!!(tvh.ok&&tvh.d&&tvh.d.available);const done={pair:true,wifi:UNIT.wifi==='set'||!!UNIT.online,brain:!!BRAINSET,look:LOOKED(),away:!awayOn||!!tvh.d.ready_to_use};const left=['pair','wifi','brain','look'].filter(k=>!done[k]);
  add(v,...lt(UNIT.name),statLine(UNIT),bat!=null?h('div',{class:'stl'},h('div',{class:'meter2','aria-hidden':'true'},h('i',{style:'width:'+bat+'%'})),T('Battery')+' '+bat+'%'+(o.battery.charging?' ⚡':'')):null,h('div',{style:'height:20px'}));
  if(left.length){const steps=[['pair','Pair your robot',null],['wifi','Connect to Wi-Fi',()=>nav('robot','wifi')],['brain','Choose a brain',()=>{location.href='/brain'}],['look','Pick a look',()=>nav('robot','look')],['away','Away from home',()=>nav('more','network-away'),true]];
   add(v,grp(T('Get started'),...steps.map(([k,t,fn,opt])=>h(fn&&!done[k]?'button':'div',{class:'step'+(done[k]?' done':'')+(fn&&!done[k]?' go r':''),onclick:fn&&!done[k]?fn:null},h('span',{class:'tick'},done[k]?SVG(IC.check):null),h('span',{class:'rl'},T(t)+(opt?' ('+T('Optional').toLowerCase()+')':'')),fn&&!done[k]?chev():null))))}
  const big=(ic,l,fn,pressed)=>h('button',{type:'button',class:'big','aria-pressed':pressed?'true':null,onclick:fn},h('span',{class:'ri'},SVG(IC[ic])),T(l));
  const q=!!(o.saved||{}).quiet_now;
  const qb=big('moon','Quiet now',async()=>{const r=await dev({quiet_now:!(CXD.o.saved||{}).quiet_now});if(r.ok){CXD.o.saved=Object.assign({},CXD.o.saved,{quiet_now:!(CXD.o.saved||{}).quiet_now});qb.setAttribute('aria-pressed',String(!!CXD.o.saved.quiet_now))}},q);
  add(v,h('div',{class:'tiles4'},big('wifi','Wi-Fi',()=>nav('robot','wifi')),big('face','Look and feel',()=>nav('robot','look')),big('remote','Remote control',()=>nav('robot','remote')),qb))},
 async robot(v){const f=FRONT.robot;add(v,...lt(f.title,f.help));if(!UNIT){add(v,need());return}const c=await cx();
  add(v,grp(null,...['look','volume','brightness','wifi','remote','voice'].map(i=>SET.find(s=>s.id===i).row(c))),moreFold(...['behavior','packs','games'].map(i=>SET.find(s=>s.id===i).row(c))))},
 async brain(v){const f=FRONT.brain;add(v,...lt(f.title,f.help));const r=await api('/api/stackchan/brain');const d=r.ok?r.d:{};const names={none:T('No brain yet'),home:T('Using MaiPai Home'),own:T('Using your own model'),local:T('Using your own model')};BRAINSET=d.mode&&d.mode!=='none';
  add(v,grp(null,rowEl({label:names[d.mode]||names.none,icon:'brain'}),rowEl({label:T('Choose a brain'),icon:'gear',go:()=>{location.href='/brain'}})))},
 async safety(v){const f=FRONT.safety;add(v,...lt(f.title,f.help));if(!UNIT){add(v,need());return}const c=await cx();
  add(v,grp(null,...['quietnow','quiethours','mic','camera','lock','access'].map(i=>SET.find(s=>s.id===i).row(c))))},
 async more(v){const f=FRONT.more;add(v,...lt(f.title,f.help));const c=UNIT?await cx():{o:{}};
  add(v,grp(null,...['packs','games','network','update','about','system'].map(i=>i==='about'?rowEl({label:T('About'),icon:'info',go:()=>{location.href='/about'}}):SET.find(s=>s.id===i).row(c))),
   grp(null,rowEl({label:T('Status'),icon:'check',go:()=>{location.href='/health'}}),rowEl({label:T('On my robot'),icon:'box',go:()=>{location.href='/on-my-robot'}})))}
};
let BRAINSET=null;
function LOOKED(){try{return localStorage.getItem('looked.'+UNIT.device_id)==='1'}catch(e){return false}}
/* detail views */
function legacyView(g,title,page){return async v=>{add(v,...detailHead(title,page));const p=panels[g];const box=h('div',{class:'legacy'});add(v,box);box.append(p);
  if(!BUILT[g]&&UNIT){BUILT[g]=true;BUILDP[g]=Promise.resolve(BUILDERS[g](p,UNIT)).then(()=>layoutPanel(g)).catch(e=>{toast(T('net_error'),'bad');console.error(e)})}await BUILDP[g]}}
const DETAIL={
 'robot/look':async v=>{add(v,...detailHead(T('Look and feel'),'robot'));const c=await cx();const fv=c.fv;if(!fv.values){add(v,h('p',{class:'empty2'},fv.error||T('net_error')));return}
  try{localStorage.setItem('looked.'+UNIT.device_id,'1')}catch(e){}
  let val=Object.assign({},fv.values);const ch=fv.choices;
  const cv=h('canvas',{width:640,height:480,role:'img','aria-label':T('preview')});const face=new Face(cv,{style:val.style,color:val.color,background:val.background,tint:val.emotion_tint,captions:val.captions,size:val.caption_size,lang:val.lang});
  const put=async patch=>{const old=Object.assign({},val);Object.assign(val,patch);face.set({style:val.style,color:val.color,background:val.background});const r=await save(facePath(UNIT.device_id),patch);if(!r.ok){val=old;face.set({style:val.style,color:val.color});return false}if(patch.color){UNIT.color=patch.color;applyAccent();drawPick()}return true};
  const sel=h('select',{'aria-label':T('Face style'),style:'border:0;background:none;color:var(--fg);font:inherit;text-align:right;max-width:60%',onchange:async e=>{const ok=await put({style:e.target.value});if(!ok)e.target.value=val.style}});for(const s of ch.style)sel.append(h('option',{value:s,selected:s===val.style},S['settings.face.style.'+s]||pretty(s)));
  const nm=h('input',{class:'tx',type:'text',value:UNIT.name,maxlength:40,'aria-label':T('Robot name'),onchange:async e=>{const r=await unitSet(UNIT.device_id,{name:e.target.value});if(r.ok){UNIT.name=e.target.value;drawPick()}}});
  const sw=swatches(S['settings.face.color'],ch.color,val.color,s=>put({color:s}),true);
  add(v,h('div',{class:'pv2'},cv),grp(null,rowEl({label:T('Face style'),control:sel}),h('div',{class:'r col2'},h('span',{class:'rl'},T('Eye color')),sw),rowEl({label:T('Robot name'),control:nm})),
   h('div',{class:'ok2'},SVG(IC.check),T('Changes show on the robot at once.')),moreFold(rowEl({label:T('Every look setting'),go:()=>nav('robot','looks')})))},
 'robot/looks':legacyView('look',T('Every look setting'),'robot'),
 'robot/voice':legacyView('voice',T('Voice and listening'),'robot'),
 'robot/remote':legacyView('remote',T('Remote control'),'robot'),
 'robot/wifi':async v=>{add(v,...detailHead('Wi-Fi','robot'));const c=await cx();const nt=await api(unitPath(UNIT.device_id,'network-test'),{});const steps=nt.ok&&nt.d.steps?nt.d.steps:[];const wl=steps.find(s=>/wifi/i.test(s.step||''));
  const ok=UNIT.wifi==='set'||UNIT.online;
  add(v,ok?h('div',{class:'ok2'},SVG(IC.check),T('Connected to Wi-Fi')+(wl?': '+wl.line.replace(/^Wi-Fi:\s*/i,''):'')):h('div',{class:'ok2',style:'background:color-mix(in srgb,var(--warn) 16%,var(--grp))'},T('Not connected yet')),
   grp(null,rowEl({label:T('Status'),value:S['settings.wifi.'+UNIT.wifi]||''}),rowEl({label:T('Run a check'),icon:'wifi',go:async()=>{toast(T('Checking')+'...');const r=await api(unitPath(UNIT.device_id,'network-test'),{});toast((r.d.summary||r.d.error||'').toString())}})),
   h('p',{class:'sub'},T('Join a new network on the robot: open its Wi-Fi settings and pick your network.')),
   h('div',{class:'next'},grp(T('Next'),rowEl({label:T('Choose a brain'),icon:'brain',go:()=>{location.href='/brain'}}))))},
 'robot/pair':async v=>{add(v,...detailHead(T('Pair your robot'),'robot'),h('p',{class:'sub'},T('pair.help')));
  const code=h('div',{class:'ok2',hidden:true,style:'font-size:34px;letter-spacing:.3em;font-weight:700;justify-content:center'}),wait=h('div');
  add(v,grp(null,rowEl({label:T('pair.button'),icon:'plus',go:async()=>{const r=await api('/api/stackchan/pairings/code',{});if(r.ok&&r.d.code){code.textContent=r.d.code;code.hidden=false;toast(T('pair.minutes'))}else toast(T('pair.error'),'bad')}})),code,wait);
  const shown=new Set();const poll=async()=>{const r=await api('/api/stackchan/pairings/waiting');const w=r.ok&&r.d.waiting?r.d.waiting:[];
   if(w.join()!==[...shown].join()){shown.clear();w.forEach(d=>shown.add(d));wait.replaceChildren(...(w.length?[grp(T('pair.waiting'),...w.map(d=>{const inp=h('input',{class:'tx',type:'text',inputmode:'numeric',maxlength:6,autocomplete:'one-time-code',placeholder:'000000','aria-label':T('pair.waiting')+' '+d});
     return rowEl({label:d,control:[inp,h('button',{class:'info',style:'width:auto;padding:0 12px;height:30px;color:var(--ac)',type:'button',onclick:async()=>{const x=await api('/api/stackchan/pairings/code-entry',{device_id:d,code:inp.value});toast(x.ok?T('pair.paired'):(x.d.error||T('pair.error')),x.ok?'':'bad');if(x.ok){location.hash='#home';location.reload()}}},T('pair.approve'))]})}))]:[]))}
   if(document.body.contains(wait)&&loc().detail==='pair')setTimeout(poll,2000)};poll()},
 'safety/lock':legacyView('security',T('Lock'),'safety'),
 'safety/quiet':async v=>{add(v,...detailHead(T('Quiet hours'),'safety'));const c=await cx();const sv=c.o.saved||{};const q=Object.assign({enabled:false,from:'22:00',to:'07:00',days:[0,1,2,3,4,5,6]},sv.quiet_schedule||{});
  const persist=async()=>(await dev({quiet_schedule:q})).ok;const dn=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const tm=k=>h('input',{type:'time',value:q[k],style:'border:0;background:none;color:var(--fg);font:inherit',onchange:e=>{q[k]=e.target.value||q[k];persist()}});
  const days=h('div',{class:'sg',role:'group'});dn.forEach((n,i)=>days.append(h('button',{type:'button','aria-checked':String(q.days.includes(i)),onclick:e=>{const on=!q.days.includes(i);q.days=on?[...q.days,i].sort():q.days.filter(d=>d!==i);e.currentTarget.setAttribute('aria-checked',String(on));persist()}},T(n))));
  add(v,grp(null,swRow(T('Quiet on a schedule'),q.enabled,async on=>{q.enabled=on;return persist()},{icon:'moon',help:T('Sounds stay quiet in these hours. Alarms and timers still ring.')}),rowEl({label:T('From'),control:tm('from')}),rowEl({label:T('To'),control:tm('to')}),h('div',{class:'r col2'},h('span',{class:'rl'},T('Days')),days)))},
 'safety/access':legacyView('remote',T('Remote access'),'safety'),
 'more/behavior':legacyView('behavior',T('Behavior'),'more'),
 'more/packs':legacyView('packs',T('Packs'),'more'),
 'more/games':legacyView('play',T('Games'),'more'),
 'more/network':legacyView('network',T('Network'),'more'),
 'more/system':legacyView('system',T('System'),'more'),
};
function legacyHolder(g){return h('div',{})}
async function render(){const{page,detail}=loc();setNav(page);const v=$('#view');if(!v)return;
 for(const g of GROUPS){const p=panels[g];if(p&&p.parentElement!==$('#store'))$('#store').append(p)}
 v.replaceChildren();document.body.classList.toggle('detail',!!detail);
 const def=detail?DETAIL[page+'/'+detail]:PAGE2[page];window.scrollTo({top:0});
 try{if(!def)nav(page,'');else await def(v)}catch(e){console.error(e);add(v,h('p',{class:'empty2'},T('net_error')))}}
async function main(){shell();const r=await api('/api/stackchan/settings');
 if(!r.ok){toast(r.d.error||T('net_error'),'bad');return}
 UNITS=r.d.units;HOST=r.d.host_address;HOSTV=r.d.host_version||'';
 let keep=null;try{keep=sessionStorage.getItem('unit')}catch(e){}
 UNIT=UNITS.find(u=>u.device_id===keep)||UNITS.find(u=>u.device_id===r.d.default_unit)||UNITS[0]||null;
 applyAccent();drawPick();addEventListener('hashchange',render);render()}
"""


def css() -> str:
    return CSS


def page_modules() -> list[str]:
    """The JavaScript of every moved page: each ``settings_ui_p_<name>.py`` next to this file holds a ``JS`` string that sets ``DETAIL['<page>/<name>']``
    with the kit above. Found by file name, so moving a page never edits a shared file."""
    import importlib
    import pkgutil
    from pathlib import Path

    out = []
    for info in sorted(pkgutil.iter_modules([str(Path(__file__).parent)]), key=lambda m: m.name):
        if info.name.startswith("settings_ui_p_"):
            out.append(importlib.import_module(f"maipai_body.{info.name}").JS)
    return out


def js() -> str:
    return JS.replace("__NAV__", json.dumps([list(n) for n in NAV])).replace("__FRONT__", json.dumps(FRONT)) + "\n".join(page_modules())
