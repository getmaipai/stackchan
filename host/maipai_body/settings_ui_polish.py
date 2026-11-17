# ruff: noqa: E501
"""The settings page's newer sections, as script: overlays, listening cues, "While it thinks", look effects,
packs and languages. Appended to the page script by ``settings_ui``; every word comes from ``T('pol.*')``
(``i18n_polish.py``)."""

from __future__ import annotations

JS_POLISH = r"""
/* ---- newer features: overlays, listening cues, thinking sounds, look effects, packs, languages ---- */
const FXM={mono:'grayscale(1)',warm:'sepia(.6) saturate(1.3)',cool:'hue-rotate(170deg) saturate(.8)'};
const PACKT=['look','sound','dance','game'];
async function prefsView(id){const r=await api(unitPath(id,'prefs'));return r.ok?r.d:{values:{},unit_ready:false,features:{},notice:''}}
function comingBadge(){return h('span',{class:'badge'},T('pol.coming'))}
function comingNote(pv,key){return pv.unit_ready||(key&&pv.unit_keys&&!pv.unit_keys.includes(key))?null:h('p',{class:'hint'},comingBadge())}
function prefSaver(id,pv){return async patch=>{const r=await save(unitPath(id,'prefs'),patch);if(r.ok)Object.assign(pv.values,patch);return r.ok}}
function ptoggle(pv,put,key,label,help,after){return toggle(label,help,pv.values[key],async on=>{const ok=await put({[key]:on});if(ok&&after)after(on);return ok})}
function pseg(pv,put,key,label,opts,after){return seg(label,opts.map(o=>({v:o,t:T('pol.'+key+'.'+o)})),pv.values[key],async v=>{const ok=await put({[key]:v});if(ok&&after)after(v);return ok})}


/* Turning toward people: the unit's own seeker setting and who owns it (this robot, the Home hub, nobody) */
async function lookSeekCard(id,sv){const pv=await prefsView(id),put=prefSaver(id,pv),owner=pv.face_owner||sv.face_owner||'robot',ready=pv.features&&pv.features.look;
 const c=card(T('pol.look.title'),T('pol.look.help'),
  pseg(pv,put,'turn_to_faces',T('pol.look.mode'),['off','talk','always']),
  seg(T('pol.look.owner'),['robot','hub','off'].map(o=>({v:o,t:T('pol.face_owner.'+o)})),owner,async v=>(await save(unitPath(id,'device'),{face_owner:v})).ok),
  h('p',{class:'help'},T('pol.look.owner_help')));
 if(!ready)c.append(h('p',{class:'hint'},comingBadge()));
 return c}

/* overlays: pick one, how strong, how long, Test and Clear; the preview shows it at once */
function overlayCard(id,off,why,face,titleKey){let name='rain',level='normal',secs=8;
 const pills=h('div',{class:'pills',role:'radiogroup','aria-label':T('pol.ov.pick')});
 const draw=()=>pills.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v===name)));
 for(const o of OVN){const cv=document.createElement('canvas');cv.width=96;cv.height=72;cv.className='ovthumb';cv.setAttribute('aria-hidden','true');ovThumbs.set(cv,o);ovThumb(cv,o,REDUCED?3:performance.now()/1000);pills.append(h('button',{type:'button',class:'pill ovp',role:'radio','data-v':o,onclick:()=>{name=o;draw();if(face)face.ov(name,level,secs)}},cv,T('pol.ov.'+o)))}ovThumbLoop();draw();
 const lv=seg(T('pol.ov.level'),['light','normal','heavy'].map(x=>({v:x,t:T('pol.ov.'+x)})),level,v=>{level=v;if(face)face.ov(name,level,secs);return true});
 const sl=slider(T('pol.ov.seconds'),2,30,1,secs,x=>x+' s',v=>{secs=v},null,null);
 const test=h('button',{type:'button',class:'btn pri','aria-pressed':'false'},T('pol.ov.test'));
 test.addEventListener('click',()=>press(test,async()=>{if(face)face.ov(name,level,secs);const r=await remote(id,{do:'overlay',name,intensity:level,seconds:secs});if(!r.ok)toast(r.d.error,'bad');else if(r.d.pending)toast(r.d.message,'warn');else toast(T('rem.done'));return r},true));
 const clr=h('button',{type:'button',class:'btn'},T('pol.ov.clear'));
 clr.addEventListener('click',()=>press(clr,async()=>{if(face)face.ovClear();const r=await remote(id,{do:'overlay_clear'});if(!r.ok)toast(r.d.error,'bad');else if(r.d.pending)toast(r.d.message,'warn');return r},true));
 return card(T(titleKey||'pol.ov.title'),T('pol.ov.help'),pills,lv,sl,h('div',{class:'btns'},test,clr))}

/* Look: feelings, effects, look packs, overlays */
async function lookCards(id,u,v,has,face){const pv=await prefsView(id),put=prefSaver(id,pv),sp=await api(unitPath(id,'packs')),sd=sp.ok?sp.d:{packs:[],active:{},unit_ready:false};
 const fx=()=>({crt:pv.values.fx_crt,night:pv.values.fx_night_dim,glow:pv.values.fx_glow,mode:pv.values.fx_color_mode});
 const upd=()=>face.set({fx:fx(),capmode:pv.values.captions_mode,topbar:pv.values.top_bar,dots:pv.values.thinking_dots});upd();
 const feel=card(T('pol.feel.title'),T('pol.feel.help'),
  ptoggle(pv,put,'emotion_faces',T('pol.feel.emotion'),T('pol.feel.emotion_help')),
  ptoggle(pv,put,'speech_bubble',T('pol.feel.bubble'),T('pol.feel.bubble_help'),upd),
  ptoggle(pv,put,'thinking_dots',T('pol.feel.dots'),T('pol.feel.dots_help'),upd),comingNote(pv,'speech_bubble'));
 const caps=card(T('pol.cap.title'),T('pol.cap.help'),pseg(pv,put,'captions_mode',T('pol.cap.mode'),['off','subtitles','banner'],upd),comingNote(pv,'captions_mode'));
 const topbar=card(T('pol.top.title'),T('pol.top.help'),pseg(pv,put,'top_bar',T('pol.top.mode'),['hidden','always'],upd),comingNote(pv,'top_bar'));
 const eff=card(T('pol.fx.title'),T('pol.fx.help'),
  ptoggle(pv,put,'fx_crt',T('pol.fx.crt'),T('pol.fx.crt_help'),upd),
  ptoggle(pv,put,'fx_night_dim',T('pol.fx.night'),T('pol.fx.night_help'),upd),
  ptoggle(pv,put,'fx_glow',T('pol.fx.glow'),T('pol.fx.glow_help'),upd),
  pseg(pv,put,'fx_color_mode',T('pol.fx.mode'),['normal','mono','warm','cool'],upd),comingNote(pv,'fx_crt'));
 const lookPacks=sd.packs.filter(x=>x.type==='look'),act=(sd.active||{}).look||'';
 const list=h('div',{class:'list',role:'radiogroup','aria-label':T('pol.packs.look')});
 const rowB=(pid,name,sub)=>{const b=h('button',{type:'button',role:'radio',class:'pill','aria-checked':String(act===pid||(!act&&!pid)),style:'justify-content:space-between;display:flex;align-items:center;width:100%;min-height:48px;text-align:left',onclick:async()=>{const r=await save(unitPath(id,'packs/activate'),{type:'look',pack_id:pid});if(r.ok)list.querySelectorAll('button').forEach(x=>x.setAttribute('aria-checked',String(x===b)))}},h('span',{},name),h('span',{class:'hint'},sub||''));return b};
 list.append(rowB('',T('pol.packs.builtin'),T('pol.packs.builtin_help')));for(const x of lookPacks)list.append(rowB(x.id,x.name,Math.ceil(x.size/1000)+' KB'));
 const packsCard=card(T('pol.packs.look'),T('pol.packs.look_help'),list,lookPacks.length?null:h('p',{class:'hint'},T('pol.packs.none_look')),sd.unit_ready?null:h('p',{class:'hint'},comingBadge()));
 return{pv,cards:[feel,caps,topbar,eff,packsCard,overlayCard(id,false,'',face)]}}

/* Voice: when it listens, while it thinks */
async function voiceCards(id,u,v){const pv=await prefsView(id),put=prefSaver(id,pv),lang=v.lang||LANG;
 const notice=h('div',{class:'banner',role:'status'},T('pol.listen.all_off'));
 const showNotice=()=>{const x=pv.values;notice.hidden=!(x.listen_sound==='off'&&x.listen_light==='off'&&!x.listen_face)};showNotice();
 const names=['mint','sky','amber','rose','lilac','lime','coral'];const hexName=hx=>names.find(n=>PAL[n].toLowerCase()===String(hx).toLowerCase())||'';
 const col=swatches(T('pol.listen.color'),names,hexName(pv.values.listen_light_color),async n=>put({listen_light_color:PAL[n]}));
 const custom=h('input',{type:'color',value:pv.values.listen_light_color,'aria-label':T('pol.listen.color'),onchange:async e=>{const ok=await put({listen_light_color:e.target.value});if(ok)col.redraw(hexName(e.target.value))}});
 const test=h('button',{type:'button',class:'btn pri','aria-pressed':'false'},T('pol.listen.test'));
 test.addEventListener('click',()=>press(test,async()=>{const r=await save(unitPath(id,'listen-test'),{},true);if(!r.ok)toast(r.d.error,'bad');else toast(r.d.message,r.d.pending||!r.d.ok?'warn':undefined);return r},true));
 const listen=card(T('pol.listen.title'),T('pol.listen.help'),notice,
  pseg(pv,put,'listen_sound',T('pol.listen.sound'),['off','chime','mm'],showNotice),
  pseg(pv,put,'listen_light',T('pol.listen.light'),['off','dim','normal'],showNotice),
  h('div',{class:'row'},h('div',{class:'lbl'},h('b',{},T('pol.listen.color'))),h('div',{style:'display:flex;gap:10px;align-items:center;flex-wrap:wrap'},col,custom)),
  ptoggle(pv,put,'listen_face',T('pol.listen.face'),T('pol.listen.face_help'),showNotice),
  h('p',{class:'hint'},T('pol.listen.always')),h('div',{class:'btns'},test),comingNote(pv,'listen_sound'));
 /* while it thinks */
 const fr=await api(unitPath(id,'fillers')),fd=fr.ok?fr.d:{packs:[],active:null,status:{running:false},can_make:false};
 const wait=slider(T('pol.think.wait'),.2,1.5,.1,pv.values.filler_wait_s,x=>x.toFixed(1)+' s',null,x=>put({filler_wait_s:x}),['0.2 s','1.5 s']);
 const modeSeg=pseg(pv,put,'filler_mode',T('pol.think.title'),['none','tone','phrase'],m=>{api(facePath(id),{thinking_tone:m==='tone'});wait.classList.toggle('off',m==='none');wait.querySelector('input').disabled=m==='none'});
 wait.classList.toggle('off',pv.values.filler_mode==='none');wait.querySelector('input').disabled=pv.values.filler_mode==='none';
 const state=h('p',{class:'hint',role:'status'}),bar=h('div',{class:'meter','aria-hidden':'true',hidden:true},h('i',{style:'width:0%'}));
 const mk=h('button',{type:'button',class:'btn','aria-pressed':'false',disabled:!fd.can_make,title:fd.can_make?null:T('pol.think.noengine')},T('pol.think.make'));
 const showState=s=>{bar.hidden=!s.running;bar.firstChild.style.width=(s.total?Math.round(100*s.done/s.total):0)+'%';state.textContent=s.running?T('pol.think.making')+' '+s.done+'/'+s.total:s.error||(fd.packs.length?fd.packs.map(x=>x.name+' ('+Math.ceil(x.size/1000)+' KB)').join(', '):T('pol.think.none_made'))};showState(fd.status);
 const poll=async()=>{const r=await api(unitPath(id,'fillers'));if(!r.ok)return;fd.packs=r.d.packs;showState(r.d.status);if(r.d.status.running)setTimeout(poll,900);else{mk.classList.remove('busy');if(!r.d.status.error)toast(T('pol.think.made'))}};
 mk.addEventListener('click',async()=>{if(mk.classList.contains('busy'))return;mk.classList.add('busy');const r=await save(unitPath(id,'fillers/generate'),{voice:'default',lang},true);if(!r.ok){mk.classList.remove('busy');toast(r.d.error,'bad');return}poll()});
 const think=card(T('pol.think.title'),T('pol.think.help'),modeSeg,wait,h('p',{class:'hint'},T('pol.think.rules')),h('div',{class:'btns'},mk),bar,state,fd.can_make?null:h('p',{class:'hint'},T('pol.think.noengine')),comingNote(pv,'filler_mode')&&null);
 return[listen,think]}

/* Packs: the library, the active pack per unit, languages */
const sizeWord=b=>b>=1e6?(b/1e6).toFixed(1)+' MB':Math.ceil(b/1000)+' KB';
function b64FromBuffer(buf){let s='';const a=new Uint8Array(buf),c=0x8000;for(let i=0;i<a.length;i+=c)s+=String.fromCharCode.apply(null,a.subarray(i,i+c));return btoa(s)}
BUILDERS.packs=async(p,u)=>{const id=u.device_id,lr=await api('/api/stackchan/packs'),ur=await api(unitPath(id,'packs')),fv=await faceView(id);
 const lib=lr.ok?lr.d:{packs:[],types:[],limits:{},used:0,capacity:1},ud=ur.ok?ur.d:{active:{},unit_ready:false,packs:lib.packs};
 const body=h('div',{class:'list'}),meter=h('div',{class:'meter','aria-hidden':'true'},h('i',{style:'width:0%'})),used=h('p',{class:'hint'});
 const reload=()=>{BUILT.packs=false;p.querySelectorAll(':scope>:not(h1)').forEach(n=>n.remove());go('packs',true)};
 const rows=()=>{body.replaceChildren();if(!lib.packs.length)body.append(h('div',{class:'empty'},T('pol.packs.empty')));
  for(const x of lib.packs){const ex=h('button',{type:'button',class:'btn',onclick:async()=>{const r=await save('/api/stackchan/packs/export',{pack_id:x.id},true);if(!r.ok){toast(r.d.error,'bad');return}const a=h('a',{href:'data:application/octet-stream;base64,'+r.d.b64,download:r.d.filename});document.body.append(a);a.click();a.remove()}},T('pol.packs.export'));
   const del=h('button',{type:'button',class:'btn bad',onclick:async()=>{if(!(await ask(T('pol.packs.delete_ask').replace('{name}',x.name),T('pol.packs.delete'))))return;const r=await save('/api/stackchan/packs/delete',{pack_id:x.id},true);if(r.ok)reload();else toast(r.d.error,'bad')}},T('pol.packs.delete'));
   body.append(h('div',{class:'row'},h('div',{class:'lbl'},h('b',{},x.name),h('span',{},T('pol.type.'+x.type)+' · '+sizeWord(x.size)+(x.voice?' · '+x.voice:'')+(x.signed?' · '+T('pol.packs.signed'):''))),h('div',{class:'btns'},ex,del)))}
  meter.firstChild.style.width=Math.max(1,Math.round(100*lib.used/lib.capacity))+'%';used.textContent=T('pol.packs.used').replace('{used}',sizeWord(lib.used)).replace('{cap}',sizeWord(lib.capacity))};rows();
 const file=h('input',{type:'file',accept:'.maipack',hidden:true,onchange:async e=>{const f=e.target.files[0];if(!f)return;const r=await save('/api/stackchan/packs/import',{b64:b64FromBuffer(await f.arrayBuffer())},true);e.target.value='';if(r.ok){toast(T('pol.packs.imported'));reload()}else toast(r.d.error,'bad')}});
 const imp=h('button',{type:'button',class:'btn pri',onclick:()=>file.click()},T('pol.packs.import'));
 const libc=card(T('pol.packs.library'),T('pol.packs.library_help'),body,meter,used,h('div',{class:'btns'},imp,file));
 /* the active pack of each type for this unit */
 const act=h('div',{class:'list'});
 for(const ty of PACKT){const opts=lib.packs.filter(x=>x.type===ty),cur=(ud.active||{})[ty]||'',sel=h('select',{'aria-label':T('pol.type.'+ty),onchange:async e=>{const r=await save(unitPath(id,'packs/activate'),{type:ty,pack_id:e.target.value});if(!r.ok)e.target.value=cur}});
  sel.append(h('option',{value:''},T('pol.packs.builtin')));for(const x of opts)sel.append(h('option',{value:x.id,selected:x.id===cur},x.name+' ('+sizeWord(x.size)+')'));
  act.append(h('div',{class:'row'},h('div',{class:'lbl'},h('b',{},T('pol.type.'+ty)),h('span',{},T('pol.type.'+ty+'_help'))),sel))}
 const actc=card(T('pol.packs.active'),T('pol.packs.active_help'),ud.unit_ready?null:h('div',{class:'banner'},T('pol.packs.coming')),act);
 /* languages */
 const lv=fv.values||{lang:'en'},c=fv.choices||{lang:LANGS_ALL},langs=lib.packs.filter(x=>x.type==='language'),lcur=(ud.active||{}).language||'';
 const ls=h('select',{'aria-label':S['settings.face.lang'],onchange:e=>save(facePath(id),{screen_lang:e.target.value})});for(const l of c.lang)ls.append(h('option',{value:l,selected:l===lv.lang},S['settings.lang.'+l]||l));
 const lp=h('select',{'aria-label':T('pol.lang.pack'),onchange:async e=>{const r=await save(unitPath(id,'packs/activate'),{type:'language',pack_id:e.target.value});if(!r.ok)e.target.value=lcur}});
 lp.append(h('option',{value:''},T('pol.lang.none')));for(const x of langs)lp.append(h('option',{value:x.id,selected:x.id===lcur},x.name+(x.lang?' ('+x.lang+')':'')));
 const langc=card(T('pol.lang.title'),T('pol.lang.help'),field(S['settings.face.lang'],ls),field(T('pol.lang.pack'),lp),langs.length?null:h('p',{class:'hint'},T('pol.lang.none_help')),ud.unit_ready?null:h('p',{class:'hint'},comingBadge()));
 p.append(h('div',{class:'grid'},libc,actc,langc))};
"""
