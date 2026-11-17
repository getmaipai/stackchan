# ruff: noqa: E501
"""The settings page's Swipe pages section, as script: drag to order the pages left and right of the face, the control sheet items,
the quick actions and the closing times, with a live preview of the screen. Appended to the page script by ``settings_ui``; every
word comes from ``T('pg.*')`` (``i18n_pages.py``). The preview draws from ``pages_table.json`` (what the firmware core prints) and
``pgLayout`` is the same arithmetic as ``mpg_sheet_layout`` in ``maipai_pages_core.h`` (a test runs both and compares)."""

from __future__ import annotations

import json
from pathlib import Path

TABLE = json.loads(Path(__file__).with_name("pages_table.json").read_text())

JS_PAGES_LAYOUT = r"""
/* ---- swipe pages: the arithmetic of the unit's core (mpg_sheet_layout, mpg_grid, mpg_cell) ---- */
const PGT=__PAGES_TABLE__;
function pgLayout(items){const sl=[],ti=[],st=[];
 for(const n of items){const i=PGT.sheet.indexOf(n),k=i<=1?0:(i<=7?1:2);if(k===0&&sl.length<2)sl.push(i);else if(k===1&&ti.length<7)ti.push(i);else if(k===2&&st.length<4)st.push(i)}
 ti.push(PGT.sheet.length);const trows=Math.ceil(ti.length/4),srows=Math.ceil(sl.length/2);
 let hh=8+6,lines=0;if(st.length){lines=st.length>3?2:1;hh+=lines*16+4}
 hh+=srows*(28+4);hh+=trows*38+(trows-1)*4;hh+=6;
 const top=240-hh;let y=top+8,sy=0,sh=0;const r=[];
 if(lines){sy=y;sh=lines*16;y+=lines*16+4}
 sl.forEach((it,i)=>r.push([it,8+(i%2)*160,y+Math.floor(i/2)*32,144,28]));y+=srows*32;
 ti.forEach((it,i)=>{const inrow=(Math.floor(i/4)===trows-1)?ti.length-(trows-1)*4:4,col=i%4,rowW=inrow*72+(inrow-1)*6,full=4*72+3*6;
  r.push([it,Math.floor((320-full)/2)+col*78+Math.floor((full-rowW)/2),y+Math.floor(i/4)*42,72,38])});
 return {top_y:top,status_y:sy,status_h:sh,status:st,rects:r}}
function pgGrid(n){return n<=3?[Math.max(n,1),1]:(n===4?[2,2]:[3,2])}
function pgCell(i,n,ax,ay,aw,ah,gap){const [c,r]=pgGrid(n),cw=Math.floor((aw-(c-1)*gap)/c),ch=Math.floor((ah-(r-1)*gap)/r);return [ax+(i%c)*(cw+gap),ay+Math.floor(i/c)*(ch+gap),cw,ch]}
"""

