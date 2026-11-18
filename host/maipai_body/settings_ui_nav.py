# ruff: noqa: E501
"""Long dashboard pages get an inner tab row, rarely used cards sit behind an Advanced fold, and a search box at the top jumps to a setting.

Short pages (eight cards or fewer) stay as they are. The groups are written with the English card titles; ``card_map`` turns them into the
titles of the page's language, so the same grouping works in all six languages. The tab row scrolls sideways on a phone, the page never does."""

from __future__ import annotations

# page -> tabs (label, English card titles in it) and the cards kept behind the Advanced fold (decision 20: offer a choice only when it is needed).
SUBTABS: dict[str, dict] = {
    "look": {
        "tabs": [
            ("Face", ["Live preview", "Face style", "Top bar", "Eye color", "Screen color", "Captions", "Show captions on the screen", "Change the face with the time of day"]),
            ("Screen and light", ["Screen effects", "Screen brightness", "Light ring", "Overlays"]),
            ("Packs and pictures", ["Look packs", "Picture face", "Character pack"]),
        ],
        "adv": ["Emotion colors", "Feelings and words", "Scenes"],
    },
    "behavior": {
        "tabs": [
            ("Movement", ["Head movement", "Turning toward people", "Dance to music"]),
            ("Sleep and quiet", ["Privacy", "Quiet hours", "Clock and time zone", "Timers", "Alarms"]),
            ("Reactions and people", ["Word reactions", "People"]),
        ],
        "adv": ["Swipe pages"],  # the page layout of the robot: set once, rarely changed
    },
    "remote": {
        "tabs": [
            ("Actions", ["Quick actions", "Say something", "Head pad", "Dance", "Start a game", "Overlays", "Take a picture"]),
            ("Access and log", ["Remote access", "Paired controllers", "Remote activity"]),
        ],
        "adv": [],
    },
}
# Pages with few cards keep no tab row, but their rarely used cards still sit behind the fold.
ADVANCED_ONLY: dict[str, list[str]] = {
    "voice": ["Make your own wake word"],
    "system": ["Unit details", "Restart the unit", "Reset the unit"],
}
LABELS = ["Advanced", "Search settings", "No setting matches that", "Face", "Screen and light", "Packs and pictures", "Movement", "Sleep and quiet", "Swipe pages", "Reactions and people", "Actions", "Access and log"]


def card_map(catalog: dict[str, str]) -> dict:
    """{page: {"tabs": [labels], "of": {card title: tab index}, "adv": [card titles]}} with every title in the page's language."""
    en_values: dict[str, str] = {}
    from maipai_body.i18n import CATALOG

    for key, text in CATALOG["en"].items():
        en_values.setdefault(text, key)

    def local(title: str) -> str:
        if title in catalog:
            return catalog[title]  # a literal: its English text is its key
        key = en_values.get(title)
        return catalog.get(key, title) if key else title

    out: dict = {}
    for page, spec in SUBTABS.items():
        of = {local(title): i for i, (_, titles) in enumerate(spec["tabs"]) for title in titles}
        out[page] = {"tabs": [local(label) for label, _ in spec["tabs"]], "of": of, "adv": [local(t) for t in spec["adv"]]}
    for page, titles in ADVANCED_ONLY.items():
        out[page] = {"tabs": [], "of": {}, "adv": [local(t) for t in titles]}
    return out


CSS = """
.subtabs{display:flex;gap:8px;overflow-x:auto;white-space:nowrap;max-width:100%;margin:0 0 16px;padding-bottom:4px;-webkit-overflow-scrolling:touch}
.subtabs button{flex:none;min-height:44px;padding:0 16px;border-radius:999px;border:1.5px solid var(--line);background:var(--card2);color:var(--fg);font:inherit;font-weight:600;cursor:pointer}
.subtabs button[aria-selected=true]{background:var(--accent);border-color:var(--accent);color:#fff}
.subtabs button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.card[hidden]{display:none}
details.adv{margin:18px 0 0;border:1px solid var(--line);border-radius:16px;background:var(--card2);padding:0 14px}
details.adv>summary{min-height:48px;display:flex;align-items:center;font-weight:600;cursor:pointer}
details.adv>.advbody{display:grid;gap:14px;padding:0 0 14px}
.find{position:relative;flex:1 1 220px;max-width:340px;min-width:0}
.find input{width:100%;box-sizing:border-box;min-height:44px;border-radius:999px;border:1.5px solid var(--line);background:var(--card);color:var(--fg);font:inherit;padding:0 16px}
.find .hits{position:absolute;left:0;right:0;top:48px;z-index:20;background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.25);max-height:60vh;overflow-y:auto}
.find .hits button{display:block;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--line);color:var(--fg);font:inherit;padding:10px 14px;cursor:pointer;min-height:48px}
.find .hits button:last-child{border-bottom:0}.find .hits small{display:block;color:var(--muted)}
.find .hits .none{padding:12px 14px;color:var(--muted)}
.flash{animation:flash 1.6s ease-out}@keyframes flash{0%{box-shadow:0 0 0 4px var(--accent)}100%{box-shadow:0 0 0 0 transparent}}
.row.pack{flex-wrap:wrap;padding:8px 0;border-bottom:1px solid var(--line)}.row.pack:last-of-type{border-bottom:0}.row.pack .lbl{flex:1 1 100%}.row.pack .lbl b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.row.pack .btns{flex:none;flex-wrap:nowrap;margin-left:auto}
"""

