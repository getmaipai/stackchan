# ruff: noqa: E501
"""The Voice and listening page in the dashboard look: five visible rows, the rest in the fold, and the optional wake word maker on its own view."""

JS = r"""
/* ---- Voice and listening (settings_ui_p_voice.py) ---- */
DETAIL['robot/voice']=async v=>{add(v,...detailHead(T('Voice and listening'),'robot'));
 const id=UNIT.device_id,c=await cx(),fv=c.fv||{},vals=fv.values||{lang:'en'};
 const put=async body=>{const r=await unitSet(id,body);if(r.ok)Object.assign(UNIT,body);return r.ok};
 const ww=await api('/api/stackchan/wakeword'),hasMaker=!!(ww.ok&&ww.d.enabled);
 const lang=h('select',{'aria-label':T('Language'),style:'border:0;background:none;color:var(--fg);font:inherit;text-align:right;max-width:60%',onchange:async e=>{const old=vals.lang;const r=await save(facePath(id),{screen_lang:e.target.value});if(r.ok)vals.lang=e.target.value;else e.target.value=old}});
 for(const l of (fv.choices&&fv.choices.lang?fv.choices.lang:LANGS_ALL))lang.append(h('option',{value:l,selected:l===vals.lang},S['settings.lang.'+l]||l));
 const pv=await prefsView(id),pput=prefSaver(id,pv);
 add(v,grp(null,
  slRow(T('Speaking speed'),.75,1.5,.05,UNIT.speech_speed||1,x=>x.toFixed(2)+'x',x=>put({speech_speed:x}),{icon:'talk'}),
  sgRow(T('Wait after you stop'),[{v:'quick',t:T('Quick')},{v:'normal',t:T('Normal')},{v:'patient',t:T('Patient')}],UNIT.wait_after_talking||'quick',m=>put({wait_after_talking:m})),
  sgRow(T('Ignore noise'),[{v:'low',t:T('Low')},{v:'medium',t:T('Medium')},{v:'high',t:T('High')}],UNIT.ignore_noise||'medium',m=>put({ignore_noise:m})),
  rowEl({label:T('Language'),icon:'talk',control:lang}),
  hasMaker?rowEl({label:T('Wake word'),icon:'mic',value:ww.d.installed?ww.d.installed.word:'',go:()=>nav('robot','wakeword')}):null),
  moreFold(
   slRow(T('Voice pitch'),-12,12,1,UNIT.speech_pitch||0,x=>(x>0?'+':'')+x,x=>put({speech_pitch:x})),
   slRow(T('Volume limit'),0,100,5,UNIT.volume_cap==null?100:UNIT.volume_cap,x=>x+'%',x=>put({volume_cap:x})),
   sgRow(T('Listening sound'),['off','chime','mm'].map(o=>({v:o,t:T('pol.listen_sound.'+o)})),pv.values.listen_sound||'chime',m=>pput({listen_sound:m})),
   sgRow(T('Listening light'),['off','dim','normal'].map(o=>({v:o,t:T('pol.listen_light.'+o)})),pv.values.listen_light||'normal',m=>pput({listen_light:m})),
   swRow(T('Show listening on screen'),pv.values.listen_face,on=>pput({listen_face:on}),{help:T('pol.listen.face_help')}),
   rowEl({label:T('All voice settings'),go:()=>nav('robot','voice-more')})))};
DETAIL['robot/voice-more']=legacyView('voice',T('All voice settings'),'robot');
/* the wake word maker (only when the host package is on) */
DETAIL['robot/wakeword']=async v=>{add(v,...detailHead(T('Wake word'),'robot'));
 const first=await api('/api/stackchan/wakeword');if(!first.ok||!first.d.enabled){add(v,h('p',{class:'empty2'},T('Make your own wake word')+': '+T('Off')));return}
 const fmt=(k,o)=>T(k).replace(/\{(\w)\}/g,(m,x)=>o[x]);
 const name=h('input',{class:'tx',type:'text',value:'',maxlength:32,'aria-label':T('ww.name'),placeholder:T('ww.name')});
 const info=h('p',{class:'sub',role:'status','aria-live':'polite'}),out=h('p',{class:'sub'});
 const w=()=>name.value.trim().toLowerCase();
 const draw=async()=>{const word=w(),r=word?await api('/api/stackchan/wakeword/'+encodeURIComponent(word)):first;const d=r.ok?r.d:first.d;const k=d.counts||{positive:0,negative:0};
  info.textContent=fmt('ww.counts',{w:k.positive,o:k.negative,n:d.need});const s=d.status||{};out.textContent=(s.message||'')+(d.installed?' '+fmt('ww.installed',{w:d.installed.word}):'')};
 async function record(kind){
  if(!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia)){toast(T('ww.no_mic'),'bad');return}
  if(!w()){toast(T('ww.name'),'bad');return}
  info.textContent=T('ww.recording');toast(T('ww.recording'));
  let stream;try{stream=await navigator.mediaDevices.getUserMedia({audio:true})}catch(e){toast(T('ww.no_mic'),'bad');return}
  const ctx=new (window.AudioContext||window.webkitAudioContext)(),src=ctx.createMediaStreamSource(stream),proc=ctx.createScriptProcessor(4096,1,1),chunks=[];
  proc.onaudioprocess=e=>chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));src.connect(proc);proc.connect(ctx.destination);
  await new Promise(r=>setTimeout(r,1100));proc.disconnect();src.disconnect();stream.getTracks().forEach(t=>t.stop());const rate=ctx.sampleRate;ctx.close();
  const all=new Float32Array(chunks.reduce((n,c)=>n+c.length,0));let o=0;for(const c of chunks){all.set(c,o);o+=c.length}
  const n=16000,pcm=new Int16Array(n);for(let i=0;i<n;i++){const x=all[Math.min(all.length-1,Math.floor(i*rate/16000))]||0;pcm[i]=Math.max(-1,Math.min(1,x))*32767}
  const buf=new ArrayBuffer(44+pcm.length*2),dv=new DataView(buf),W=(a,s)=>{for(let i=0;i<s.length;i++)dv.setUint8(a+i,s.charCodeAt(i))};
  W(0,'RIFF');dv.setUint32(4,36+pcm.length*2,true);W(8,'WAVEfmt ');dv.setUint32(16,16,true);dv.setUint16(20,1,true);dv.setUint16(22,1,true);dv.setUint32(24,16000,true);dv.setUint32(28,32000,true);dv.setUint16(32,2,true);dv.setUint16(34,16,true);W(36,'data');dv.setUint32(40,pcm.length*2,true);
  new Int16Array(buf,44).set(pcm);let bin='';const bytes=new Uint8Array(buf);for(let i=0;i<bytes.length;i+=0x8000)bin+=String.fromCharCode(...bytes.subarray(i,i+0x8000));
  const r=await api('/api/stackchan/wakeword/clip',{word:w(),kind,wav_b64:btoa(bin)});if(!r.ok)toast(r.d.error||T('ww.error'),'bad');else toast(T('Saved'));await draw()}
 const post=async a=>{const r=await api('/api/stackchan/wakeword/'+a,{word:w()});if(!r.ok)toast(r.d.error||T('ww.error'),'bad');else toast(T('Saved'));await draw();return r};
 const poll=async()=>{await draw();const r=await api('/api/stackchan/wakeword/'+encodeURIComponent(w()));if(r.ok&&r.d.status&&r.d.status.state==='running')setTimeout(poll,1500)};
 add(v,grp(null,rowEl({label:T('Wake word'),icon:'mic',control:name}),
   rowEl({label:T('ww.rec_word'),icon:'mic',go:()=>record('positive')}),
   rowEl({label:T('ww.rec_other'),icon:'talk',go:()=>record('negative')}),
   rowEl({label:T('ww.train'),icon:'gear',go:async()=>{await post('train');poll()}}),
   rowEl({label:T('ww.install'),icon:'check',go:()=>post('install')})),
  info,out,moreFold(rowEl({label:T('ww.clear'),go:()=>post('clear')}),h('p',{class:'rh'},T('ww.help'))));
 await draw()};
"""