JS_PAGES = r"""
/* ---- swipe pages: the preview and the section ---- */
function pgShades(fg){const m=/^#(..)(..)(..)$/.exec(fg),c=[1,2,3].map(i=>parseInt(m[i],16));return p=>'rgb('+c.map(x=>Math.round(x*p/100)).join(',')+')'}
function pgRound(g,x,y,w,h,r,fill,stroke){g.beginPath();g.roundRect(x,y,w,h,Math.min(r,w/2,h/2));if(fill){g.fillStyle=fill;g.fill()}if(stroke){g.strokeStyle=stroke;g.lineWidth=1;g.stroke()}}
function pgIcon(g,name,x,y,sc,col,bg){for(const [k,sx,sy,w,hh] of (PGT.icon_shapes[name]||[])){const X=x+sx*sc,Y=y+sy*sc,W=w*sc,H=hh*sc;
 if(k===0){g.fillStyle=col;g.beginPath();g.ellipse(X+W/2,Y+H/2,W/2,H/2,0,0,7);g.fill()}
 else if(k===1){g.strokeStyle=col;g.lineWidth=2*sc;g.beginPath();g.ellipse(X+W/2,Y+H/2,W/2-sc,H/2-sc,0,0,7);g.stroke()}
 else if(k===4){g.fillStyle=bg;g.fillRect(X,Y,W,H)}
 else{pgRound(g,X,Y,W,H,k===3?sc:0,col)}}}
function pgSegs(d){return [0x3F,0x06,0x5B,0x4F,0x66,0x6D,0x7D,0x07,0x7F,0x6F][d]}
function pgDigit(g,d,x,y,w,hh,t,col){const len=(hh-3*t)/2,m=pgSegs(d),R=[[x+t,y,w-2*t,t],[x+w-t,y+t,t,len],[x+w-t,y+2*t+len,t,len],[x+t,y+2*t+2*len,w-2*t,t],[x,y+2*t+len,t,len],[x,y+t,t,len],[x+t,y+t+len,w-2*t,t]];
 for(let s=0;s<7;s++)if(m&(1<<s))pgRound(g,R[s][0],R[s][1],R[s][2],R[s][3],t/3,col)}
function pgDrawPage(g,type,fg,cfg,idx,n,dim){const C=pgShades(fg),d=dim?35:100,col=C(d),dm=p=>C(p*d/100);
 g.fillStyle='#000';g.fillRect(0,28,320,156);g.save();g.translate(0,28);g.font='16px system-ui,sans-serif';g.textBaseline='top';
 const title=T('pg.page.'+type);
 if(type!=='clock'&&type!=='frame'){g.fillStyle=dm(70);g.fillText(title,10,2)}
 if(type==='clock'){const l={dw:44,dh:87,bar:9,gap:10,cw:22},w=4*l.dw+2*l.gap+l.cw,x0=(320-w)/2,xs=[x0,x0+l.dw+l.gap,x0+2*l.dw+l.gap+l.cw,x0+3*l.dw+2*l.gap+l.cw];
  [1,0,2,4].forEach((dg,i)=>pgDigit(g,dg,xs[i],10,l.dw,l.dh,l.bar,col));
  const cx=x0+2*l.dw+l.gap+(l.cw-l.bar)/2;pgRound(g,cx,10+l.dh/3-l.bar/2,l.bar,l.bar,3,col);pgRound(g,cx,10+2*l.dh/3-l.bar/2,l.bar,l.bar,3,col);
  g.font='20px system-ui,sans-serif';g.fillStyle=dm(70);g.textAlign='center';g.fillText('Tue Nov 17',160,10+l.dh+8);g.textAlign='left'}
 else if(type==='timers'){const rows=[[T('pg.sample.tea'),'4:32'],[T('pg.sample.pasta'),'24:59']];
  rows.forEach((r,i)=>{const y=26+i*38;pgRound(g,8,y,304,34,10,dm(16));g.fillStyle=col;g.font='18px system-ui,sans-serif';g.fillText(r[0],20,y+8);g.font='22px system-ui,sans-serif';g.fillText(r[1],150,y+6);pgRound(g,266,y,46,34,10,dm(30));g.font='16px system-ui,sans-serif';g.fillText('x',285,y+9)});
  [1,5,10].forEach((m,i)=>{pgRound(g,8+i*104,104,96,38,10,dm(16),dm(55));g.fillStyle=col;g.font='16px system-ui,sans-serif';g.textAlign='center';g.fillText('+'+m+' min',8+i*104+48,115);g.textAlign='left'})}
 else if(type==='games'){[['memory',14],['reaction',287],['whack',22]].forEach((r,i)=>{const y=26+i*38;pgRound(g,8,y,304,34,10,dm(16),dm(40));g.fillStyle=col;g.font='19px system-ui,sans-serif';g.fillText(T('pg.sample.'+r[0]),20,y+7);g.font='14px system-ui,sans-serif';g.fillStyle=dm(70);g.textAlign='right';g.fillText(T('pg.sample.best')+' '+r[1],268,y+9);g.textAlign='left';g.fillStyle=col;g.beginPath();g.moveTo(292,y+9);g.lineTo(292,y+25);g.lineTo(304,y+17);g.fill()})}
 else if(type==='actions'){const a=cfg.actions;a.forEach((nm,i)=>{const [x,y,w,hh]=pgCell(i,a.length,8,26,304,108,8);pgRound(g,x,y,w,hh,12,dm(16),dm(55));g.fillStyle=col;g.font='20px system-ui,sans-serif';g.textAlign='center';g.fillText(T('pg.action.'+nm),x+w/2,y+hh/2-11);g.textAlign='left'})}
 else if(type==='frame'){const gr=g.createLinearGradient(64,0,256,144);gr.addColorStop(0,'#1a3a8f');gr.addColorStop(.5,'#8a5a9a');gr.addColorStop(1,'#f0c040');g.fillStyle=gr;g.fillRect(64,0,192,144)}
 else{const tl=[['sun','weather','72 F'],['home','garage','Open'],['lamp','lights','3 on'],['temp','inside','68 F'],['bell','mail','1'],['heart','mom','Home']];
  tl.forEach((t,i)=>{const [x,y,w,hh]=pgCell(i,6,8,26,304,108,8);pgRound(g,x,y,w,hh,12,dm(16));g.font='14px system-ui,sans-serif';g.fillStyle=dm(70);g.fillText(T('pg.sample.'+t[1]),x+7,y+3);pgIcon(g,t[0],x+6,y+22,1,col,dm(16));g.font='20px system-ui,sans-serif';g.fillStyle=col;g.fillText(t[2],x+34,y+21)});
  g.font='14px system-ui,sans-serif';g.fillStyle=dm(55);g.textAlign='right';g.fillText('5 min',310,5);g.textAlign='left'}
 if(n>=2)for(let i=0;i<n;i++){const on=i===idx,x=160+(i*2-(n-1))*7;g.fillStyle=dm(on?100:32);g.beginPath();g.arc(x,148,on?4:3,0,7);g.fill()}
 g.restore()}
function pgDrawSheet(g,fg,cfg,dim){const C=pgShades(fg),d=dim?35:100,L=pgLayout(cfg.sheet_items),dm=p=>C(p*d/100);
 g.fillStyle=C(10*d/100);g.beginPath();g.roundRect(0,L.top_y,320,260-L.top_y,14);g.fill();g.fillStyle=dm(45);g.fillRect(14,L.top_y,292,2);g.fillStyle=dm(50);g.fillRect(142,L.top_y+4,36,4);
 g.textBaseline='top';g.font='14px system-ui,sans-serif';
 if(L.status.length){g.fillStyle=dm(85);const txt={8:'Wi-Fi 3/4',9:'Battery 82%',10:'Private net up',11:'Settings: 192.0.2.10'};g.fillText(L.status.map(i=>txt[i]).join('    '),8,L.status_y)}
 for(const [it,x,y,w,hh] of L.rects){const name=PGT.sheet[it];
  if(it<=1){g.fillStyle=dm(80);g.fillText(T('pg.item.'+name),x,y-1);pgRound(g,x,y+18,w,10,5,dm(28));pgRound(g,x,y+18,w*(it===0?.7:.8),10,5,dm(100));g.fillStyle=dm(100);g.beginPath();g.arc(x+w*(it===0?.7:.8),y+23,6,0,7);g.fill()}
  else{const on=name==='light';pgRound(g,x,y,w,hh,10,on?dm(100):dm(16),dm(40));g.fillStyle=on?'#000':dm(100);g.textAlign='center';
   const label=it===PGT.sheet.length?'More':({light:'Light',find:'Find me'}[name]||T('pg.item.'+name).split(' ')[0]);
   if(['mute','quiet','light'].includes(name)){g.fillText(label,x+w/2,y+3);g.fillText(on?'on':'off',x+w/2,y+hh-18)}else g.fillText(label,x+w/2,y+hh/2-8);g.textAlign='left'}}}
function pgFace(g,fg){const C=pgShades(fg);g.fillStyle='#000';g.fillRect(0,0,320,240);pgRound(g,40,60,79,85,24,C(100));pgRound(g,201,60,79,85,24,C(100));pgRound(g,128,152,64,12,6,C(100))}
function pgPreview(cv,cfg,sel,fg,dim){const g=cv.getContext('2d');pgFace(g,fg);
 const strip=[...cfg.left].reverse().concat(['face'],cfg.right);
 if(sel==='sheet'){pgDrawSheet(g,fg,cfg,dim);return}
 const i=strip.indexOf(sel);if(sel!=='face'&&i>=0)pgDrawPage(g,sel,fg,cfg,i,strip.length,dim)}
function pgList(label,help,items,all,min,max,names,onchange){
 const box=h('div',{class:'pglist'}),sel=h('select',{'aria-label':T('pg.add')});
 const draw=()=>{box.replaceChildren();
  items.forEach((it,i)=>{const row=h('div',{class:'item',draggable:'true','data-i':i,title:T('pg.drag')},
   h('span',{class:'grow'},names(it)),
   h('button',{class:'btn',type:'button','aria-label':T('pg.up')+': '+names(it),disabled:i===0,onclick:()=>{[items[i-1],items[i]]=[items[i],items[i-1]];draw();onchange()}},'↑'),
   h('button',{class:'btn',type:'button','aria-label':T('pg.down')+': '+names(it),disabled:i===items.length-1,onclick:()=>{[items[i+1],items[i]]=[items[i],items[i+1]];draw();onchange()}},'↓'),
   h('button',{class:'btn',type:'button','aria-label':T('pg.remove')+': '+names(it),disabled:items.length<=min,onclick:()=>{items.splice(i,1);draw();onchange()}},'×'));
   row.addEventListener('dragstart',e=>{e.dataTransfer.setData('text/plain',String(i));e.dataTransfer.effectAllowed='move'});
   row.addEventListener('dragover',e=>{e.preventDefault();e.dataTransfer.dropEffect='move'});
   row.addEventListener('drop',e=>{e.preventDefault();const from=Number(e.dataTransfer.getData('text/plain'));if(Number.isInteger(from)&&from!==i){const [m]=items.splice(from,1);items.splice(i,0,m);draw();onchange()}});
   box.append(row)});
  if(!items.length)box.append(h('p',{class:'hint'},T('pg.none_left')));
  sel.replaceChildren(h('option',{value:''},label));
  for(const a of all()){if(!items.includes(a))sel.append(h('option',{value:a},names(a)))}
  sel.disabled=items.length>=max||sel.options.length<2;sel.value=''};
 sel.addEventListener('change',()=>{if(sel.value){items.push(sel.value);draw();onchange()}});
 draw();return h('div',{class:'stack'},help?h('p',{class:'hint'},help):null,box,sel)}
async function swipePagesCard(id){const r=await api(unitPath(id,'pages'));if(!r.ok)return null;const pv=r.d,vals=pv.values;
 let sel='face';const cv=h('canvas',{width:320,height:240,role:'img','aria-label':T('pg.preview'),style:'width:100%;max-width:320px;border-radius:12px;background:#000;display:block'});
 const fg='#f4f4f4',chips=h('div',{class:'btns',role:'group','aria-label':T('pg.preview')});
 const strip=()=>[...vals.left].reverse().concat(['face'],vals.right);
 const draw=()=>{if(sel!=='sheet'&&!strip().includes(sel))sel='face';pgPreview(cv,vals,sel,fg,false);chips.replaceChildren(...strip().map(p=>h('button',{class:'btn'+(p===sel?' pri':''),type:'button','aria-pressed':String(p===sel),onclick:()=>{sel=p;draw()}},p==='face'?T('pg.face'):T('pg.page.'+p))),h('button',{class:'btn'+(sel==='sheet'?' pri':''),type:'button','aria-pressed':String(sel==='sheet'),onclick:()=>{sel='sheet';draw()}},T('pg.page.sheet')))};
 const put=async patch=>{const q=await save(unitPath(id,'pages'),patch,true);if(q.ok){Object.assign(vals,q.d.values||patch);draw()}return q.ok};
 const coming=pv.unit_ready?null:h('p',{class:'hint'},h('span',{class:'badge'},T('pol.coming')));
 const left=pgList(T('pg.add'),T('pg.left_help'),vals.left,()=>PGT.pages.filter(p=>!vals.right.includes(p)),0,3,p=>T('pg.page.'+p),()=>{draw();put({left:vals.left})});
 const right=pgList(T('pg.add'),T('pg.right_help'),vals.right,()=>PGT.pages.filter(p=>!vals.left.includes(p)),0,3,p=>T('pg.page.'+p),()=>{draw();put({right:vals.right})});
 const acts=pgList(T('pg.add_action'),T('pg.actions_help'),vals.actions,()=>PGT.actions,4,6,a=>T('pg.action.'+a),()=>{draw();put({actions:vals.actions})});
 const items=pgList(T('pg.add_item'),T('pg.items_help'),vals.sheet_items,()=>PGT.sheet,0,12,a=>T('pg.item.'+a),()=>{draw();put({sheet_items:vals.sheet_items})});
 const times=[slider(T('pg.page_idle'),PGT.limits.idle_s[0],PGT.limits.idle_s[1],5,vals.idle_s,x=>x+' '+T('pg.seconds'),null,x=>put({idle_s:x})),
  slider(T('pg.sheet_idle'),PGT.limits.sheet_s[0],PGT.limits.sheet_s[1],1,vals.sheet_s,x=>x+' '+T('pg.seconds'),null,x=>put({sheet_s:x}))];
 const note=h('p',{class:'hint',role:'status'},T('pg.prev_note'));
 const showBtn=h('button',{class:'btn',type:'button',onclick:async e=>{const b=e.currentTarget;b.disabled=true;const q=await save(unitPath(id,'pages/show'),{name:sel==='face'?'face':sel},true);b.disabled=false;if(q.ok&&q.d.ok)toast(T('pg.shown'));else toast((q.d&&(q.d.message||q.d.error))||T('net_error'),q.d&&q.d.pending?'warn':'bad')}},T('pg.show'));
 const tilesBtn=h('button',{class:'btn',type:'button',onclick:async e=>{const b=e.currentTarget;b.disabled=true;const sample=[['sun','weather','72 F'],['home','garage','Open'],['lamp','lights','3 on'],['temp','inside','68 F'],['bell','mail','1'],['heart','mom','Home']].map(t=>({icon:t[0],label:T('pg.sample.'+t[1]),value:t[2]}));
  const q=await save(unitPath(id,'pages/tiles'),{tiles:sample},true);b.disabled=false;if(q.ok&&q.d.ok)toast(q.d.message);else toast((q.d&&(q.d.message||q.d.error))||T('net_error'),q.d&&q.d.pending?'warn':'bad')}},T('pg.tiles'));
 const resetBtn=h('button',{class:'btn',type:'button',onclick:async()=>{if(await put(pv.defaults)){location.reload()}}},T('pg.reset'));
 draw();
 return card(T('pg.title'),T('pg.help'),coming,h('div',{class:'stack'},cv,chips,note),
  h('h3',{},T('pg.left')),left,h('h3',{},T('pg.right')),right,h('h3',{},T('pg.times')),...times,h('h3',{},T('pg.actions')),acts,h('h3',{},T('pg.items')),items,
  h('p',{class:'hint'},T('pg.show_help')),h('div',{class:'btns'},showBtn,tilesBtn,resetBtn),h('p',{class:'hint'},T('pg.tiles_help')))}
"""

JS_PAGES_FULL = JS_PAGES_LAYOUT.replace("__PAGES_TABLE__", json.dumps(TABLE)) + JS_PAGES
