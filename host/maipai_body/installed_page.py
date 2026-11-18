# ruff: noqa: E501
"""The dashboard page 'On my robot': per robot, what is installed, what the robot can hold, and an Automatic default with an Edit for people who want it."""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>On my robot</title>
<style>
:root{--bg:#fff;--fg:#17202a;--muted:#566573;--card:#f4f6f8;--accent:#0b6bcb;--good:#1e7a46;--bad:#b3261e;--warn:#9a6700;--line:#d5dbe1}
@media (prefers-color-scheme:dark){:root{--bg:#101418;--fg:#eaeef2;--muted:#a0abb6;--card:#1a2027;--accent:#6cb2ff;--good:#5fd08b;--bad:#ff8a80;--warn:#f0c36a;--line:#2c3640}}
body{margin:0;background:var(--bg);color:var(--fg);font:18px/1.5 system-ui,sans-serif}main{max-width:46rem;margin:0 auto;padding:1rem 16px 3rem}
h1{font-size:1.6rem;margin:.4rem 0}h2{font-size:1.15rem;margin:.2rem 0}.card{background:var(--card);border-radius:12px;padding:1rem;margin:1rem 0}
label.item{display:flex;gap:.6rem;align-items:center;padding:.4rem 0;border-top:1px solid var(--line)}label.item input{width:1.3rem;height:1.3rem}
button{font:inherit;font-weight:600;min-height:44px;padding:0 1.1rem;border-radius:10px;border:0;background:var(--accent);color:#fff;cursor:pointer;margin:.5rem .5rem 0 0}button.plain{background:transparent;color:var(--accent);border:1px solid var(--accent)}
select{font:inherit;padding:.4rem;border-radius:8px}.muted{color:var(--muted);font-size:.9rem}.good{color:var(--good)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.meter{height:.9rem;background:var(--line);border-radius:6px;overflow:hidden}.meter>div{height:100%;background:var(--accent)}
</style></head><body><main>
<h1>On my robot</h1>
<p><label>Robot <select id="unit"></select></label></p>
<p id="summary" role="status" aria-live="polite"></p>
<div class="meter" aria-hidden="true"><div id="bar" style="width:0"></div></div><p id="meter" class="muted"></p>
<p id="mode"></p>
<div id="kinds"></div>
<script>
const $=id=>document.getElementById(id),api=async(p,b)=>{try{const r=await fetch(p,b===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return {ok:r.ok,d:await r.json()}}catch(e){return {ok:false,d:{error:'The host did not answer. Reload this page.'}}}};
const KB=n=>Math.round(n/1000)+' KB';let editing=false,chosen={},view=null,timer=null;
async function units(){const r=await api('/api/stackchan/installed');const s=$('unit');for(const u of (r.d.units||[]))s.add(new Option((u.name||u.id)+(u.connected?'':' (away)'),u.id));
 const q=new URL(document.URL).searchParams.get('unit');if(q)s.value=q;if(!s.options.length){$('summary').textContent='No robot is paired yet. Pair one first.';return}load()}
async function load(){clearTimeout(timer);const id=$('unit').value;const r=await api('/api/stackchan/installed/'+encodeURIComponent(id));if(!r.ok){$('summary').textContent=r.d.error||'The page could not load.';$('summary').className='bad';return}
 view=r.d;if(!editing)chosen=Object.fromEntries(Object.entries(view.kinds).map(([k,v])=>[k,v.chosen.map(c=>c.id)]));draw();
 if(view.kinds&&Object.values(view.kinds).some(k=>k.chosen.some(c=>['waiting','installing'].includes(c.state))))timer=setTimeout(load,3000)}
function draw(){const v=view;$('summary').textContent=(v.warnings[0]||v.summary);$('summary').className=v.warnings.length?'warn':(v.summary.startsWith('The robot has')?'good':'');
 $('bar').style.width=v.meter.percent+'%';$('meter').textContent='Memory used on the robot by your choices: '+KB(v.meter.used_bytes)+' of '+KB(v.meter.budget_bytes);
 const m=$('mode');m.replaceChildren();
 if(!editing){m.append(Object.assign(document.createElement('span'),{textContent:v.mode==='automatic'?'Automatic: we choose for you (your language, a default face, a starter set of games). ':'You chose these yourself. '}));
  const e=Object.assign(document.createElement('button'),{className:'plain',textContent:'Edit',onclick:()=>{editing=true;draw()}});m.append(e);
  if(v.mode!=='automatic')m.append(Object.assign(document.createElement('button'),{className:'plain',textContent:'Back to Automatic',onclick:async()=>{await api('/api/stackchan/installed/'+encodeURIComponent($('unit').value)+'/choose',{mode:'automatic'});editing=false;load()}}))}
 const box=$('kinds');box.replaceChildren();
 for(const [kind,k] of Object.entries(v.kinds)){if(!k.catalog.length&&!k.chosen.length)continue;
  const c=document.createElement('section');c.className='card';c.append(Object.assign(document.createElement('h2'),{textContent:k.label+' ('+(editing?(chosen[kind]||[]).length:k.used)+' of '+k.slots+')'}));
  const rows=editing?k.catalog:k.chosen.map(x=>({id:x.id,name:x.name,size:x.size,state:x.state,message:x.message}));
  for(const it of rows){const l=document.createElement('label');l.className='item';
   if(editing){const cb=Object.assign(document.createElement('input'),{type:'checkbox',checked:(chosen[kind]||[]).includes(it.id)});cb.onchange=()=>{const a=chosen[kind]||[];chosen[kind]=cb.checked?[...a,it.id]:a.filter(x=>x!==it.id);if((chosen[kind]||[]).length>k.slots){chosen[kind].pop();cb.checked=false;$('summary').textContent=k.label+': the robot has room for '+k.slots+'. Take one off to add another.';$('summary').className='warn'}else draw()};l.append(cb)}
   l.append(Object.assign(document.createElement('span'),{textContent:it.name+' · '+KB(it.size)+(it.state?' · '+({installed:'on the robot',installing:'sending',waiting:'waiting',failed:'will retry'}[it.state]||it.state):'')}));
   if(it.message)l.append(Object.assign(document.createElement('span'),{className:'muted',textContent:it.message}));c.append(l)}
  if(!editing&&!rows.length)c.append(Object.assign(document.createElement('p'),{className:'muted',textContent:'The robot uses its built-in set.'}));box.append(c)}
 if(editing){const b=document.createElement('div');b.append(Object.assign(document.createElement('button'),{textContent:'Apply',onclick:async()=>{const r=await api('/api/stackchan/installed/'+encodeURIComponent($('unit').value)+'/choose',{mode:'custom',chosen});if(!r.ok){$('summary').textContent=r.d.error;$('summary').className='warn';return}editing=false;load()}}),Object.assign(document.createElement('button'),{className:'plain',textContent:'Cancel',onclick:()=>{editing=false;load()}}));box.append(b)}}
$('unit').onchange=()=>{editing=false;load()};units();
</script></main></body></html>
"""


def render_installed_page() -> bytes:
    return PAGE.encode("utf-8")
