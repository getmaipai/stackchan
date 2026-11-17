# ruff: noqa: E501
"""The settings page's Security section, as script: the passcode lock's status, set or change a code, remove it, the auto lock time and
Lock now. Every word comes from ``T('lk.*')`` (``i18n_lock.py``); every sentence of a refusal comes from the host (``unit_lock.py``).

The code is typed into password-type, numeric, at-most-six-digit fields with autocomplete off. It leaves the page in the JSON body of one
POST to the host and nowhere else: never in a URL, never in localStorage or sessionStorage, never in the console. Each field is cleared
after every request, whatever the answer."""

JS_LOCK = r"""
/* ---- security: the passcode lock (the unit keeps the code; this page only asks) ---- */
ICO.security='M6 11V8a6 6 0 0112 0v3M5 11h14v10H5zM12 15v2';
function lkField(label){return h('input',{type:'password',inputmode:'numeric',pattern:'[0-9]*',maxlength:6,autocomplete:'off',autocapitalize:'off',spellcheck:'false','aria-label':label,placeholder:T('lk.digits')})}
function lkNum(k,n){return T(k).replace('{n}',String(n))}
async function lockCard(id){
 const box=h('div',{class:'stack'});let v={status:'unknown',has_code:null,locked:null,auto_minutes:null,auto_options:[0,1,5,15,30,60],unit_ready:false};
 const say=(r,warn)=>{const d=r.d||{};if(r.ok&&d.ok!==false)toast(d.message||S['settings.saved']);else toast(d.error||d.message||T('net_error'),d.pending||warn?'warn':'bad')};
 const reload=async()=>{const r=await api(unitPath(id,'lock'));if(r.ok)v=r.d;draw()};
 const send=async(what,body,fields)=>{let r;try{r=await api(unitPath(id,what),body)}finally{fields.forEach(f=>{f.value=''})}say(r);await reload();return r.ok&&r.d.ok!==false};
 const status=()=>{const t=[T('lk.status')+': '+T('lk.status.'+v.status)];if(v.auto_minutes===0)t.push(T('lk.auto.off'));else if(v.auto_minutes>0)t.push(lkNum('lk.auto.on',v.auto_minutes));return h('p',{class:'hint',role:'status'},t.join('. '))};
 function draw(){
  const off=!v.unit_ready||v.locked===true,kids=[status()];
  if(v.locked===true)kids.push(h('p',{class:'hint'},T('lk.locked_note')));
  const cur=v.has_code?lkField(T('lk.current')):null,a=lkField(T('lk.new')),b=lkField(T('lk.again'));
  const save=h('button',{class:'btn pri',type:'button',disabled:off,onclick:async()=>{const body={code:a.value,confirm_code:b.value};if(cur)body.current=cur.value;await send('lock',body,[cur,a,b].filter(Boolean))}},T('lk.save'));
  kids.push(h('h3',{},v.has_code?T('lk.change_title'):T('lk.set_title')),h('p',{class:'hint'},T('lk.set_help')),...(cur?[field(T('lk.current'),cur)]:[]),field(T('lk.new'),a),field(T('lk.again'),b),h('div',{class:'btns'},save));
  if(v.has_code){const rc=lkField(T('lk.remove_current'));
   kids.push(h('h3',{},T('lk.remove_title')),h('p',{class:'hint'},T('lk.remove_help')),field(T('lk.remove_current'),rc),
    h('div',{class:'btns'},h('button',{class:'btn bad',type:'button',disabled:off,onclick:async()=>{await send('lock/clear',{current:rc.value},[rc])}},T('lk.remove'))))}
  kids.push(h('h3',{},T('lk.auto_title')),h('p',{class:'hint'},T('lk.auto_help')),
   seg(T('lk.auto_title'),v.auto_options.map(n=>({v:n,t:n===0?T('lk.auto_off'):lkNum('lk.minutes',n)})),v.auto_minutes,async n=>send('lock/auto',{auto_minutes:n},[]),off),
   h('div',{class:'btns'},h('button',{class:'btn',type:'button',disabled:!v.unit_ready||!v.has_code||v.locked===true,onclick:async()=>{await send('lock/now',{},[])}},T('lk.now'))),h('p',{class:'hint'},T('lk.now_help')),h('p',{class:'hint'},T('lk.forgot')));
  box.replaceChildren(...kids)}
 await reload();
 return card(T('lk.title'),T('lk.help'),box)}
BUILDERS.security=async(p,u)=>{p.append(h('div',{class:'stack'},await lockCard(u.device_id)))};
"""
