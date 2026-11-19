# ruff: noqa: E501
"""The System page in the dashboard look (owner request 2026-11-19). Replaces ``more/system`` (old builder: ``BUILDERS.system``). Placement: host dashboard.

Visible rows: Robot name, Updates, About, Support the project, Reset. Behind More settings: words on the screen, time zone, host address, unit details.
The old Restart row was a disabled "soon" button (the host has no restart call for a unit), so it is hidden until that call exists
(docs/dev/settings-justification.md: hide a row that does nothing)."""

JS = r"""
/* ---- More > System (settings_ui_p_system.py) ---- */
{
const SPONSOR='https://github.com/sponsors/JesseWebDotCom';
const linkRow=(label,icon,href,help)=>{const hp=h('div',{class:'rh',hidden:true},help);
 const a=h('a',{class:'r go',href,target:'_blank',rel:'noopener noreferrer','aria-label':label},h('span',{class:'ri'},SVG(IC[icon])),h('span',{class:'rl'},label),chev());
 const i=h('button',{type:'button',class:'info','aria-label':T('More about')+' '+label,style:'position:absolute;right:50px;top:14px',onclick:()=>{hp.hidden=!hp.hidden}},'i');
 return h('div',{class:'rw',style:'position:relative'},a,i,hp)};
const sysSelect=(label,opts,val,fn)=>{const sel=h('select',{'aria-label':label,style:'border:0;background:none;color:var(--fg);font:inherit;text-align:right;max-width:60%',onchange:async e=>{const old=val;const ok=await fn(e.target.value);if(ok===false)e.target.value=old;else val=e.target.value}});
 for(const o of opts)sel.append(h('option',{value:o.v,selected:o.v===val},o.t));return sel};
DETAIL['more/system']=async v=>{add(v,...detailHead(T('System'),'more'));if(!UNIT){add(v,need());return}
 const u=UNIT,id=u.device_id;
 const nm=h('input',{class:'tx',type:'text',value:u.name,maxlength:40,'aria-label':T('Robot name'),onchange:async e=>{const r=await unitSet(id,{name:e.target.value});if(r.ok){u.name=e.target.value;drawPick()}else e.target.value=u.name}});
 const [cv,fv]=await Promise.all([api(unitPath(id,'clock')),faceView(id)]);
 const fold=[];
 if(fv.values&&fv.choices)fold.push(rowEl({label:S['settings.face.lang'],control:sysSelect(S['settings.face.lang'],fv.choices.lang.map(l=>({v:l,t:S['settings.lang.'+l]||l})),fv.values.lang,async l=>{const r=await save(facePath(id),{screen_lang:l});return r.ok}),icon:'talk'}));
 if(cv.ok&&cv.d.zones)fold.push(rowEl({label:S['settings.clock.zone'],control:sysSelect(S['settings.clock.zone'],cv.d.zones.map(z=>({v:z.id,t:z.label})),cv.d.zone,async z=>(await save(unitPath(id,'clock'),{zone:z})).ok),icon:'gear'}),
  rowEl({label:T('Set the clock'),icon:'gear',go:async()=>{await save(unitPath(id,'clock'),{sync:true})}}));
 fold.push(rowEl({label:T('Host address'),value:HOST||'',icon:'gear'}),rowEl({label:S['settings.details'],icon:'info',go:()=>nav('more','system-details')}));
 add(v,grp(null,rowEl({label:T('Robot name'),icon:'face',control:nm}),
  rowEl({label:T('Updates'),icon:'plus',go:()=>nav('more','system-update')}),
  rowEl({label:T('sys.about'),icon:'info',go:()=>{location.href='/about'}}),
  linkRow(T('Support the project'),'people',SPONSOR,T('MaiPai is free and open, and your support helps keep it going.')),
  rowEl({label:T('Reset'),icon:'lock',go:()=>nav('more','system-reset')})),
  moreFold(...fold))};
DETAIL['more/system-update']=async v=>{add(v,...detailHead(T('Updates'),'more'));if(!UNIT){add(v,need());return}
 const id=UNIT.device_id;const out=h('div',{class:'ok2',role:'status',hidden:true});
 const show=r=>{const m=r.ok?(r.d.message||''):(r.d.error||'');out.textContent=m;out.hidden=!m};
 add(v,h('p',{class:'sub'},T('Nothing installs until you choose Install update.')),out,
  grp(null,rowEl({label:S['settings.firmware'],value:UNIT.firmware_version||S['settings.firmware.unknown'],icon:'info'}),
   rowEl({label:T('system.check'),icon:'check',go:async()=>{const r=await api(setPath(id)+'/update',{});show(r);toast(r.ok?(r.d.message||T('Checked')):(r.d.error||T('net_error')),r.ok?'':'bad')}}),
   rowEl({label:S['settings.update_confirm'],icon:'plus',go:async()=>{if(!await ask(S['settings.update_confirm_ask'],S['settings.update_confirm']))return;const r=await api(setPath(id)+'/update',{confirm:true});show(r);toast(r.ok?(r.d.message||T('Update started')):(r.d.error||T('net_error')),r.ok?'':'bad')}})))};
DETAIL['more/system-reset']=async v=>{add(v,...detailHead(T('Reset'),'more'));if(!UNIT){add(v,need());return}
 const id=UNIT.device_id;const word=h('input',{class:'tx',type:'text',autocomplete:'off',placeholder:'RESET','aria-label':T('sys.reset_type')});
 add(v,grp(null,rowEl({label:T('sys.reset_type'),control:word,help:T('sys.reset_help')}),
  rowEl({label:T('sys.reset_go'),icon:'lock',go:async()=>{if(word.value!=='RESET'){toast(T('sys.reset_type'),'bad');return}
   if(await ask(T('sys.reset_help'),T('sys.reset_go'))){const r=await save(unitPath(id,'reset'),{confirm_word:word.value});if(r.ok)word.value=''}}})))};
DETAIL['more/system-details']=async v=>{add(v,...detailHead(S['settings.details'],'more'));if(!UNIT){add(v,need());return}
 const id=UNIT.device_id;const dd=await api(unitPath(id,'details'));const rows=[];
 if(dd.ok&&dd.d.version){const d=dd.d,free=d.internal_free||0,low=d.internal_min||0;
  rows.push(rowEl({label:S['settings.firmware'],value:d.version}),rowEl({label:'Tag',value:d.tag}),rowEl({label:T('sys.storage'),value:d.image+', '+d.slot}),rowEl({label:T('sys.memory'),value:bytesWord(free)+' '+T('sys.free')+', '+bytesWord(low)+' '+T('sys.lowest')}))}
 else add(v,h('p',{class:'empty2'},(dd.d&&dd.d.error)||T('net_error')));
 rows.push(rowEl({label:T('sys.host_version'),value:HOSTV}),rowEl({label:T('sys.license'),value:'GNU AGPL-3.0'}));
 add(v,grp(null,...rows.filter(r=>r)))};
}
"""
