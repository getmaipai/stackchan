# ruff: noqa: E501
"""The Brain page and the first-run page (the same page; ``?first=1`` adds the welcome line): two routes (hosted, custom) and, under custom, three ways to get a brain.

A small self-contained page served by the settings server at /brain. English only for now, like the other pages the translators have not reached."""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Choose a brain</title>
<style>
:root{--bg:#fff;--fg:#17202a;--muted:#566573;--card:#f4f6f8;--accent:#0b6bcb;--good:#1e7a46;--bad:#b3261e;--line:#d5dbe1}
@media (prefers-color-scheme:dark){:root{--bg:#101418;--fg:#eaeef2;--muted:#a0abb6;--card:#1a2027;--accent:#6cb2ff;--good:#5fd08b;--bad:#ff8a80;--line:#2c3640}}
body{margin:0;background:var(--bg);color:var(--fg);font:18px/1.5 system-ui,sans-serif}
main{max-width:44rem;margin:0 auto;padding:1rem 16px 3rem}
h1{font-size:1.6rem;margin:.4rem 0}h2{font-size:1.2rem;margin:.2rem 0}
.card{background:var(--card);border-radius:12px;padding:1rem;margin:1rem 0;border:2px solid transparent}.card.on{border-color:var(--accent)}
label{display:block;margin:.6rem 0 .1rem;font-weight:600}input,select{font:inherit;width:100%;box-sizing:border-box;padding:.5rem;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg)}
button{font:inherit;font-weight:600;min-height:44px;padding:0 1.1rem;border-radius:10px;border:0;background:var(--accent);color:#fff;cursor:pointer;margin:.5rem .5rem 0 0}button.plain{background:transparent;color:var(--accent);border:1px solid var(--accent)}button:disabled{opacity:.5}
.muted{color:var(--muted);font-size:.9rem}.good{color:var(--good)}.bad{color:var(--bad)}progress{width:100%;height:1rem}.row{display:flex;gap:.6rem;align-items:end}.row>div{flex:1}
.routes{display:grid;grid-template-columns:15rem 1fr;gap:1rem}.tabs{display:flex;flex-direction:column;gap:.5rem}.tab{display:block;text-align:left;background:var(--card);color:var(--fg);border:2px solid transparent;margin:0;padding:.6rem .8rem;min-height:44px;line-height:1.3}.tab.on{border-color:var(--accent)}.tab small{display:block;font-weight:400;color:var(--muted)}
@media (max-width:640px){.routes{grid-template-columns:1fr}.tabs{flex-direction:row}.tab{flex:1}}
</style></head><body><main>
<h1>Choose a brain</h1>
<p id="welcome" class="muted" hidden>Welcome. The robot needs a brain to think and talk. Pick a route, then one way on it. You can change it later on this page.</p>
<p id="now" role="status" aria-live="polite"></p>

<div class="routes"><nav class="tabs" aria-label="Brain route">
<button class="tab" id="t_hosted" type="button" data-route="hosted">Hosted by M5Stack/Xiaozhi<small>Your voice goes to their servers, outside your home.</small></button>
<button class="tab" id="t_custom" type="button" data-route="custom">Custom<small>Your voice stays where you point it.</small></button></nav>
<div class="pane">
<section class="card" id="r_hosted" hidden><h2>Hosted by M5Stack/Xiaozhi</h2>
<p>Your voice goes to M5Stack/Xiaozhi's servers, outside your home. They run the model, the listening and the speaking.</p>
<p class="muted" id="hosted_plan">Planned. It opens once a test build shows their server accepts this firmware. Until then, use Custom.</p>
<button id="save_hosted" type="button">Use the hosted route</button><p id="m_hosted" role="status"></p></section>
<div id="r_custom" hidden>
<p class="muted">Custom: your voice stays where you point it. Pick one of the three ways below: your own key or server, your own host or MaiPai Home, or a model on your computer.</p>
<section class="card" id="c_home"><h2>1. MaiPai Home</h2>
<p class="muted">Use a MaiPai Home hub on your network. Home keeps the household, the voices and the rules. You pair the robot with it after you save.</p>
<label for="home_url">Home's address</label><input id="home_url" placeholder="http://192.0.2.10:8000" inputmode="url">
<button id="save_home" type="button">Use MaiPai Home</button><p id="m_home" role="status"></p></section>

<section class="card" id="c_own"><h2>2. Your own stack</h2>
<p class="muted">Use a language model, a speech-to-text server and a text-to-speech server you already run. Each has a test button.</p>
<label for="llm_url">Language model address (the part before /v1)</label><div class="row"><div><input id="llm_url" placeholder="http://192.0.2.10:8080" inputmode="url"></div><button class="plain" type="button" data-test="model">Test</button></div><p id="t_model" role="status" class="muted"></p>
<label for="model">Model name</label><input id="model" placeholder="the name your server uses">
<label for="stt_url">Speech to text address</label><div class="row"><div><input id="stt_url" placeholder="http://192.0.2.10:9000" inputmode="url"></div><button class="plain" type="button" data-test="stt">Test</button></div><p id="t_stt" role="status" class="muted"></p>
<label for="tts_url">Text to speech address</label><div class="row"><div><input id="tts_url" placeholder="http://192.0.2.10:9001" inputmode="url"></div><button class="plain" type="button" data-test="tts">Test</button></div><p id="t_tts" role="status" class="muted"></p>
<label for="api_key_env">Name of the variable that holds the key (optional)</label><input id="api_key_env" placeholder="MY_MODEL_KEY">
<button id="save_own" type="button">Use my own stack</button><p id="m_own" role="status"></p></section>

<section class="card" id="c_local"><h2>3. A small stack on this computer</h2>
<p class="muted">The host downloads a small language model, a speech-to-text model and a text-to-speech voice and runs them here. After the download nothing leaves this computer. It is slower and simpler than the other two ways.</p>
<div id="needs" class="muted"></div>
<label for="choice">Model size</label><select id="choice"></select>
<button id="install" type="button">Install</button><button id="stop" class="plain" type="button" hidden>Stop</button><button id="remove" class="plain" type="button" hidden>Remove it</button>
<progress id="bar" max="100" value="0" hidden aria-label="Install progress"></progress><p id="m_local" role="status" aria-live="polite"></p></section>
</div></div></div>
</main>
<script>
const $=id=>document.getElementById(id);
const api=async(path,body)=>{try{const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return {ok:r.ok,d:await r.json()}}catch(e){return {ok:false,d:{error:'The host did not answer. Check that it is running, then reload this page.'}}}};
const say=(id,text,cls)=>{const e=$(id);e.textContent=text||'';e.className=cls||''};
const MB=n=>Math.round(n/1e6)+' MB',GB=n=>(n/1e9).toFixed(1)+' GB';
let polling=false;
let ROUTE=null;
function showRoute(r){ROUTE=r;for(const k of ['hosted','custom']){$('r_'+k).hidden=k!==r;$('t_'+k).classList.toggle('on',k===r)}}
document.querySelectorAll('[data-route]').forEach(b=>b.addEventListener('click',()=>showRoute(b.dataset.route)));
$('save_hosted').addEventListener('click',async()=>{const r=await api('/api/stackchan/brain/apply',{mode:'hosted'});say('m_hosted',r.d.message||r.d.error,r.d.ok?'good':'bad');load()});
async function load(){const r=await api('/api/stackchan/brain');if(!r.ok){say('now',r.d.error||'The page could not load.','bad');return}
 const d=r.d,names={none:'No brain is set yet.',home:'Now: MaiPai Home.',own:'Now: your own stack.',local:'Now: the small stack on this computer.'};
 say('now',(d.problem||names[d.mode]));for(const m of ['home','own','local'])$('c_'+m).classList.toggle('on',d.mode===m);
 $('hosted_plan').hidden=!!d.hosted_proven;$('save_hosted').disabled=!d.hosted_proven;if(ROUTE===null)showRoute(d.route);
 for(const k of ['hosted','custom'])$('t_'+k).title=d.voice_line[k];
 $('welcome').hidden=!(new URL(document.URL).searchParams.get('first')&&d.mode==='none');
 for(const k of ['home_url','llm_url','model','stt_url','tts_url','api_key_env'])if(!$(k).value&&d[k])$(k).value=d[k];
 const o=d.overview||{},i=d.install||{};
 if(!o.supported){say('needs',o.message||'');$('install').disabled=true}else{
  const sel=$('choice');if(!sel.options.length)for(const [k,v] of Object.entries(o.options)){sel.add(new Option(v.label+(k===o.recommended?' (recommended)':''),k));}
  if(!sel.dataset.set){sel.value=o.recommended;sel.dataset.set='1'}
  const v=o.options[sel.value];say('needs','Download about '+MB(v.download_bytes)+', disk about '+MB(v.disk_bytes)+' in '+o.folder+' ('+MB(o.free_disk_bytes)+' free), memory about '+v.memory_mb+' MB'+(o.memory_mb?' ('+MB(o.memory_mb*1e6)+' here)':'')+'. It contacts '+v.addresses.join(' and ')+' to download. Nothing else.');}
 const busy=['downloading','unpacking','testing'].includes(i.state);
 $('install').disabled=busy||!o.supported;$('stop').hidden=!busy;$('remove').hidden=!(i.state==='ready'||o.installed);
 $('bar').hidden=!busy;$('bar').value=i.percent||0;say('m_local',i.message||'',i.state==='failed'?'bad':(i.state==='ready'?'good':''));
 if(busy&&!polling){polling=true;setTimeout(()=>{polling=false;load()},1000)}}
$('choice').addEventListener('change',()=>load());
document.querySelectorAll('[data-test]').forEach(b=>b.addEventListener('click',async()=>{const k=b.dataset.test,url=$(k==='model'?'llm_url':k+'_url').value;say('t_'+k,'Testing...');const r=await api('/api/stackchan/brain/test',{kind:k,url,model:$('model').value});say('t_'+k,r.d.message||r.d.error,r.d.ok?'good':'bad')}));
$('save_home').addEventListener('click',async()=>{const r=await api('/api/stackchan/brain/apply',{mode:'home',url:$('home_url').value});say('m_home',(r.d.message||r.d.error)+(r.d.note?' '+r.d.note:''),r.d.ok?'good':'bad');load()});
$('save_own').addEventListener('click',async()=>{const r=await api('/api/stackchan/brain/apply',{mode:'own',llm_url:$('llm_url').value,model:$('model').value,stt_url:$('stt_url').value,tts_url:$('tts_url').value,api_key_env:$('api_key_env').value});say('m_own',(r.d.message||r.d.error)+(r.d.note?' '+r.d.note:''),r.d.ok?'good':'bad');load()});
$('install').addEventListener('click',async()=>{const r=await api('/api/stackchan/brain/install',{choice:$('choice').value});if(!r.d.ok)say('m_local',r.d.error,'bad');load()});
$('stop').addEventListener('click',async()=>{await api('/api/stackchan/brain/stop',{});load()});
$('remove').addEventListener('click',async()=>{if(!confirm('Remove the small stack and its downloaded files?'))return;await api('/api/stackchan/brain/remove',{});load()});
load();
</script></body></html>
"""


def render_brain_page() -> bytes:
    from maipai_body.dashboard_shell import apply

    return apply(PAGE, "brain").encode("utf-8")
