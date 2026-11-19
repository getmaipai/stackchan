# ruff: noqa: E501
"""The Remote control page and the Remote access page in the new dashboard look (api32, owner request 2026-11-19).

Replaces ``DETAIL['robot/remote']`` and ``DETAIL['safety/access']`` and adds four second-level views:
``robot/remote-head``, ``robot/remote-overlays``, ``safety/controllers`` and ``safety/activity``.
It makes the same calls the old builder made (``BUILDERS.remote``, ``quickActions`` and ``accessCards`` in ``settings_ui.py``):
GET and POST ``/api/stackchan/unit/<id>/remote`` and GET and POST ``/api/stackchan/remote-access[/allow|/revoke]``.
Every name lives inside one block so it cannot clash with the shell or another page file."""

JS = r"""
/* ---- Remote control and Remote access (settings_ui_p_remote.py) ---- */
{
const RC=async(id,body)=>{const r=await remote(id,body);if(r.ok)toast(r.d.pending?r.d.message:(r.d.message||T('rem.done')),r.d.pending?'warn':'');return r};
const RCDATA=async id=>{const r=await api(unitPath(id,'remote'));return r.ok?r.d:{reachable:false,dances:[],games:[],limits:{yaw:128,pitch:[5,85]}}};
const offBanner=why=>h('div',{class:'ok2',style:'background:color-mix(in srgb,var(--warn) 16%,var(--grp))'},why);
const ricon=n=>h('span',{class:'ri'},SVG(IC[n]||n));
const IRC={talk:IC.talk,find:'M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-5-5',photo:'M4 8h3l2-3h6l2 3h3v11H4zM12 11a3.5 3.5 0 100 7 3.5 3.5 0 000-7z',dance:'M9 18V5l12-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0zM21 16a3 3 0 11-6 0 3 3 0 016 0z',look:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 100 6 3 3 0 000-6z',beep:'M11 5L6 9H3v6h3l5 4zM15.5 8.5a5 5 0 010 7M18.5 6a9 9 0 010 12',flash:'M13 2L4 14h7l-1 8 9-12h-7z',stop:'M6 6h12v12H6z',head:'M12 3v14M6 11l6 6 6-6',layers:'M12 3l9 5-9 5-9-5zM3 13l9 5 9-5'};
const aicon=n=>IRC[n]||IC[n]||n;
/* a row that does one thing when pressed: busy while it runs, dimmed when the robot is away */
const actRow=(icon,label,fn,off,value)=>{const val=h('span',{class:'rv'},value||'');const b=h('button',{type:'button',class:'r go',disabled:!!off,onclick:async()=>{if(b.disabled)return;b.disabled=true;b.setAttribute('aria-busy','true');try{await fn(b,val)}finally{b.disabled=!!off;b.removeAttribute('aria-busy')}}},h('span',{class:'ri'},SVG(aicon(icon))),h('span',{class:'rl'},label),val);if(off)b.style.opacity='.5';return b};
const subHead=(title,backTo,page)=>{const hd=detailHead(title,page);const bk=hd[0].querySelector('.back');if(bk){const nb=bk.cloneNode(true);nb.lastChild.textContent=T(backTo==='remote'?'Remote control':'Remote access');nb.addEventListener('click',()=>nav(page,backTo));bk.replaceWith(nb)}return hd};
const selStyle='border:0;background:none;color:var(--fg);font:inherit;text-align:right;max-width:55%;min-height:36px';
const goBtn=(label,fn,off)=>{const b=h('button',{type:'button',disabled:!!off,style:'border:0;background:none;color:var(--ac);font:600 17px/1 var(--font);cursor:pointer;min-height:44px;padding:0 4px',onclick:async()=>{if(b.disabled)return;b.disabled=true;try{await fn()}finally{b.disabled=!!off}}},label);if(off)b.style.opacity='.5';return b};

DETAIL['robot/remote']=async v=>{add(v,...detailHead(T('Remote control'),'robot'));if(!UNIT){add(v,need());return}
 const id=UNIT.device_id,c=await cx(true),d=await RCDATA(id),reach=!!UNIT.online&&d.reachable!==false,off=!reach;
 const banner=off?offBanner(T('rem.offline')):(d.cue===false?offBanner(T('ra.cue_none')):null);
 /* 1. Say something: a text field and Send */
 const txt=h('input',{class:'tx',type:'text',maxlength:200,placeholder:T('rem.say_label'),'aria-label':T('rem.say'),disabled:off,style:'text-align:left'});
 const send=async()=>{const t=txt.value.trim();if(!t){toast(T('rem.say_label'),'warn');return}const r=await RC(id,{do:'say',text:t});if(r.ok)txt.value=''};
 const sendB=goBtn(T('Send'),send,off);txt.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();if(!sendB.disabled)sendB.click()}});
 const sayRow=h('div',{class:'r'},ricon('talk'),txt,sendB);
 /* 2. Look around: three head moves in one segmented row */
 const lk=h('div',{class:'sg',role:'group','aria-label':T('rem.look')});
 for(const [t,k] of [[T('Look'),'look'],[T('rem.nod'),'nod'],[T('rem.shake'),'shake']]){const b=h('button',{type:'button',disabled:off,onclick:async()=>{b.setAttribute('aria-checked','true');try{await RC(id,{do:k})}finally{b.setAttribute('aria-checked','false')}}},t);b.setAttribute('aria-checked','false');lk.append(b)}
 const lookRow=h('div',{class:'r col2'},h('span',{class:'rl'},T('rem.look')),lk);
 /* 3. Dance: pick one, Go */
 let danceRow=null;
 if(d.dances.length){const dsel=h('select',{'aria-label':T('rem.dance'),disabled:off,style:selStyle});for(const x of d.dances)dsel.append(h('option',{value:x.name},pretty(x.name)+(x.seconds?' ('+x.seconds+' s)':'')));
  danceRow=h('div',{class:'r'},ricon(aicon('dance')),h('span',{class:'rl'},T('rem.dance')),dsel,goBtn(T('Go'),()=>RC(id,{do:'dance',name:dsel.value}),off))}
 /* 4. Take a picture: the photo appears under the group */
 const shot=h('div',{});
 const picRow=actRow('photo',T('rem.photo'),async()=>{if(!d.photo){toast(T('rem.photo_need'),'warn');return}const r=await remote(id,{do:'photo'});if(r.ok&&r.d.image){shot.replaceChildren(h('div',{class:'pv2'},h('img',{src:r.d.image,alt:T('rem.photo_alt'),style:'width:100%;height:auto;display:block'})));toast(T('rem.done'))}},off,d.photo?'':T('rem.photo_need'));
 /* 5. Find my robot: starts and stops the beacon */
 let finding=false;
 const findRow=actRow('find',T('rem.find'),async(b,val)=>{const r=await remote(id,{do:'find',on:!finding});if(r.ok){finding=!finding;b.querySelector('.rl').textContent=finding?T('rem.find_stop'):T('rem.find');toast(r.d.message||T('rem.done'))}},off);
 /* 6. Mute */
 const priv=c.o.privacy;
 const muteRow=swRow(T('rem.mute'),priv?priv.mute:UNIT.muted,async on=>{const r=await remote(id,{do:'mute',on});if(r.ok)toast(on?T('rem.mute'):T('rem.unmute'));return r.ok},{icon:'vol',off});
 /* the fold: games, overlays, head position, sounds, lights, stop the dance */
 const gsel=h('select',{'aria-label':T('rem.game'),disabled:off,style:selStyle});for(const x of d.games)gsel.append(h('option',{value:x.id},x.title));
 const gameRow=d.games.length?h('div',{class:'r'},ricon('game'),h('span',{class:'rl'},T('rem.game')),gsel,goBtn(T('rem.game_go'),()=>RC(id,{do:'game',name:gsel.value}),off)):null;
 const fold=moreFold(gameRow,
  rowEl({label:T('pol.ov.title'),icon:aicon('layers'),go:()=>nav('robot','remote-overlays')}),
  rowEl({label:T('Head position'),icon:aicon('head'),go:()=>nav('robot','remote-head')}),
  actRow('beep',T('rem.beep'),()=>RC(id,{do:'beep'}),off),
  actRow('flash',T('rem.flash'),()=>RC(id,{do:'flash'}),off),
  d.dances.length?actRow('stop',T('rem.dance_stop'),()=>RC(id,{do:'stop_dance'}),off):null);
 add(v,banner,grp(null,sayRow,lookRow,danceRow,picRow,findRow,muteRow),shot,fold)};

DETAIL['robot/remote-head']=async v=>{add(v,...subHead(T('Head position'),'remote','robot'));if(!UNIT){add(v,need());return}
 const id=UNIT.device_id,d=await RCDATA(id),off=!(UNIT.online&&d.reachable!==false),L=d.limits,yMax=L.yaw,pMin=L.pitch[0],pMax=L.pitch[1];let yaw=0,pitch=pMin+10;
 const move=async()=>{const r=await RC(id,{do:'head',yaw:Math.round(yaw),pitch:Math.round(pitch)});return r.ok};
 const sy=slRow(T('Turn'),-yMax,yMax,1,yaw,x=>String(x),x=>{yaw=x;return move()},{icon:'remote'});
 const sp=slRow(T('Tilt'),pMin,pMax,1,pitch,x=>String(x),x=>{pitch=x;return move()},{icon:aicon('head')});
 if(off)for(const s of [sy,sp])s.querySelector('input').disabled=true;
 const reset=(s,val)=>{const i=s.querySelector('input');i.value=val;i.dispatchEvent(new Event('input'))};
 add(v,off?offBanner(T('rem.offline')):null,grp(null,sy,sp,actRow('remote',T('rem.center'),async()=>{const r=await RC(id,{do:'center'});if(r.ok){yaw=0;pitch=pMin;reset(sy,0);reset(sp,pMin)}},off)))};

DETAIL['robot/remote-overlays']=async v=>{add(v,...subHead(T('pol.ov.title'),'remote','robot'));if(!UNIT){add(v,need());return}
 const id=UNIT.device_id,d=await RCDATA(id),off=!(UNIT.online&&d.reachable!==false);let name=OVN[0]||'rain',level='normal',secs=8;
 const sel=h('select',{'aria-label':T('pol.ov.pick'),disabled:off,style:selStyle,onchange:e=>{name=e.target.value}});for(const o of OVN)sel.append(h('option',{value:o},T('pol.ov.'+o)));sel.value=name;
 add(v,off?offBanner(T('rem.offline')):null,grp(null,rowEl({label:T('pol.ov.pick'),icon:aicon('layers'),control:sel}),
  sgRow(T('pol.ov.level'),['light','normal','heavy'].map(x=>({v:x,t:T('pol.ov.'+x)})),level,async x=>{level=x;return true}),
  slRow(T('pol.ov.seconds'),2,30,1,secs,x=>x+' s',x=>{secs=x})),
  grp(null,actRow('check',T('pol.ov.test'),async()=>{await RC(id,{do:'overlay',name,intensity:level,seconds:secs})},off),actRow('stop',T('pol.ov.clear'),async()=>{await RC(id,{do:'overlay_clear'})},off)))};

/* ---- Remote access ---- */
const ACC='/api/stackchan/remote-access';
const accPut=async(a,patch)=>{const x=await save(ACC,patch,true);if(x.ok){Object.assign(a,x.d);toast(x.d.message||S['settings.saved'])}return x.ok};
const kindWord=k=>{const w=T('ra.k.'+k);return w==='ra.k.'+k?pretty(k):w};
const accErr=r=>h('p',{class:'empty2'},r.d.error||T('net_error'));

DETAIL['safety/access']=async v=>{add(v,...detailHead(T('Remote access'),'safety'));
 const r=await api(ACC);if(!r.ok){add(v,accErr(r));return}const a=r.d;const paired=a.controllers.filter(c=>c.status==='paired').length,waiting=a.controllers.length-paired;
 add(v,grp(null,
  swRow(T('Remote access'),a.enabled,on=>accPut(a,{enabled:on}),{icon:'key',help:T('ra.enabled_help')}),
  rowEl({label:T('ra.controllers'),icon:'people',value:waiting?paired+' + '+waiting+' '+T('ra.waiting').toLowerCase():String(paired),go:()=>nav('safety','controllers')})),
  moreFold(
   rowEl({label:T('Activity log'),icon:'info',go:()=>nav('safety','activity')}),
   sgRow(T('ra.speaking'),[{v:'off',t:T('ra.sp_off')},{v:'ask',t:T('Ask first')},{v:'on',t:T('ra.sp_on')}],a.speaking,x=>accPut(a,{speaking:x})),
   swRow(T('ra.nocue'),a.allow_without_cue,on=>accPut(a,{allow_without_cue:on}),{icon:'cam',help:T('ra.nocue_help')})))};

DETAIL['safety/controllers']=async v=>{add(v,...subHead(T('ra.controllers'),'access','safety'));
 const r=await api(ACC);if(!r.ok){add(v,accErr(r));return}const a=r.d,box=h('div',{});add(v,box);
 const draw=()=>{if(!a.controllers.length){box.replaceChildren(h('p',{class:'empty2'},T('ra.none')));return}
  const act=async(path,c)=>{const x=await save(path,{id:c.id},true);if(x.ok){a.controllers=x.d.controllers;toast(x.d.message||T('rem.done'));draw()}};
  box.replaceChildren(grp(null,...a.controllers.map(c=>{const btn=(t,fn,bad)=>h('button',{type:'button',style:'border:0;background:none;color:'+(bad?'var(--bad,#d33)':'var(--ac)')+';font:600 15px/1 var(--font);cursor:pointer;min-height:44px;padding:0 6px',onclick:fn},t);
   return rowEl({label:c.label,icon:'people',value:T(c.status==='paired'?'ra.paired':'ra.waiting'),control:h('span',{style:'display:flex;gap:4px'},c.status==='paired'?null:btn(T('ra.allow'),()=>act(ACC+'/allow',c)),btn(T('ra.revoke'),()=>act(ACC+'/revoke',c),true))})})))};
 draw()};

DETAIL['safety/activity']=async v=>{add(v,...subHead(T('Activity log'),'access','safety'));
 const r=await api(ACC);if(!r.ok){add(v,accErr(r));return}let a=r.d,last10=true;const box=h('div',{});
 const draw=()=>{const xs=last10?a.activity.slice(0,10):a.activity;
  box.replaceChildren(xs.length?grp(null,...xs.map(x=>rowEl({label:kindWord(x.action)+' · '+x.controller,icon:'info',value:T('ra.r.'+x.result),help:String(x.time).slice(0,19).replace('T',' ')+(x.text?' · “'+x.text+'”':'')+(x.note?' · '+x.note:'')}))):h('p',{class:'empty2'},T('ra.empty')))};
 add(v,grp(null,sgRow(T('Show'),[{v:'10',t:T('ra.last10')},{v:'all',t:T('ra.all')}],'10',async x=>{last10=x==='10';draw();return true})),box,
  grp(null,actRow('check',T('ra.refresh'),async()=>{const x=await api(ACC);if(x.ok){a=x.d;draw();toast(T('rem.done'))}else toast(x.d.error||T('net_error'),'bad')})));
 draw()};
}
"""
