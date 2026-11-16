# ruff: noqa: E501
"""The settings page section for picture faces (firmware patches H03 and H04).

One section per unit: the mode, a picture per expression, the places of the eyes and mouth (overlay mode) and
two buttons. The page itself draws each chosen picture into a 640 by 480 canvas on the owner's own computer and sends
that to the host, which resizes it to 320 by 240; nothing is uploaded anywhere else.
"""

from __future__ import annotations

PICTURES_JS = r"""
function picSection(id){const f=document.createElement('fieldset');
const lg=document.createElement('legend');lg.textContent=S['settings.pics'];f.append(lg);
const help=document.createElement('p');help.textContent=S['settings.pics.help'];f.append(help);
const base='/api/stackchan/unit/'+encodeURIComponent(id)+'/pictures';
const body=document.createElement('div');f.append(body);
const note=document.createElement('p');note.setAttribute('role','status');f.append(note);
async function post(action,data){const r=await fetch(base+'/'+action,{method:'POST',
headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({lang:'__LANG__'},data||{}))});
const d=await r.json();if(!r.ok){note.textContent=d.error;return null}
note.textContent=d.message||'';return d}
async function rgb(file){const bmp=await createImageBitmap(file);const c=document.createElement('canvas');
c.width=640;c.height=480;const x=c.getContext('2d');x.fillStyle='#000';x.fillRect(0,0,640,480);
const s=Math.max(640/bmp.width,480/bmp.height),w=bmp.width*s,h=bmp.height*s;
x.drawImage(bmp,(640-w)/2,(480-h)/2,w,h);const px=x.getImageData(0,0,640,480).data;let bin='';
for(let i=0;i<px.length;i+=32768)bin+=String.fromCharCode.apply(null,px.subarray(i,i+32768));return btoa(bin)}
const OV=[['lx','x'],['ly','y'],['rx','x'],['ry','y'],['eye_w','w'],['eye_h','h'],['mx','x'],['my','y'],['mouth_w','w'],['mouth_h','h']];
function draw(d){body.replaceChildren();
const mode=document.createElement('select');mode.setAttribute('aria-label',S['settings.pics.mode']);
for(const m of d.choices.mode)mode.append(Object.assign(document.createElement('option'),{value:m,textContent:S['settings.pics.mode.'+m]}));
mode.value=d.mode;
const ml=document.createElement('label');ml.textContent=S['settings.pics.mode'];ml.append(mode);body.append(ml);
const opts=()=>({mode:mode.value,fps:parseInt(fps.value,10)||6,overlay:ovValues()});
const fps=Object.assign(document.createElement('input'),{type:'number',min:d.limits.fps[0],max:d.limits.fps[1],value:d.fps});
const fl=document.createElement('label');fl.textContent=S['settings.pics.fps'];fl.append(fps);
if(d.mode==='sequence')body.append(fl);
const ovin={};const ovbox=document.createElement('div');
const ovValues=()=>{const o={};for(const [k] of OV)if(ovin[k])o[k]=parseInt(ovin[k].value,10);if(ovin.color)o.color=ovin.color.value;return o};
if(d.mode==='overlay'){const t=document.createElement('p');t.textContent=S['settings.pics.overlay'];ovbox.append(t);
const row=document.createElement('div');row.className='row';
for(const [k,short] of OV){const i=Object.assign(document.createElement('input'),{type:'number',value:d.overlay[k],title:k,placeholder:short});
i.setAttribute('aria-label',k);ovin[k]=i;row.append(i)}
const col=Object.assign(document.createElement('input'),{type:'color',value:d.overlay.color});col.setAttribute('aria-label',S['settings.pics.colour']);ovin.color=col;row.append(col);
ovbox.append(row);body.append(ovbox)}
const save=async()=>{const r=await post('options',opts());if(r)draw(r)};
mode.onchange=save;fps.onchange=save;for(const k in ovin)ovin[k].onchange=save;
for(const s of d.slots){const row=document.createElement('div');row.style.margin='.6rem 0';
const t=document.createElement('b');t.textContent=S['settings.pics.slot.'+s.slot]+' ';row.append(t);
for(const u of s.thumbs){const im=document.createElement('img');im.src=u;im.width=80;im.height=60;im.alt=S['settings.pics.slot.'+s.slot];im.style.marginRight='4px';row.append(im)}
const max=d.limits.per_slot;
if(s.frames<max){const pick=Object.assign(document.createElement('input'),{type:'file',accept:'image/*',multiple:d.mode==='sequence'});
pick.setAttribute('aria-label',S['settings.pics.add']+': '+S['settings.pics.slot.'+s.slot]);pick.style.width='auto';
pick.onchange=async()=>{let at=s.frames,last=null;for(const file of Array.from(pick.files).slice(0,max-s.frames)){
let b64;try{b64=await rgb(file)}catch(e){note.textContent=S['settings.pics.unreadable'];return}
const r=await post('add',{slot:s.slot,index:at,width:640,height:480,rgba_b64:b64});if(!r)return;last=r;at++}
if(last)draw(last)};row.append(pick)}
if(s.frames>0){const rm=document.createElement('button');rm.textContent=S['settings.pics.remove'];
rm.onclick=async()=>{const r=await post('remove',{slot:s.slot});if(r)draw(r)};row.append(rm)}
body.append(row)}
const used=document.createElement('p');used.textContent=S['settings.pics.used']+': '+d.frames+' / '+d.limits.frames+', '+Math.round(d.bytes/1024)+' KB / '+Math.round(d.limits.bytes/1024)+' KB';
body.append(used);
if(d.problem){const p=document.createElement('p');p.setAttribute('role','alert');p.textContent=d.problem;body.append(p)}
const send=document.createElement('button');send.textContent=S['settings.pics.send'];send.disabled=!d.ready;
send.onclick=async()=>{note.textContent=S['settings.pics.sending'];const r=await post('send');if(r)draw(await (await fetch(base+'?lang=__LANG__')).json())};
const clr=document.createElement('button');clr.textContent=S['settings.pics.clear'];
clr.onclick=async()=>{if(!confirm(S['settings.pics.clear_ask']))return;const r=await post('clear');if(r)draw(r)};
body.append(send,' ',clr)}
fetch(base+'?lang=__LANG__').then(r=>r.json()).then(d=>{if(d.slots)draw(d);else note.textContent=d.error||''}).catch(()=>{});
return f}
"""


def pictures_js(code: str) -> str:
    """The section's script with the page language filled in."""
    return PICTURES_JS.replace("__LANG__", code)