JS = r"""
/* Inner tabs for long pages, the Advanced fold and the search box (settings_ui_nav.py). */
const NAV=__CARDMAP__;
const SUBSEL={};
function titleOf(card){const h=card.querySelector(':scope>h3')||card.querySelector('h3');return h?h.textContent:''}
function layoutPanel(g){const spec=NAV[g],p=panels[g];if(!spec||p.querySelector(':scope>.subtabs,:scope>details.adv'))return;
 const cards=[...p.querySelectorAll('section.card')].filter(c=>!c.parentElement.closest('section.card'));if(!cards.length)return;
  let last=0;const own=new Map();
 for(const c of cards){if(spec.adv.includes(titleOf(c)))continue;const t=titleOf(c);let i=spec.of[t];if(i===undefined)i=last;else last=i;own.set(c,i)}
 const adv=[...p.querySelectorAll('section.card')].filter(c=>spec.adv.includes(titleOf(c)));
 if(adv.length){const box=h('div',{class:'advbody'});const det=h('details',{class:'adv'},h('summary',{},T('Advanced')),box);adv.forEach(c=>{c.dataset.adv='1';box.append(c)});p.append(det);p.querySelectorAll('.adv').forEach(d=>d.dataset.advbox='1')}
 if(spec.tabs.length>1&&cards.length>8){
  const row=h('div',{class:'subtabs',role:'tablist','aria-label':p.querySelector('h1').textContent});
  const show=i=>{SUBSEL[g]=i;row.querySelectorAll('button').forEach((b,k)=>b.setAttribute('aria-selected',String(k===i)));for(const c of cards){if(c.dataset.adv||!own.has(c))continue;c.hidden=own.get(c)!==i}};
  spec.tabs.forEach((label,i)=>row.append(h('button',{type:'button',role:'tab','aria-selected':'false',onclick:()=>show(i)},label)));
  p.querySelector('h1').after(row);p._showSub=show;p._ownTab=own;show(SUBSEL[g]||0)}}
async function buildAll(){for(const g of GROUPS){if(!BUILT[g]&&UNIT){BUILT[g]=true;BUILDP[g]=Promise.resolve(BUILDERS[g](panels[g],UNIT)).then(()=>layoutPanel(g)).catch(e=>console.error(e))}if(BUILDP[g])await BUILDP[g]}}
let FIND=null;
async function searchIndex(){if(FIND)return FIND;await buildAll();const out=[];
 for(const g of GROUPS){const p=panels[g],page=p.querySelector('h1').textContent;
  for(const el of p.querySelectorAll('section.card h3,.row .lbl>b,label.f,.item b')){const text=(el.childNodes[0]&&el.childNodes[0].textContent||el.textContent||'').trim();if(!text||text.length>80)continue;
   const help=el.closest('.row')&&el.closest('.row').querySelector('.lbl span');out.push({g,page,text,help:help?help.textContent:'',el,key:(text+' '+(help?help.textContent:'')).toLowerCase()})}}
 FIND=out;return out}
function jumpTo(hit){go(hit.g);const p=panels[hit.g];const card=hit.el.closest('section.card');
 if(card&&card.dataset.adv){const d=card.closest('details');if(d)d.open=true}
 else if(card&&p._ownTab&&p._showSub){p._showSub(p._ownTab.get(card)||0)}
 setTimeout(()=>{(card||hit.el).scrollIntoView({block:'center',behavior:'smooth'});const t=hit.el.closest('.row')||card||hit.el;t.classList.add('flash');setTimeout(()=>t.classList.remove('flash'),1700)},60)}
function searchBox(){const input=h('input',{type:'search','aria-label':T('Search settings'),placeholder:T('Search settings'),autocomplete:'off'}),hits=h('div',{class:'hits',hidden:true,role:'listbox'});
 const close=()=>{hits.hidden=true};
 input.addEventListener('input',async()=>{const q=input.value.trim().toLowerCase();if(q.length<2){close();return}const idx=await searchIndex();
  const found=idx.filter(x=>x.key.includes(q)).slice(0,12);hits.replaceChildren();
  if(!found.length)hits.append(h('div',{class:'none'},T('No setting matches that')));
  for(const x of found)hits.append(h('button',{type:'button',role:'option',onclick:()=>{close();input.value='';jumpTo(x)}},x.text,h('small',{},x.page+(x.help?' · '+x.help:''))));
  hits.hidden=false});
 input.addEventListener('keydown',e=>{if(e.key==='Escape'){close();input.blur()}});
 document.addEventListener('click',e=>{if(!e.target.closest('.find'))close()});
 return h('div',{class:'find'},input,hits)}
"""
