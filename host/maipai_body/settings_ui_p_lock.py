# ruff: noqa: E501
"""The Lock page in the dashboard look (``DETAIL['safety/lock']``, and ``'safety/lock-code'`` for changing the code).

Same host calls as the old Security card in ``settings_ui_lock.py``: GET ``lock``, POST ``lock``, ``lock/clear``, ``lock/now`` and
``lock/auto`` under ``/api/stackchan/unit/<id>/``. The old page has no "who can unlock" choice, so none is shown here.

The code is typed into password-type, numeric, at-most-six-digit fields with autocomplete off. It leaves the page in the JSON body of one
POST to the host and nowhere else: never in a URL, never in storage, never in the console. Each field is cleared after every request,
whatever the answer."""

JS = r"""
/* ---- safety/lock in the dashboard look (settings_ui_p_lock.py) ---- */
function lkPad(label){const i=h('input',{class:'tx',type:'password',inputmode:'numeric',pattern:'[0-9]*',maxlength:6,autocomplete:'off',autocapitalize:'off',spellcheck:'false','aria-label':label,placeholder:T('lk.digits'),style:'letter-spacing:.2em',oninput:()=>{i.value=i.value.replace(/\D/g,'')}});return i}
async function lkRead(){const r=await api(unitPath(UNIT.device_id,'lock'));return r.ok?r.d:{status:'unknown',has_code:null,locked:null,auto_minutes:null,auto_options:[0,1,15],unit_ready:false}}
async function lkSend(what,body,fields){let r;try{r=await api(unitPath(UNIT.device_id,what),body)}finally{fields.forEach(f=>{f.value=''})}
 const d=r.d||{},ok=r.ok&&d.ok!==false;toast(ok?(d.message||S['settings.saved']):(d.error||d.message||T('net_error')),ok?undefined:(d.pending?'warn':'bad'));return ok}
function lkForm(title,pads,label,fn,cancel){const run=async()=>{await fn()};pads[pads.length-1].onkeydown=e=>{if(e.key==='Enter')run()};
 return grp(title,...pads.map(([l,i])=>rowEl({label:l,icon:'key',control:i})),rowEl({label,icon:'check',go:run}),cancel?rowEl({label:T('Cancel'),go:cancel}):null)}
DETAIL['safety/lock']=async v=>{add(v,...detailHead(T('Lock'),'safety'));
 let st=await lkRead(),ask='';const box=h('div',{});add(v,box);
 const reload=async()=>{st=await lkRead();ask='';draw()};
 function draw(){const parts=[],busy=!st.unit_ready||st.locked===true;
  if(!st.unit_ready)parts.push(h('p',{class:'sub'},st.message||T('lk.status.unknown')));else if(st.locked===true)parts.push(h('p',{class:'sub'},T('Unlock the robot with its keypad to change this.')));
  parts.push(grp(null,
   swRow(T('Lock'),st.has_code===true,async on=>{ask=on?'new':'remove';draw();return false},{icon:'lock',off:busy,help:T('A code keeps other people from using the robot.')}),
   st.has_code?rowEl({label:T('Change code'),icon:'key',go:()=>nav('safety','lock-code')}):null,
   st.has_code?sgRow(T('Lock after'),(st.auto_options||[0,1,15]).concat(st.auto_minutes!=null&&!(st.auto_options||[0,1,15]).includes(st.auto_minutes)?[st.auto_minutes]:[]).map(n=>({v:n,t:n===0?T('lk.auto_off'):T('lk.minutes').replace('{n}',String(n))})),st.auto_minutes,async n=>{const ok=await lkSend('lock/auto',{auto_minutes:n},[]);if(ok)st.auto_minutes=n;return ok}):null));
  if(ask==='new'){const a=lkPad(T('lk.new')),b=lkPad(T('lk.again'));
   parts.push(lkForm(T('Set a code'),[[T('lk.new'),a],[T('lk.again'),b]],T('lk.save'),async()=>{if(await lkSend('lock',{code:a.value,confirm_code:b.value},[a,b]))await reload()},()=>{ask='';draw()}))}
  if(ask==='remove'){const c=lkPad(T('lk.current'));
   parts.push(lkForm(T('Turn lock off'),[[T('lk.current'),c]],T('lk.remove'),async()=>{if(await lkSend('lock/clear',{current:c.value},[c]))await reload()},()=>{ask='';draw()}))}
  if(st.has_code)parts.push(moreFold(
   st.unit_ready&&st.locked!==true?rowEl({label:T('lk.now'),icon:'lock',go:async()=>{if(await lkSend('lock/now',{},[]))await reload()}}):null,
   rowEl({label:T('Forgot the code'),icon:'info',help:T('lk.forgot')})));
  box.replaceChildren(...parts)}
 draw()};
DETAIL['safety/lock-code']=async v=>{add(v,...detailHead(T('Change code'),'safety'));
 const st=await lkRead(),cur=lkPad(T('lk.current')),a=lkPad(T('lk.new')),b=lkPad(T('lk.again'));
 if(!st.has_code){add(v,h('p',{class:'empty2'},T('lk.status.none')));return}
 if(!st.unit_ready||st.locked===true)add(v,h('p',{class:'sub'},st.locked===true?T('Unlock the robot with its keypad to change this.'):T('lk.status.unknown')));
 add(v,lkForm(null,[[T('lk.current'),cur],[T('lk.new'),a],[T('lk.again'),b]],T('lk.save'),async()=>{if(await lkSend('lock',{code:a.value,confirm_code:b.value,current:cur.value},[cur,a,b]))nav('safety','lock')},null))};
"""
