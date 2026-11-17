# ruff: noqa: E501
"""The settings page section for picture faces (firmware patches H03 and H04).

One card per unit: the mode, a picture per expression, the places of the eyes and mouth (overlay mode) and
two buttons. The page itself draws each chosen picture into a 640 by 480 canvas on the owner's own computer and sends
that to the host, which resizes it to 320 by 240; nothing is uploaded anywhere else.
It uses the page's own helpers (``h``, ``card``, ``seg``, ``slider``, ``api``, ``save``, ``ask``, ``toast``).
"""

from __future__ import annotations

PICTURES_JS = r"""
function picSection(id){
const base=unitPath(id,'pictures');
const wrap=h('div',{class:'stack'});
const note=h('p',{class:'hint',role:'status'});
async function post(action,data){const r=await api(base+'/'+action,data||{});if(!r.ok){toast(r.d.error||T('net_error'),'bad');return null}if(r.d.message)toast(r.d.message);return r.d}
async function rgb(file){const bmp=await createImageBitmap(file);const c=document.createElement('canvas');
c.width=640;c.height=480;const x=c.getContext('2d');x.fillStyle='#000';x.fillRect(0,0,640,480);
const s=Math.max(640/bmp.width,480/bmp.height),w=bmp.width*s,hh=bmp.height*s;
x.drawImage(bmp,(640-w)/2,(480-hh)/2,w,hh);const px=x.getImageData(0,0,640,480).data;let bin='';
for(let i=0;i<px.length;i+=32768)bin+=String.fromCharCode.apply(null,px.subarray(i,i+32768));return btoa(bin)}
const OV=[['lx','x'],['ly','y'],['rx','x'],['ry','y'],['eye_w','w'],['eye_h','h'],['mx','x'],['my','y'],['mouth_w','w'],['mouth_h','h']];
function draw(d){wrap.replaceChildren();
 const modes=seg(S['settings.pics.mode'],d.choices.mode.map(m=>({v:m,t:S['settings.pics.mode.'+m]})),d.mode,async m=>{const r=await post('options',{mode:m,fps:d.fps,overlay:d.overlay});if(r){draw(r);return true}return false});
 const head=card(S['settings.pics'],S['settings.pics.help'],modes);
 if(d.mode==='sequence')head.append(slider(S['settings.pics.fps'],d.limits.fps[0],d.limits.fps[1],1,d.fps,x=>x+'',null,async x=>{const r=await post('options',{mode:d.mode,fps:x});if(r)draw(r)}));
 if(d.mode==='overlay'){const ovin={};const grid=h('div',{class:'hrs'});
  const send=async()=>{const o={};for(const [k] of OV)o[k]=parseInt(ovin[k].value,10);o.color=ovin.color.value;const r=await post('options',{mode:d.mode,fps:d.fps,overlay:o});if(r)draw(r)};
  for(const [k] of OV){const i=h('input',{type:'number',value:d.overlay[k],onchange:send});ovin[k]=i;grid.append(field(k.replace('_',' '),i))}
  const col=h('input',{type:'color',value:d.overlay.color,'aria-label':S['settings.pics.color'],onchange:send});ovin.color=col;
  head.append(h('p',{class:'hint'},S['settings.pics.overlay']),grid,field(S['settings.pics.color'],col))}
 wrap.append(head);
 const slots=h('div',{class:'tiles',style:'grid-template-columns:repeat(auto-fill,minmax(150px,1fr))'});
 for(const s of d.slots){const max=d.limits.per_slot;const t=h('div',{class:'tile',style:'cursor:default'},h('b',{},S['settings.pics.slot.'+s.slot]));
  for(const u of s.thumbs)t.append(h('div',{class:'screen'},h('img',{src:u,alt:S['settings.pics.slot.'+s.slot],style:'width:100%;display:block'})));
  if(!s.thumbs.length)t.append(h('div',{class:'empty',style:'padding:20px 8px'},'+'));
  const btns=h('div',{class:'btns',style:'justify-content:center'});
  if(s.frames<max){const id2='pic-'+s.slot;const pick=h('input',{type:'file',accept:'image/*',multiple:d.mode==='sequence',id:id2,style:'position:absolute;width:1px;height:1px;opacity:0','aria-label':S['settings.pics.add']+': '+S['settings.pics.slot.'+s.slot]});
   pick.onchange=async()=>{let at=s.frames,last=null;for(const file of Array.from(pick.files).slice(0,max-s.frames)){let b64;try{b64=await rgb(file)}catch(e){toast(S['settings.pics.unreadable'],'bad');return}
    const r=await post('add',{slot:s.slot,index:at,width:640,height:480,rgba_b64:b64});if(!r)return;last=r;at++}if(last)draw(last)};
   btns.append(pick,h('label',{class:'btn',for:id2,style:'min-height:40px;padding:0 12px;font-size:.84rem'},S['settings.pics.add']))}
  if(s.frames>0)btns.append(h('button',{class:'btn',type:'button',style:'min-height:40px;padding:0 12px;font-size:.84rem',onclick:async()=>{const r=await post('remove',{slot:s.slot});if(r)draw(r)}},S['settings.pics.remove']));
  t.append(btns);slots.append(t)}
 const used=h('div',{class:'slide'},h('div',{class:'head'},h('span',{class:'hint'},S['settings.pics.used']),h('output',{},d.frames+' / '+d.limits.frames+', '+Math.round(d.bytes/1024)+' KB / '+Math.round(d.limits.bytes/1024)+' KB')),h('div',{class:'meter'},h('i',{style:'width:'+Math.min(100,d.bytes*100/d.limits.bytes)+'%'})));
 const sendB=h('button',{class:'btn pri',type:'button',disabled:!d.ready,onclick:async()=>{toast(S['settings.pics.sending']);const r=await post('send');if(r)draw(await (await fetch(base+'?lang='+LANG)).json())}},S['settings.pics.send']);
 const clr=h('button',{class:'btn bad',type:'button',onclick:async()=>{if(!(await ask(S['settings.pics.clear_ask'],S['settings.pics.clear'])))return;const r=await post('clear');if(r)draw(r)}},S['settings.pics.clear']);
 wrap.append(card(null,null,slots,used,d.problem?h('div',{class:'banner bad',role:'alert'},d.problem):null,h('div',{class:'btns'},sendB,clr)))}
api(base).then(r=>{if(r.ok&&r.d.slots)draw(r.d);else wrap.append(card(S['settings.pics'],null,h('div',{class:'banner'},r.d.error||T('net_error')),h('span',{class:'badge'},T('soon'))))});
return wrap}
"""


def pictures_js(code: str) -> str:
    """The section's script with the page language filled in."""
    return PICTURES_JS.replace("__LANG__", code)
