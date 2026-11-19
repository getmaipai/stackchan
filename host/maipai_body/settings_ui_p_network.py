# ruff: noqa: E501
"""The Network page in the new dashboard look (api38): Wi-Fi status, a network check, the guided steps for using the robot away from home,
and the paired robots. The calls are the ones the old builder (``BUILDERS.network`` and ``tsCard`` in settings_ui.py) makes."""

from __future__ import annotations

JS = r"""
/* ---- Network (settings_ui_p_network.py) ---- */
(()=>{
const TS_LINK='https://login.tailscale.com/admin/settings/keys';
const GUIDE='https://github.com/getmaipai/stackchan/blob/main/docs/user/use-it-anywhere.md';
const MARK={ok:['M5 12l5 5 9-10','var(--ok)'],warn:['M12 4l9 16H3zM12 10v4M12 17h.01','var(--warn)'],fail:['M6 6l12 12M18 6L6 18','var(--bad)']};
const mark=s=>MARK[s==='ok'?'ok':s==='warn'?'warn':'fail'];
function stepRow(s){const m=mark(s.state);return h('div',{class:'r'},h('span',{class:'ri',style:'background:'+m[1]},SVG(m[0])),h('span',{class:'rl'},s.line||''))}
function plainRow(label,value,help){return rowEl({label,value,help})}
let busy=false;
async function runCheck(out){if(busy)return;const id=UNIT.device_id;busy=true;out.replaceChildren(h('p',{class:'empty2'},T('Checking')+'...'));
 const r=await api(unitPath(id,'network-test'),{});busy=false;const d=r.d||{};
 if(!r.ok){out.replaceChildren(h('div',{class:'ok2',style:'background:color-mix(in srgb,var(--bad) 14%,var(--grp))'},d.error||T('net_error')));toast(d.error||T('net_error'),'bad');return}
 const steps=Array.isArray(d.steps)?d.steps:[];
 out.replaceChildren(...[steps.length?grp(T('Each step'),...steps.map(stepRow)):null,d.summary?h('p',{class:'sub'},d.summary):null,d.fix?h('p',{class:'sub'},d.fix):null].filter(Boolean));
 toast(d.summary||T('Check finished'),steps.some(s=>s.state!=='ok'&&s.state!=='warn')?'bad':null)}
DETAIL['more/network']=async v=>{add(v,...detailHead(T('Network'),'more'));
 if(!UNIT){add(v,need());return}
 const c=await cx();const o=c.o||{};const out=h('div',{});
 const wifi=S['settings.wifi.'+UNIT.wifi]||UNIT.wifi||'';
 add(v,grp(null,
  rowEl({label:'Wi-Fi',icon:'wifi',value:wifi}),
  rowEl({label:T('Run a check'),icon:'check',go:()=>runCheck(out)}),
  rowEl({label:T('Away from home'),icon:'remote',go:()=>nav('more','network-away')}),
  rowEl({label:T('Paired robots'),icon:'people',go:()=>nav('more','network-robots')})),
  out,
  moreFold(
   plainRow(S['settings.online']||T('Online'),UNIT.online?(S['settings.online.yes']||T('Yes')):(S['settings.online.no']||T('No'))),
   plainRow(T('Robot ID'),UNIT.device_id),
   plainRow(T('Battery'),o.battery&&o.battery.percent!=null?o.battery.percent+'%':'')))};
DETAIL['more/network-robots']=async v=>{add(v,...detailHead(T('Paired robots'),'more'));
 const list=(typeof UNITS!=='undefined'&&UNITS)||[];
 add(v,list.length?grp(null,...list.map(u=>rowEl({label:u.name||u.device_id,value:u.online?T('Online'):T('Offline'),icon:'face'}))):h('p',{class:'empty2'},T('Add your first robot to begin.')),
  grp(T('This computer'),plainRow(T('Address'),HOST||''),plainRow(T('Robot ID'),UNIT?UNIT.device_id:'')),
  h('p',{class:'sub'},T('net.pair_help')))};
DETAIL['more/network-away']=async v=>{add(v,...detailHead(T('Away from home'),'more'));
 if(!UNIT){add(v,need());return}
 const id=UNIT.device_id,tv=await api(unitPath(id,'travel'));
 const about=rowEl({label:T('About this'),icon:'info',go:()=>window.open(GUIDE,'_blank','noopener,noreferrer')});
 if(!(tv.ok&&tv.d.available)){add(v,h('div',{class:'ok2',style:'background:color-mix(in srgb,var(--warn) 16%,var(--grp))'},tv.ok?(tv.d.error||T('ts.err.not_compiled')):(tv.d.error||T('net_error'))),grp(null,about));return}
 const d=tv.d;const again=()=>render();
 const errText={refusal:T('ts.err.refusal'),key:T('ts.err.bad_key'),error:T('ts.err.bad_key')}[d.last_error]||'';
 const code=h('input',{class:'tx',type:'password',autocomplete:'off',spellcheck:'false',placeholder:T('Paste it here'),'aria-label':T('Access code'),name:'ts-'+Math.random().toString(36).slice(2)});
 const peer=h('input',{class:'tx',type:'text',inputmode:'decimal',autocomplete:'off',value:d.peer||'',placeholder:'100.x.x.x','aria-label':T('Home address'),name:'ts-'+Math.random().toString(36).slice(2)});
 const state=T('ts.state.'+d.phase);
 const out=h('div',{});
 add(v,grp(T('Set up in three steps'),
   rowEl({label:T('1. Get an access code'),icon:'key',value:T('Opens Tailscale'),go:()=>window.open(TS_LINK,'_blank','noopener,noreferrer')}),
   rowEl({label:T('2. Paste the code'),icon:'lock',control:code}),
   rowEl({label:T('3. Send it to the robot'),icon:'check',go:async()=>{if(!code.value.trim()){toast(T('Paste the access code first.'),'bad');return}const r=await save(unitPath(id,'travel'),{key:code.value});if(r.ok){code.value='';again()}}})),
  grp(null,
   rowEl({label:T('Status'),value:state}),
   swRow(T('Use it away'),!!d.enabled,async on=>(await save(unitPath(id,'travel'),{enabled:on})).ok,{icon:'remote',help:T('ts.about_body')})),
  errText?h('p',{class:'sub'},errText):null,out,
  moreFold(
   d.ip?plainRow(T('ts.addr'),d.ip):null,
   plainRow(T('ts.route'),d.route==='private'?T('ts.route.private'):T('ts.route.home')),
   rowEl({label:T('Home address'),control:peer}),
   rowEl({label:T('Save address'),go:async()=>{const r=await save(unitPath(id,'travel'),{peer:peer.value});if(r.ok)again()}}),
   rowEl({label:T('Test the connection'),go:async()=>{const r=await api(unitPath(id,'travel'));const x=r.d||{};
     toast(!r.ok||!x.available?(x.error||T('net_error')):x.phase==='connected'?T('ts.test.ok'):!x.ready_to_use?T('ts.test.nokey'):x.last_error?({refusal:T('ts.err.refusal'),key:T('ts.err.bad_key'),error:T('ts.err.bad_key')}[x.last_error]||''):T('ts.test.ready'),r.ok&&x.available&&!x.last_error?null:'bad')}}),
   rowEl({label:T('Forget the code'),go:async()=>{if(await ask(T('units.travel_forget')+'?',T('units.travel_forget'))){const r=await save(unitPath(id,'travel'),{forget:true});if(r.ok)again()}}}),
   about))};
})();
"""
