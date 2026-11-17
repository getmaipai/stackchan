# ruff: noqa: E501
"""The settings page's newer sections, as script: overlays, listening cues, "While it thinks", look effects,
packs and languages. Appended to the page script by ``settings_ui``; every word comes from ``T('pol.*')``
(``i18n_polish.py``)."""

from __future__ import annotations

JS_POLISH = r"""
/* ---- newer features: overlays, listening cues, thinking sounds, look effects, packs, languages ---- */
const OVN=['rain','snow','sun','clouds','wind','thunder','fog','stars','disco','confetti','fireworks','hearts','steam','balloons','leaves','zzz'];
const FXM={mono:'grayscale(1)',warm:'sepia(.6) saturate(1.3)',cool:'hue-rotate(170deg) saturate(.8)'};
const PACKT=['look','sound','dance','game'];
async function prefsView(id){const r=await api(unitPath(id,'prefs'));return r.ok?r.d:{values:{},unit_ready:false,features:{},notice:''}}
function comingBadge(){return h('span',{class:'badge'},T('pol.coming'))}
function comingNote(pv,key){return pv.unit_ready||(key&&pv.unit_keys&&!pv.unit_keys.includes(key))?null:h('p',{class:'hint'},comingBadge())}
function prefSaver(id,pv){return async patch=>{const r=await save(unitPath(id,'prefs'),patch);if(r.ok)Object.assign(pv.values,patch);return r.ok}}
function ptoggle(pv,put,key,label,help,after){return toggle(label,help,pv.values[key],async on=>{const ok=await put({[key]:on});if(ok&&after)after(on);return ok})}
function pseg(pv,put,key,label,opts,after){return seg(label,opts.map(o=>({v:o,t:T('pol.'+key+'.'+o)})),pv.values[key],async v=>{const ok=await put({[key]:v});if(ok&&after)after(v);return ok})}

/* what the preview draws for each overlay (the unit draws its own) */
function drawOv(d,ov,t,w,h){const k={light:.45,normal:1,heavy:1.8}[ov.intensity]||1,s=w/640,tt=t-ov.t0,n=Math.round(36*k),R=(i,j)=>{const x=Math.sin(i*127.1+j*311.7)*43758.5453;return x-Math.floor(x)},W=640,H=480,nm=ov.name;
 d.save();d.scale(s,s);d.lineCap='round';
 if(nm==='rain'){d.strokeStyle='rgba(150,200,255,.75)';d.lineWidth=2;for(let i=0;i<n*2;i++){const x=R(i,1)*W,y=((R(i,2)*H+tt*(520+R(i,3)*300))%(H+40))-20;d.beginPath();d.moveTo(x,y);d.lineTo(x-6,y+22);d.stroke()}}
 else if(nm==='snow'){d.fillStyle='rgba(255,255,255,.9)';for(let i=0;i<n*1.5;i++){const x=R(i,1)*W+Math.sin(tt*1.3+i)*18,y=(R(i,2)*H+tt*(50+R(i,3)*60))%H;d.beginPath();d.arc(x,y,2+R(i,4)*3,0,6.3);d.fill()}}
 else if(nm==='sun'){const cx=520,cy=90+Math.sin(tt)*6;d.fillStyle='rgba(255,210,70,.95)';d.beginPath();d.arc(cx,cy,34,0,6.3);d.fill();d.strokeStyle='rgba(255,210,70,.8)';d.lineWidth=5;for(let i=0;i<12;i++){const a=i*.5236+tt*.5;d.beginPath();d.moveTo(cx+Math.cos(a)*46,cy+Math.sin(a)*46);d.lineTo(cx+Math.cos(a)*68,cy+Math.sin(a)*68);d.stroke()}}
 else if(nm==='clouds'){d.fillStyle='rgba(225,232,245,.88)';for(let i=0;i<3;i++){const x=((tt*14+i*260)%900)-130,y=50+i*30;for(const[dx,dy,r]of[[0,0,34],[38,-12,42],[80,2,32],[40,10,36]]){d.beginPath();d.arc(x+dx,y+dy,r,0,6.3);d.fill()}}}
 else if(nm==='wind'){d.strokeStyle='rgba(220,235,255,.7)';d.lineWidth=3;for(let i=0;i<n/3;i++){const y=40+R(i,1)*400,x=((tt*(300+R(i,2)*200)+R(i,3)*W)%(W+200))-100;d.beginPath();d.moveTo(x,y);d.bezierCurveTo(x+30,y-12,x+60,y+12,x+90,y-4);d.stroke()}}
 else if(nm==='thunder'){const ph=(tt%3)/3;if(ph<.06||(ph>.1&&ph<.14)){d.fillStyle='rgba(255,255,255,.55)';d.fillRect(0,0,W,H)}if(ph<.14){d.strokeStyle='rgba(255,236,120,.95)';d.lineWidth=5;d.beginPath();d.moveTo(470,0);d.lineTo(440,110);d.lineTo(480,120);d.lineTo(440,250);d.stroke()}}
 else if(nm==='fog'){for(let i=0;i<4;i++){const y=120+i*80,g=d.createLinearGradient(0,y-40,0,y+40);g.addColorStop(0,'rgba(210,215,225,0)');g.addColorStop(.5,'rgba(210,215,225,.28)');g.addColorStop(1,'rgba(210,215,225,0)');d.fillStyle=g;d.fillRect(((tt*10*(i%2?1:-1))%60)-60,y-40,W+120,80)}}
 else if(nm==='stars'){d.fillStyle='#fff';for(let i=0;i<n;i++){d.globalAlpha=.35+.65*Math.abs(Math.sin(tt*1.6+i*2.1));star(d,R(i,1)*W,R(i,2)*H*.55,3+R(i,3)*5)}d.globalAlpha=1}
 else if(nm==='disco'){d.fillStyle='rgba(0,0,0,.32)';d.fillRect(0,0,W,H);for(let i=0;i<n/3;i++){d.fillStyle='hsla('+((i*47+tt*60)%360)+',90%,60%,.35)';d.beginPath();d.arc(R(i,1)*W+Math.sin(tt+i)*30,R(i,2)*H+Math.cos(tt*1.3+i)*20,22+R(i,3)*20,0,6.3);d.fill()}d.fillStyle='#cfd6e6';d.beginPath();d.arc(320,46,32,0,6.3);d.fill();d.fillStyle='#fff';for(let i=0;i<6;i++){d.globalAlpha=.4+.6*Math.abs(Math.sin(tt*3+i));star(d,320+Math.cos(tt+i)*22,46+Math.sin(tt*1.2+i*2)*20,5)}d.globalAlpha=1}
 else if(nm==='confetti'){for(let i=0;i<n*1.5;i++){const x=R(i,1)*W+Math.sin(tt*2+i)*20,y=(R(i,2)*H+tt*(110+R(i,3)*90))%H;d.save();d.translate(x,y);d.rotate(tt*3+i);d.fillStyle='hsl('+(i*53%360)+',90%,60%)';d.fillRect(-5,-3,10,6);d.restore()}}
 else if(nm==='fireworks'){for(let b=0;b<3;b++){const q=tt*.7+b*.33,ph=q%1,cx=120+R(b,Math.floor(q))*400,cy=70+R(b,5)*120;d.strokeStyle='hsl('+(b*110+Math.floor(q)*40)+',95%,65%)';d.globalAlpha=1-ph;d.lineWidth=3;for(let i=0;i<14;i++){const a=i*.4488;d.beginPath();d.moveTo(cx+Math.cos(a)*ph*70,cy+Math.sin(a)*ph*70);d.lineTo(cx+Math.cos(a)*(ph*70+14),cy+Math.sin(a)*(ph*70+14));d.stroke()}}d.globalAlpha=1}
 else if(nm==='hearts'){d.fillStyle='rgba(255,120,160,.9)';for(let i=0;i<n/2;i++){const ph=(tt*.3+R(i,1))%1,x=R(i,2)*W+Math.sin(tt*2+i)*14,y=H-ph*(H+40);d.globalAlpha=1-ph*.7;heartP(d,x,y,10+R(i,3)*12);d.fill()}d.globalAlpha=1}
 else if(nm==='steam'){d.strokeStyle='rgba(235,240,250,.5)';d.lineWidth=6;for(let i=0;i<5;i++){const x=200+i*60,ph=(tt*.4+i*.2)%1;d.globalAlpha=1-ph;d.beginPath();d.moveTo(x,H-20-ph*40);for(let y=0;y<150;y+=15)d.lineTo(x+Math.sin(tt*2+y*.06+i)*10,H-60-ph*40-y);d.stroke()}d.globalAlpha=1}
 else if(nm==='balloons'){for(let i=0;i<n/6+2;i++){const ph=(tt*.12+R(i,1))%1,x=R(i,2)*W+Math.sin(tt+i)*16,y=H+40-ph*(H+120);d.fillStyle='hsl('+(i*67%360)+',80%,60%)';d.beginPath();d.ellipse(x,y,20,26,0,0,6.3);d.fill();d.strokeStyle='rgba(255,255,255,.6)';d.lineWidth=1.5;d.beginPath();d.moveTo(x,y+26);d.quadraticCurveTo(x+6,y+46,x,y+66);d.stroke()}}
 else if(nm==='leaves'){for(let i=0;i<n/2;i++){const x=R(i,1)*W+Math.sin(tt*1.4+i)*30,y=(R(i,2)*H+tt*(60+R(i,3)*40))%H;d.save();d.translate(x,y);d.rotate(tt*1.5+i);d.fillStyle='hsl('+(20+R(i,4)*30)+',80%,45%)';d.beginPath();d.ellipse(0,0,9,5,0,0,6.3);d.fill();d.restore()}}
 else if(nm==='zzz'){d.strokeStyle='rgba(200,210,255,.9)';d.lineWidth=4;for(let i=0;i<4;i++){const ph=(tt*.25+i*.25)%1,x=400+ph*50+Math.sin(ph*6)*8,y=150-ph*110,sz=10+ph*16;d.globalAlpha=Math.sin(ph*Math.PI);d.beginPath();d.moveTo(x-sz/2,y-sz/2);d.lineTo(x+sz/2,y-sz/2);d.lineTo(x-sz/2,y+sz/2);d.lineTo(x+sz/2,y+sz/2);d.stroke()}d.globalAlpha=1}
 d.restore()}

/* overlays: pick one, how strong, how long, Test and Clear; the preview shows it at once */
function overlayCard(id,off,why,face,titleKey){let name='rain',level='normal',secs=8;
 const pills=h('div',{class:'pills',role:'radiogroup','aria-label':T('pol.ov.pick')});
 const draw=()=>pills.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v===name)));
 for(const o of OVN)pills.append(h('button',{type:'button',class:'pill',role:'radio','data-v':o,onclick:()=>{name=o;draw();if(face)face.ov(name,level,secs)}},T('pol.ov.'+o)));draw();
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
 const upd=()=>face.set({fx:fx(),bubble:pv.values.speech_bubble,dots:pv.values.thinking_dots});upd();
 const feel=card(T('pol.feel.title'),T('pol.feel.help'),
  ptoggle(pv,put,'emotion_faces',T('pol.feel.emotion'),T('pol.feel.emotion_help')),
  ptoggle(pv,put,'speech_bubble',T('pol.feel.bubble'),T('pol.feel.bubble_help'),upd),
  ptoggle(pv,put,'thinking_dots',T('pol.feel.dots'),T('pol.feel.dots_help'),upd),comingNote(pv,'speech_bubble'));
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
 return{pv,cards:[feel,eff,packsCard,overlayCard(id,false,'',face)]}}

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
