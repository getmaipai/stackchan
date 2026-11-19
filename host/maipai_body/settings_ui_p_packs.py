# ruff: noqa: E501
"""The Packs page in the new dashboard look (docs/plan/settings-simplification.md; brief api36).

Placement: host dashboard. ``DETAIL['more/packs']`` is the front view: six rows, each opening a small view of its own
(``more/packs-languages``, ``-look``, ``-pictures``, ``-character``, ``-sounds``, ``-installed``). Each small view lists the
packs as rows with an Install or Remove action. The calls are the ones the old Packs builder, the Look page and the picture
section make (``packs`` and ``packs/activate``, ``faces`` with ``screen_lang``, ``pictures/*``, ``phrases``). This file is
appended to the page script by ``settings_ui_shell.page_modules``; it holds no Python logic."""

JS = r"""
/* ---- Packs (settings_ui_p_packs.py): the front view and six small views ---- */
{
const PK='/api/stackchan/packs';
const kb=b=>b>=1e6?(b/1e6).toFixed(1)+' MB':Math.max(1,Math.ceil(b/1000))+' KB';
const cap=s=>String(s).charAt(0).toUpperCase()+String(s).slice(1);
const warnCss='background:color-mix(in srgb,var(--warn) 16%,var(--grp))';
/* a small text button at the right end of a row (Install, Remove, Add) */
const btn=(label,fn,bad)=>{const b=h('button',{type:'button',style:'border:0;background:none;cursor:pointer;min-height:44px;padding:0 4px;font:500 17px/1 var(--font);color:'+(bad?'var(--bad,#ff3b30)':'var(--ac)'),onclick:async e=>{e.stopPropagation();if(b.disabled)return;b.disabled=true;try{await fn()}finally{b.disabled=false}}},label);return b};
const fail=(b,msg)=>b.append(h('p',{class:'empty2'},msg||T('net_error')));
const b64Of=async f=>{const a=new Uint8Array(await f.arrayBuffer());let s='';for(let i=0;i<a.length;i+=32768)s+=String.fromCharCode.apply(null,a.subarray(i,i+32768));return btoa(s)};
/* one read of what the old Packs builder read: the library, this robot's choices, the face values (language) */
const data=async()=>{const id=UNIT.device_id,[lr,ur,fv]=await Promise.all([api(PK),api(unitPath(id,'packs')),faceView(id)]);
 const lib=lr.ok?lr.d:{packs:[],types:[],used:0,capacity:1},ud=ur.ok?ur.d:{active:{},rows:{},unit_ready:false,unit:{}};
 return{id,lib,ud,fv,libOk:lr.ok,error:lr.ok?'':(lr.d.error||'')}};
const activeOf=(d,type)=>{const pid=(d.ud.active||{})[type];return pid?d.lib.packs.find(x=>x.id===pid):null};
const activate=async(d,type,pid)=>{const r=await save(unitPath(d.id,'packs/activate'),{type,pack_id:pid},true);if(r.ok)toast(pid?T('Installed'):T('Removed'));return r.ok};
/* a small view: back to Packs, a large title, then the body, drawn again after every action */
const sub=(v,title,build)=>{const hd=detailHead(title,'more');const back=hd[0].querySelector('.back');back.onclick=()=>nav('more','packs');back.lastChild.textContent=T('Packs');
 const body=h('div');add(v,...hd,body);
 const draw=async()=>{if(!UNIT){body.replaceChildren(need());return}
  try{const d=await data(),frag=h('div');if(!d.libOk&&!(d.fv&&d.fv.values))fail(frag,d.error);else await build(frag,d,draw);body.replaceChildren(...frag.childNodes)}
  catch(e){console.error(e);body.replaceChildren(h('p',{class:'empty2'},T('net_error')))}};
 return draw()};
/* the rows of one kind of pack: Install or Remove, by the same packs/activate call as the old selects */
const packRows=(d,type,again)=>{const act=(d.ud.active||{})[type]||'',list=d.lib.packs.filter(x=>x.type===type);
 return list.map(x=>{const on=act===x.id;return rowEl({label:x.name,value:kb(x.size)+(x.voice?' · '+x.voice:''),
  control:on?btn(T('Remove'),async()=>{if(await activate(d,type,''))again()},true):btn(T('Install'),async()=>{if(await activate(d,type,x.id))again()})})})};
const noneRow=text=>h('p',{class:'empty2'},text||T('No packs yet'));
const builtinRow=(d,type)=>rowEl({label:T('pol.packs.builtin'),value:(d.ud.active||{})[type]?'':T('In use')});

/* front view: six rows, each opens a small view */
DETAIL['more/packs']=async v=>{add(v,...detailHead(T('Packs'),'more'));if(!UNIT){add(v,need());return}
 const d=await data(),pr=await api(unitPath(d.id,'pictures')),pd=pr.ok&&pr.d.slots?pr.d:null;
 const lv=d.fv.values||{},look=activeOf(d,'look'),snd=activeOf(d,'sound'),n=Object.values(d.ud.active||{}).filter(Boolean).length;
 const imp=h('input',{type:'file',accept:'.maipack',hidden:true,'aria-label':T('Import a pack'),onchange:async e=>{const f=e.target.files[0];if(!f)return;const r=await save(PK+'/import',{b64:await b64Of(f)},true);e.target.value='';if(r.ok){toast(T('pol.packs.imported'));nav('more','packs')}}});
 add(v,grp(null,
  rowEl({label:T('Languages'),icon:'talk',value:lv.lang?(S['settings.lang.'+lv.lang]||lv.lang):'',go:()=>nav('more','packs-languages')}),
  rowEl({label:T('Look packs'),icon:'face',value:look?look.name:T('pol.packs.builtin'),go:()=>nav('more','packs-look')}),
  rowEl({label:T('Pictures'),icon:'cam',value:pd&&pd.frames?String(pd.frames):T('None'),go:()=>nav('more','packs-pictures')}),
  rowEl({label:T('Character pack'),icon:'people',go:()=>nav('more','packs-character')}),
  rowEl({label:T('Sounds'),icon:'vol',value:snd?snd.name:T('pol.packs.builtin'),go:()=>nav('more','packs-sounds')}),
  rowEl({label:T('Installed on the robot'),icon:'box',value:n?String(n):'',go:()=>nav('more','packs-installed')})),
  moreFold(rowEl({label:T('Import a pack'),icon:'plus',go:()=>imp.click()})),imp)};

/* Languages: the screen language; Install switches to it, Remove goes back to English */
DETAIL['more/packs-languages']=v=>sub(v,T('Languages'),async(b,d,again)=>{const fv=d.fv;if(!fv.values){fail(b,fv.error);return}
 const cur=fv.values.lang,unitLang=((d.ud.unit||{}).language||{}).lang||'';
 const set=async l=>{const r=await save(facePath(d.id),{screen_lang:l},true);if(r.ok){toast(l==='en'?T('Removed'):T('pol.lang.switched'));again()}};
 b.append(grp(null,...fv.choices.lang.map(l=>{const pk=d.lib.packs.find(x=>x.type==='language'&&x.lang===l),on=l===cur;
  const size=l==='en'?T('pol.lang.builtin'):(pk?kb(pk.size):T('pol.lang.nopack'));
  const st=on&&l!=='en'&&d.ud.unit_ready?(unitLang===l?T('pol.lang.on_robot'):T('pol.lang.sending')):'';
  return rowEl({label:S['settings.lang.'+l]||l,value:cap(size)+(st?' · '+st:''),control:on?(l==='en'?h('span',{class:'rv'},T('In use')):btn(T('Remove'),()=>set('en'),true)):btn(T('Install'),()=>set(l))})})),
  moreFold(rowEl({label:T('Accents on screen'),help:T('pol.lang.ascii')})))});

/* Look packs: more faces from the library */
DETAIL['more/packs-look']=v=>sub(v,T('Look packs'),async(b,d,again)=>{const rows=packRows(d,'look',again);
 b.append(grp(null,builtinRow(d,'look'),...rows));if(!rows.length)b.append(noneRow(T('pol.packs.none_look')));
 if(!d.ud.unit_ready)b.append(h('p',{class:'sub'},T('pol.st.noreach')))});

/* Pictures: one picture per expression (the calls of the old picture section) */
DETAIL['more/packs-pictures']=v=>sub(v,T('Pictures'),async(b,d,again)=>{const base=unitPath(d.id,'pictures'),r=await api(base);
 if(!r.ok||!r.d.slots){fail(b,r.d.error);return}const p=r.d;
 const post=async(a,body)=>{const x=await api(base+'/'+a,body||{});if(!x.ok){toast(x.d.error||T('net_error'),'bad');return null}if(x.d.message)toast(x.d.message);return x.d};
 const rgb=async file=>{const bmp=await createImageBitmap(file),c=document.createElement('canvas');c.width=640;c.height=480;const x=c.getContext('2d');x.fillStyle='#000';x.fillRect(0,0,640,480);
  const s=Math.max(640/bmp.width,480/bmp.height),w=bmp.width*s,hh=bmp.height*s;x.drawImage(bmp,(640-w)/2,(480-hh)/2,w,hh);const px=x.getImageData(0,0,640,480).data;let bin='';
  for(let i=0;i<px.length;i+=32768)bin+=String.fromCharCode.apply(null,px.subarray(i,i+32768));return btoa(bin)};
 const modes=sgRow(S['settings.pics.mode'],p.choices.mode.map(m=>({v:m,t:S['settings.pics.mode.'+m]})),p.mode,async m=>{const x=await post('options',{mode:m,fps:p.fps,overlay:p.overlay});if(x){again();return true}return false});
 const slots=p.slots.map(s=>{const name=S['settings.pics.slot.'+s.slot],max=p.limits.per_slot;
  const pick=h('input',{type:'file',accept:'image/*',multiple:p.mode==='sequence',hidden:true,'aria-label':S['settings.pics.add']+': '+name,onchange:async()=>{let at=s.frames,last=null;
   for(const file of Array.from(pick.files).slice(0,max-s.frames)){let b64;try{b64=await rgb(file)}catch(e){toast(S['settings.pics.unreadable'],'bad');return}
    const x=await post('add',{slot:s.slot,index:at,width:640,height:480,rgba_b64:b64});if(!x)return;last=x;at++}if(last){toast(T('Installed'));again()}}});
  const acts=h('span',{style:'display:inline-flex;align-items:center;gap:6px'},pick);
  if(s.frames<max)acts.append(btn(T('Install'),()=>pick.click()));
  if(s.frames>0)acts.append(btn(T('Remove'),async()=>{const x=await post('remove',{slot:s.slot});if(x){toast(T('Removed'));again()}},true));
  const thumb=s.thumbs.length?h('img',{src:s.thumbs[0],alt:name,style:'width:40px;height:30px;border-radius:4px;object-fit:cover;vertical-align:middle'}):null;
  return rowEl({label:name,value:thumb,control:acts})});
 add(b,p.problem?h('div',{class:'ok2',role:'alert',style:warnCss},p.problem):null,grp(null,modes),grp(null,...slots));
 if(p.ready)b.append(grp(null,rowEl({label:S['settings.pics.send'],icon:'check',go:async()=>{toast(S['settings.pics.sending']);const x=await post('send');if(x){toast(T('Sent'));again()}}})));
 const OV=[['lx','x'],['ly','y'],['rx','x'],['ry','y'],['eye_w','w'],['eye_h','h'],['mx','x'],['my','y'],['mouth_w','w'],['mouth_h','h']];
 const fold=[rowEl({label:S['settings.pics.used'],value:p.frames+' / '+p.limits.frames+' · '+kb(p.bytes)})];
 if(p.mode==='sequence')fold.push(slRow(S['settings.pics.fps'],p.limits.fps[0],p.limits.fps[1],1,p.fps,x=>String(x),async x=>{const y=await post('options',{mode:p.mode,fps:x});if(y)toast(S['settings.saved'])}));
 if(p.mode==='overlay'){const ovin={},send=async()=>{const o={};for(const[k]of OV)o[k]=parseInt(ovin[k].value,10);o.color=ovin.color.value;const y=await post('options',{mode:p.mode,fps:p.fps,overlay:o});if(y)toast(S['settings.saved'])};
  for(const[k]of OV){ovin[k]=h('input',{class:'tx',type:'number',value:p.overlay[k],'aria-label':pretty(k),onchange:send});fold.push(rowEl({label:pretty(k),control:ovin[k]}))}
  ovin.color=h('input',{type:'color',value:p.overlay.color,'aria-label':S['settings.pics.color'],onchange:send});fold.push(rowEl({label:S['settings.pics.color'],control:ovin.color}))}
 fold.push(rowEl({label:S['settings.pics.clear'],go:async()=>{if(!(await ask(S['settings.pics.clear_ask'],S['settings.pics.clear'])))return;const x=await post('clear');if(x){toast(T('Removed'));again()}}}));
 b.append(moreFold(...fold))});

/* Character pack: choose a shared character pack (.zip); the host checks it and installs it as the picture face */
DETAIL['more/packs-character']=v=>sub(v,T('Character pack'),async(b,d,again)=>{const out=h('div',{role:'status','aria-live':'polite'});
 const inp=h('input',{type:'file',accept:'.zip,application/zip',hidden:true,'aria-label':T('char.choose'),onchange:async e=>{const f=e.target.files&&e.target.files[0];e.target.value='';if(!f)return;
  const bad=lines=>out.replaceChildren(h('div',{class:'ok2',role:'alert',style:warnCss},h('div',{},h('b',{},T('char.problems')),...lines.map(x=>h('div',{},x)))));
  if(f.size>8*1024*1024){bad([T('char.too_big')]);return}
  out.replaceChildren(h('p',{class:'sub'},T('char.checking')));
  let b64;try{b64=await b64Of(f)}catch(x){bad([T('char.unreadable')]);return}
  const r=await api(unitPath(d.id,'pictures/import-character'),{b64});
  if(!r.ok){bad(r.d.problems||[r.d.error||T('net_error')]);return}
  toast(T('char.done'));
  out.replaceChildren(h('div',{class:'ok2'},SVG(IC.check),T('char.done')),grp(null,rowEl({label:S['settings.pics.send'],icon:'check',go:async()=>{toast(S['settings.pics.sending']);const x=await api(unitPath(d.id,'pictures/send'),{});if(x.ok)toast(T('Sent'));else toast(x.d.error||T('net_error'),'bad')}})))}});
 b.append(grp(null,rowEl({label:T('Choose a file'),icon:'people',value:'.zip',go:()=>inp.click()})),inp,out)});

/* Sounds: sound packs, thinking sounds and the offline phrases */
DETAIL['more/packs-sounds']=v=>sub(v,T('Sounds'),async(b,d,again)=>{
 const group=(title,type)=>{const rows=packRows(d,type,again);b.append(grp(title,builtinRow(d,type),...rows));if(!rows.length)b.append(noneRow())};
 group(T('pol.type.sound'),'sound');group(T('pol.type.filler'),'filler');group(T('pol.type.phrase'),'phrase');
 const pr=await api(unitPath(d.id,'phrases'));
 if(pr.ok&&pr.d.can_make){const pd=pr.d,lv=d.fv.values||{lang:'en'},plang=(pd.languages||['en']).includes(lv.lang)?lv.lang:'en',val=h('span',{});
  const poll=async()=>{const x=await api(unitPath(d.id,'phrases'));if(!x.ok)return;const s=x.d.status||{};
   if(s.running){val.textContent=s.done+'/'+s.total;setTimeout(poll,900)}else{if(s.error)toast(s.error,'bad');else toast(T('pol.phr.made'));again()}};
  b.append(grp(null,rowEl({label:T('Make phrases'),icon:'talk',value:val,go:async()=>{if(val.textContent)return;val.textContent='...';const r=await save(unitPath(d.id,'phrases/generate'),{voice:'default',for_lang:plang},true);if(!r.ok){val.textContent='';return}poll()}})))}});

/* Installed on the robot: what each kind of pack is set to, and the library behind it (in the fold) */
DETAIL['more/packs-installed']=v=>sub(v,T('Installed on the robot'),async(b,d,again)=>{const ud=d.ud,rowsOf=ud.rows||{},act=ud.active||{};
 const types=['look','language','filler','phrase','sound','dance','game'].filter(t=>act[t]||d.lib.packs.some(x=>x.type===t));
 const word=t=>{const r=rowsOf[t]||{};if(!ud.unit_ready||!act[t])return'';return r.in_sync?T('pol.st.synced'):T('Waiting to send')};
 const rows=types.map(t=>{const p=activeOf(d,t),w=word(t);
  return rowEl({label:T('pol.type.'+t),value:(p?p.name:T('pol.packs.builtin'))+(w?' · '+w:''),control:p?btn(T('Remove'),async()=>{if(await activate(d,t,''))again()},true):null})});
 b.append(grp(null,...rows));if(!rows.length)b.append(noneRow());
 if(ud.unit_ready)b.append(grp(null,rowEl({label:T('pol.packs.send_now'),icon:'check',go:async()=>{const r=await save(unitPath(d.id,'packs/sync'),{},true);if(r.ok){toast(T('pol.packs.sent_now'));again()}else toast(r.d.error||T('net_error'),'bad')}})));
 else b.append(h('p',{class:'sub'},T('pol.st.noreach')));
 const lib=d.lib,fold=[rowEl({label:T('Library'),value:T('pol.packs.used').replace('{used}',kb(lib.used)).replace('{cap}',kb(lib.capacity))})];
 for(const x of lib.packs){fold.push(rowEl({label:x.name,value:T('pol.type.'+x.type)+' · '+kb(x.size)+(x.signed?' · '+T('pol.packs.signed'):''),control:h('span',{style:'display:inline-flex;align-items:center;gap:6px'},
  btn(T('pol.packs.export'),async()=>{const r=await save(PK+'/export',{pack_id:x.id},true);if(!r.ok)return;const a=h('a',{href:'data:application/octet-stream;base64,'+r.d.b64,download:r.d.filename});document.body.append(a);a.click();a.remove();toast(T('Exported'))}),
  btn(T('pol.packs.delete'),async()=>{if(!(await ask(T('pol.packs.delete_ask').replace('{name}',x.name),T('pol.packs.delete'))))return;const r=await save(PK+'/delete',{pack_id:x.id},true);if(r.ok){toast(T('Removed'));again()}},true))}))}
 b.append(moreFold(...fold))});
}
"""
