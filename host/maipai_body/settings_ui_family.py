# ruff: noqa: E501
"""The parent view on the home page: a Family and safety card (plain status words, the privacy promise, who controlled the robot),
a pairing code button and the phone code. Words come from ``T('fam.*')``, ``T('pair.*')`` and ``T('phone.*')`` (``i18n_family.py``).
The page shows no history because the robot keeps none. Cards that need the host computer say so when the host refuses."""

JS_FAMILY = r"""
/* ---- home: Family and safety, pairing code, phone code ---- */
{const prevHome=BUILDERS.home;BUILDERS.home=async(p,u)=>{await prevHome(p,u);
 const id=u.device_id,ov=await api(unitPath(id,'overview')),o=ov.ok?ov.d:{},lk=await api(unitPath(id,'lock')),L=lk.ok?lk.d:{};
 const word=(on,yes,no)=>on==null?T('fam.unknown'):(on?T(yes):T(no));
 const rows=[[T('fam.l_robot'),u.online?T('fam.online'):T('fam.offline')],
  [T('fam.l_mic'),o.privacy?(o.privacy.mute?T('fam.muted'):T('fam.listening')):T('fam.unknown')],
  [T('fam.l_camera'),o.privacy?(o.privacy.vision_off?T('fam.camera_off'):T('fam.camera_on')):T('fam.unknown')],
  [T('fam.l_lock'),word(L.locked==null?null:!!L.locked,'fam.locked','fam.unlocked')]];
 const stats=h('div',{class:'stats'},...rows.map(r=>h('div',{class:'stat'},h('b',{},r[1]),h('span',{},r[0]))));
 const recent=h('div',{class:'hint'},'...');
 api('/api/stackchan/remote-access').then(r=>{const a=r.ok&&r.d.activity?r.d.activity.slice(0,3):[];recent.replaceChildren(...(a.length?a.map(x=>h('div',{},(x.controller||'')+' · '+(x.action||'')+' · '+(x.result||''))):[T('fam.recent_none')]))});
 const fam=card(T('fam.title'),T('fam.help'),stats,h('p',{class:'hint',role:'note'},T('fam.privacy')),h('p',{class:'hint'},T('fam.no_history')),h('p',{class:'hint'},T('fam.brain_note')),h('b',{},T('fam.recent')),recent);
 const codeBox=h('div',{class:'hint',role:'status','aria-live':'polite'});
 const pair=card(T('pair.title'),T('pair.help'),h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:async()=>{const r=await api('/api/stackchan/pairings/code',{});if(r.ok&&r.d.code){codeBox.replaceChildren(h('div',{style:'font-size:2.2rem;letter-spacing:.3em;font-weight:700;margin:.4rem 0'},r.d.code),h('span',{},T('pair.minutes')))}else{codeBox.textContent=T('pair.error')}}},T('pair.button'))),codeBox);
 const phoneBox=h('div',{class:'hint',role:'status'});
 const phone=card(T('phone.title'),T('phone.help'),h('div',{class:'btns'},h('button',{class:'btn',type:'button',onclick:async()=>{const r=await api('/api/stackchan/phone-link');if(!r.ok){phoneBox.textContent=T('phone.error');return}if(!r.d.enabled){phoneBox.textContent=r.d.note||T('phone.error');return}const holder=h('div',{style:'max-width:260px;background:#fff;padding:8px;border-radius:8px'});holder.innerHTML=r.d.svg;const s=holder.querySelector('svg');if(s){s.setAttribute('role','img');s.setAttribute('aria-label',T('phone.title'));s.style.width='100%';s.style.height='auto'}phoneBox.replaceChildren(holder)}},T('phone.show'))),phoneBox);
 p.prepend(h('div',{class:'grid'},fam,pair,phone))}}

/* the "soon" stubs are not shown: a control that does nothing is hidden until it works */
{const soon=()=>{const w=T('soon');document.querySelectorAll('.row.off,.slide.off,.hrs.off').forEach(e=>{e.hidden=true});
  document.querySelectorAll('[disabled]').forEach(e=>{if((e.title||'')===w||e.querySelector('.badge'))e.hidden=true});
  document.querySelectorAll('.badge').forEach(e=>{if(e.textContent===w&&!e.closest('[hidden]'))e.hidden=true})};
 new MutationObserver(soon).observe(document.body,{childList:true,subtree:true});}

/* documentation screenshots: ?only=words shows just the cards whose title holds those words */
{const only=new URLSearchParams(location.search).get('only');if(only){const q=only.toLowerCase();
 new MutationObserver(()=>document.querySelectorAll('.card').forEach(c=>{const t=((c.querySelector('h3')||{}).textContent||'').toLowerCase();c.style.display=t.includes(q)?'':'none'})).observe(document.body,{childList:true,subtree:true})}}
"""
