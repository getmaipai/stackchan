# ruff: noqa: E501
"""The wake word maker card, added to the Voice page. It appears only when the host answers that the package is on
(`/api/stackchan/wakeword`). Clips are recorded in the browser as 16-bit 16 kHz mono WAV and sent to the host; the page keeps nothing."""

JS_WAKEMAKER = r"""
/* ---- voice: make your own wake word (optional package) ---- */
{const prevVoice=BUILDERS.voice;BUILDERS.voice=async(p,u)=>{await prevVoice(p,u);
 const first=await api('/api/stackchan/wakeword');if(!first.ok||!first.d.enabled)return;
 const fmt=(k,v)=>T(k).replace(/\{(\w)\}/g,(m,c)=>v[c]);
 const name=h('input',{type:'text',value:'',maxlength:32,'aria-label':T('ww.name'),placeholder:T('ww.name')});
 const info=h('p',{class:'hint',role:'status','aria-live':'polite'}),out=h('p',{class:'hint'});
 const w=()=>name.value.trim().toLowerCase();
 const draw=async()=>{const word=w(),r=word?await api('/api/stackchan/wakeword/'+encodeURIComponent(word)):first;const d=r.ok?r.d:first.d;const c=d.counts||{positive:0,negative:0};
  info.textContent=fmt('ww.counts',{w:c.positive,o:c.negative,n:d.need});
  const s=d.status||{};out.textContent=(s.message||'')+(s.result?' '+T('ww.result')+JSON.stringify(s.result):'')+(d.installed?' '+fmt('ww.installed',{w:d.installed.word}):'')};
 async function record(kind){
  if(!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia)){toast(T('ww.no_mic'),'bad');return}
  info.textContent=T('ww.recording');
  let stream;try{stream=await navigator.mediaDevices.getUserMedia({audio:true})}catch(e){toast(T('ww.no_mic'),'bad');return}
  const ctx=new (window.AudioContext||window.webkitAudioContext)(),src=ctx.createMediaStreamSource(stream),proc=ctx.createScriptProcessor(4096,1,1),chunks=[];
  proc.onaudioprocess=e=>chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));src.connect(proc);proc.connect(ctx.destination);
  await new Promise(r=>setTimeout(r,1100));proc.disconnect();src.disconnect();stream.getTracks().forEach(t=>t.stop());const rate=ctx.sampleRate;ctx.close();
  const all=new Float32Array(chunks.reduce((n,c)=>n+c.length,0));let o=0;for(const c of chunks){all.set(c,o);o+=c.length}
  const n=16000,pcm=new Int16Array(n);for(let i=0;i<n;i++){const x=all[Math.min(all.length-1,Math.floor(i*rate/16000))]||0;pcm[i]=Math.max(-1,Math.min(1,x))*32767}
  const buf=new ArrayBuffer(44+pcm.length*2),v=new DataView(buf),W=(a,s)=>{for(let i=0;i<s.length;i++)v.setUint8(a+i,s.charCodeAt(i))};
  W(0,'RIFF');v.setUint32(4,36+pcm.length*2,true);W(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);W(36,'data');v.setUint32(40,pcm.length*2,true);
  new Int16Array(buf,44).set(pcm);let bin='';const bytes=new Uint8Array(buf);for(let i=0;i<bytes.length;i+=0x8000)bin+=String.fromCharCode(...bytes.subarray(i,i+0x8000));
  const r=await api('/api/stackchan/wakeword/clip',{word:w(),kind,wav_b64:btoa(bin)});if(!r.ok)toast(r.d.error||T('ww.error'),'bad');await draw()}
 const post=async(a)=>{const r=await api('/api/stackchan/wakeword/'+a,{word:w()});if(!r.ok)toast(r.d.error||T('ww.error'),'bad');await draw();return r};
 const btn=(label,fn)=>h('button',{class:'btn',type:'button',onclick:fn},label);
 const poll=async()=>{await draw();const r=await api('/api/stackchan/wakeword/'+encodeURIComponent(w()));if(r.ok&&r.d.status&&r.d.status.state==='running')setTimeout(poll,1500)};
 p.append(card(T('ww.title'),T('ww.help'),h('div',{class:'stack'},name,h('div',{class:'btns'},btn(T('ww.rec_word'),()=>record('positive')),btn(T('ww.rec_other'),()=>record('negative'))),info,h('div',{class:'btns'},btn(T('ww.train'),async()=>{await post('train');poll()}),btn(T('ww.install'),()=>post('install')),btn(T('ww.clear'),()=>post('clear'))),out)));
 await draw()}}
"""
