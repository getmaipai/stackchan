# ruff: noqa: E501
"""The Behavior page in the new dashboard look: six rows up front, everything else in the fold or one level down.

Placement: host dashboard. The old builder (BUILDERS.behavior in settings_ui.py and its helper cards) is the spec for the
API calls; every call below is one that builder makes. The script runs inside one function so its names never clash with
another page's file."""

JS = r"""
/* ---- Behavior (settings_ui_p_behavior.py) ---- */
(()=>{
const P='behavior';
const IK={clock:'M12 3a9 9 0 100 18 9 9 0 000-18zM12 7v5l3 2',timer:'M10 2h4M12 8v5l3 2M12 5a8 8 0 100 16 8 8 0 000-16z',bell:'M6 17v-6a6 6 0 0112 0v6l2 2H4zM10 21h4',look:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 100 6 3 3 0 000-6z',head:'M12 3a9 9 0 100 18 9 9 0 000-18zM9 10v2M15 10v2M9 15c1.5 1.4 4.5 1.4 6 0',music:'M9 18V6l10-2v12M9 18a3 3 0 11-6 0 3 3 0 016 0zM19 16a3 3 0 11-6 0 3 3 0 016 0z',pages:'M4 5h12v14H4zM8 3h12v14',react:'M4 5h16v11H9l-5 4z'};
const sub=(title,key,label)=>[h('div',{class:'dt'},h('button',{type:'button',class:'back',onclick:()=>nav('more',key||P)},SVG(IC.back),label||T('Behavior'))),h('h1',{class:'lt'},title)];
const noUnit=v=>{add(v,need())};
const saved=()=>{if(!CXD.o)CXD.o={};if(!CXD.o.saved)CXD.o.saved={};return CXD.o.saved};
const put=async patch=>{const r=await dev(patch);if(r.ok)Object.assign(saved(),patch);return r.ok};
const enc=encodeURIComponent;
const tinyInput='border:0;background:none;color:var(--fg);font:inherit';

/* the front view: six rows, then the fold */
DETAIL['more/behavior']=async v=>{add(v,...detailHead(T('Behavior'),'more'));if(!UNIT){noUnit(v);return}
 const c=await cx(true),sv=c.o.saved||{};
 add(v,h('p',{class:'sub'},T('Off keeps the head still until someone speaks.')),
  grp(null,
   sgRow(T('Head movement'),[{v:'off',t:T('Off')},{v:'calm',t:T('Calm')},{v:'lively',t:T('Lively')}],sv.idle_movement||'off',m=>put({idle_movement:m})),
   swRow(T('Look toward people'),!!sv.look_speaker,on=>put({look_speaker:on}),{icon:IK.look,help:T('Turns or glances toward you when you start talking.')}),
   rowEl({label:T('Clock and time zone'),icon:IK.clock,go:()=>nav('more','behavior-clock')}),
   rowEl({label:T('Timers'),icon:IK.timer,go:()=>nav('more','behavior-timers')}),
   rowEl({label:T('Alarms'),icon:IK.bell,go:()=>nav('more','behavior-alarms')}),
   rowEl({label:T('People'),icon:'people',go:()=>nav('more','behavior-people')})),
  moreFold(
   swRow(T('Look when called'),sv.look_on_wake!==false,on=>put({look_on_wake:on}),{icon:IK.look,help:T('wake_look_help')}),
   swRow(T('Look for faces'),!!sv.look_faces,on=>put({look_faces:on}),{icon:IK.look,help:T('Searches the room with the camera when something moves. Needs the camera on.')}),
   rowEl({label:T('Turning toward faces'),icon:IK.look,go:()=>nav('more','behavior-look')}),
   swRow(T('Dance to music'),!!sv.dance_to_music,async on=>{const r=await dev({dance_to_music:on});if(r.ok){saved().dance_to_music=on;if(r.d.status)toast(T('pol.dance.status.'+r.d.status))}return r.ok},{icon:IK.music,help:T('pol.dance.help')}),
   rowEl({label:T('Quiet hours'),icon:'moon',go:()=>nav('safety','quiet')}),
   rowEl({label:T('Swipe pages'),icon:IK.pages,go:()=>nav('more','behavior-pages')}),
   rowEl({label:T('Word reactions'),icon:IK.react,go:()=>nav('more','behavior-react')}),
   rowEl({label:T('Camera and microphone'),icon:'cam',go:()=>nav('safety','')})))};

/* turning toward faces: the unit's own setting and who owns it */
DETAIL['more/behavior-look']=async v=>{add(v,...sub(T('Turning toward faces')));if(!UNIT){noUnit(v);return}
 const id=UNIT.device_id,c=await cx(),sv=c.o.saved||{};const pr=await api(unitPath(id,'prefs'));const pv=pr.ok?pr.d:{values:{},features:{}};
 if(!(pv.features&&pv.features.look)){add(v,h('p',{class:'empty2'},T('pol.coming')));return}
 const owner=pv.face_owner||sv.face_owner||'robot';
 add(v,h('p',{class:'sub'},T('Pictures are looked at once and forgotten.')),
  grp(null,
   sgRow(T('Turn toward faces'),['off','talk','always'].map(o=>({v:o,t:T('pol.turn_to_faces.'+o)})),(pv.values||{}).turn_to_faces||'off',async m=>{const r=await save(unitPath(id,'prefs'),{turn_to_faces:m});if(r.ok)(pv.values||(pv.values={})).turn_to_faces=m;return r.ok}),
   sgRow(T('pol.look.owner'),['robot','hub','off'].map(o=>({v:o,t:T('pol.face_owner.'+o)})),owner,async o=>{const r=await dev({face_owner:o});if(r.ok)saved().face_owner=o;return r.ok}),
   pv.look&&pv.look.owner&&typeof lookStatus==='function'?rowEl({label:T('Status'),value:lookStatus(pv.look)}):null),
  moreFold(rowEl({label:T('Camera use'),help:T('pol.look.help')}),rowEl({label:T('Who moves the head'),help:T('pol.look.owner_help')})))};

/* clock and time zone */
DETAIL['more/behavior-clock']=async v=>{add(v,...sub(T('Clock and time zone')));if(!UNIT){noUnit(v);return}
 const id=UNIT.device_id,c=await cx(),fv=c.fv||{},vals=fv.values||{},has=f=>fv.features==null||(fv.features||[]).includes(f);
 const cv=await api(unitPath(id,'clock'));const rows=[];
 if(cv.ok&&cv.d.zones){let cur=cv.d.zone;
  const sel=h('select',{'aria-label':T('Time zone'),style:tinyInput+';text-align:right;max-width:60%',onchange:async e=>{const old=cur,r=await save(unitPath(id,'clock'),{zone:e.target.value});if(r.ok)cur=e.target.value;else e.target.value=old}});
  for(const z of cv.d.zones)sel.append(h('option',{value:z.id,selected:z.id===cur},z.label));
  rows.push(rowEl({label:T('Time zone'),icon:IK.clock,control:sel,help:T('time.zone_help')}),
   rowEl({label:T('Set clock now'),icon:'check',go:()=>save(unitPath(id,'clock'),{sync:true})}))}
 else add(v,h('p',{class:'empty2'},(cv.d&&cv.d.error)||T('net_error')));
 if(fv.values&&has('clock'))rows.push(
  swRow(T('face.clock24'),!!vals.clock24,async on=>{const r=await save(facePath(id),{clock24:on});if(r.ok)vals.clock24=on;return r.ok}),
  sgRow(T('face.clock_style'),[{v:'digits',t:T('face.clock_digits')},{v:'ring',t:T('face.clock_ring')}],vals.clock_style||'digits',async s=>{const r=await save(facePath(id),{clock_style:s});if(r.ok)vals.clock_style=s;return r.ok}),
  slRow(T('Clock when idle'),0,3600,30,vals.clock_idle_s||0,x=>x===0?T('face.never'):x+' '+T('face.seconds'),async x=>{const r=await save(facePath(id),{clock_idle_s:x});if(r.ok)vals.clock_idle_s=x}));
 if(rows.length)add(v,grp(null,...rows))};

/* timers: started by voice, so this view says how and points to the page that shows them */
DETAIL['more/behavior-timers']=async v=>{add(v,...sub(T('Timers')));if(!UNIT){noUnit(v);return}
 add(v,h('p',{class:'sub'},T('time.timers_help')),
  grp(null,rowEl({label:T('Swipe pages'),icon:IK.pages,go:()=>nav('more','behavior-pages')})))};

/* alarms: one small group per alarm */
DETAIL['more/behavior-alarms']=async v=>{add(v,...sub(T('Alarms')));if(!UNIT){noUnit(v);return}
 const id=UNIT.device_id,DAYS=['mon','tue','wed','thu','fri','sat','sun'];
 let rows=(UNIT.alarms||[]).map(a=>({time:a.time,label:a.label||'',days:a.days||DAYS.slice()}));
 const box=h('div');add(v,h('p',{class:'sub'},T('The robot rings these on the days you pick.')),box);
 const persist=async()=>{const list=rows.filter(r=>/^\d\d:\d\d$/.test(r.time)&&r.days.length);const r=await unitSet(id,{alarms:list});if(r.ok)UNIT.alarms=list.map(a=>Object.assign({},a));return r.ok};
 const draw=()=>{box.replaceChildren();
  if(!rows.length)box.append(grp(null,h('p',{class:'empty2'},T('time.no_alarms'))));
  rows.forEach((r,i)=>{
   const tm=h('input',{type:'time',value:r.time,'aria-label':S['settings.alarm_time'],style:tinyInput,onchange:async e=>{const old=r.time;if(!/^\d\d:\d\d$/.test(e.target.value)){e.target.value=old;return}r.time=e.target.value;if(!(await persist())){r.time=old;e.target.value=old}}});
   const lb=h('input',{class:'tx',type:'text',value:r.label,maxlength:60,placeholder:T('Optional'),'aria-label':S['settings.alarm_label'],onchange:async e=>{const old=r.label;r.label=e.target.value;if(!(await persist())){r.label=old;e.target.value=old}}});
   const days=h('div',{class:'sg',role:'group','aria-label':T('Days')});
   DAYS.forEach(d=>days.append(h('button',{type:'button','aria-checked':String(r.days.includes(d)),onclick:async e=>{const b=e.currentTarget,old=r.days.slice(),on=!r.days.includes(d);r.days=on?DAYS.filter(x=>x===d||r.days.includes(x)):r.days.filter(x=>x!==d);b.setAttribute('aria-checked',String(on));
    if(!(await persist())){r.days=old;b.setAttribute('aria-checked',String(!on))}}},T('day.'+d))));
   box.append(grp(null,rowEl({label:T('Time'),icon:IK.bell,control:tm}),rowEl({label:T('Name'),control:lb}),h('div',{class:'r col2'},h('span',{class:'rl'},T('Days')),days),
    rowEl({label:T('time.remove'),go:async()=>{const gone=rows.splice(i,1)[0];draw();if(!(await persist())){rows.splice(i,0,gone);draw()}}})))});
  box.append(grp(null,rowEl({label:S['settings.alarm_add'],icon:'plus',go:async()=>{const a={time:'07:30',label:'',days:DAYS.slice()};rows.push(a);draw();if(!(await persist())){rows.pop();draw()}}})))};
 draw()};

/* people: a list, then one person at a time */
let PERSON=null;
DETAIL['more/behavior-people']=async v=>{add(v,...sub(T('People')));if(!UNIT){noUnit(v);return}
 const r=await api('/api/stackchan/people');if(!r.ok){add(v,h('p',{class:'empty2'},r.d.error||T('net_error')));return}
 const d=r.d;add(v,h('p',{class:'sub'},T('people.empty_help')),
  grp(null,...(d.people.length?d.people.map(p=>rowEl({label:p.name||T('Unnamed'),value:p.wake_phrase||'',go:()=>{PERSON=p;nav('more','behavior-person')}})):[h('p',{class:'empty2'},S['settings.people.none'])]),
   rowEl({label:T('people.add'),icon:'plus',go:()=>{PERSON={};nav('more','behavior-person')}})))};
DETAIL['more/behavior-person']=async v=>{add(v,...sub(T('Person'),'behavior-people',T('People')));if(!UNIT){noUnit(v);return}
 if(!PERSON){nav('more','behavior-people');return}
 const r=await api('/api/stackchan/people');if(!r.ok){add(v,h('p',{class:'empty2'},r.d.error||T('net_error')));return}
 const ch=r.d.choices,p=Object.assign({id:'',name:'',color:'none',caption_size:'medium',wake_phrase:''},PERSON),back=()=>nav('more','behavior-people');
 const name=h('input',{class:'tx',type:'text',value:p.name,maxlength:24,'aria-label':S['settings.people.name']}),wake=h('input',{class:'tx',type:'text',value:p.wake_phrase,maxlength:24,'aria-label':S['settings.people.wake']});
 const sw=swatches(S['settings.people.color'],ch.color,p.color,x=>{p.color=x});
 add(v,grp(null,rowEl({label:T('Name'),control:name}),rowEl({label:T('Wake phrase'),control:wake}),h('div',{class:'r col2'},h('span',{class:'rl'},T('Color')),sw),
   sgRow(T('Caption size'),ch.caption_size.map(s=>({v:s,t:S['settings.face.caption_size.'+s]||s})),p.caption_size,x=>{p.caption_size=x;return true})),
  grp(null,rowEl({label:S['settings.people.save'],icon:'check',go:async()=>{if(!name.value.trim()){toast(T('Type a name first.'),'warn');return}
    const k=await save('/api/stackchan/people',{id:p.id,name:name.value,color:p.color,caption_size:p.caption_size,wake_phrase:wake.value});if(k.ok)back()}}),
   p.id?rowEl({label:S['settings.people.use'],icon:'face',go:()=>save('/api/stackchan/people/'+enc(p.id)+'/use/'+enc(UNIT.device_id),{})}):null,
   p.id?rowEl({label:S['settings.people.remove'],go:async()=>{if(!(await ask(T('Remove')+' '+(p.name||T('Person'))+'?',S['settings.people.remove'])))return;const k=await api('/api/stackchan/people/'+enc(p.id)+'/remove',{});if(k.ok){toast(T('Removed'));back()}else toast(k.d.error||T('net_error'),'bad')}}):null))};

/* swipe pages and word reactions: long editors, kept as they were inside the new frame */
const framed=(title,build)=>async v=>{add(v,...sub(title));if(!UNIT){noUnit(v);return}
 const box=h('div',{class:'legacy'});add(v,box);const c=await build(UNIT);if(c)box.append(c);else box.append(h('p',{class:'empty2'},T('net_error')))};
DETAIL['more/behavior-pages']=framed(T('Swipe pages'),u=>swipePagesCard(u.device_id));
DETAIL['more/behavior-react']=framed(T('Word reactions'),u=>reactCard(u));
})();
"""
