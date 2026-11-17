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
function pgLayout(items){const sl=[],ti=[],st=[],gi=PGT.sheet.indexOf('games'),wi=PGT.sheet.indexOf('wifi'),bi=PGT.sheet.indexOf('battery');let row=0,lines=0;
 for(const n of items){const i=PGT.sheet.indexOf(n),k=i<=1?0:(i<=gi?1:2);if(k===0&&sl.length<2)sl.push(i);else if(k===1&&ti.length<5)ti.push(i);else if(k===2&&st.length<4){st.push(i);if(i===wi||i===bi)row=1;else lines++}}
 ti.push(PGT.sheet.length);const trows=Math.ceil(ti.length/6),srows=Math.ceil(sl.length/2);
 let hh=14;if(row)hh+=24;if(lines>0)hh+=lines*20+4;
 hh+=srows*48;hh+=trows*44+(trows-1)*4;hh+=6;
 const top=240-hh;let y=top+14,sy=0,sh=0,ty=0,th=0;const r=[];
 if(row){sy=y;sh=24;y+=24}
 if(lines>0){ty=y;th=lines*20;y+=lines*20+4}
 sl.forEach((it,i)=>r.push([it,8+(i%2)*160,y+Math.floor(i/2)*48,144,44]));y+=srows*48;
 ti.forEach((it,i)=>{const inrow=(Math.floor(i/6)===trows-1)?ti.length-(trows-1)*6:6,col=i%6,rowW=inrow*44+(inrow-1)*6,full=6*44+5*6;
  r.push([it,Math.floor((320-full)/2)+col*50+Math.floor((full-rowW)/2),y+Math.floor(i/6)*48,44,44])});
 return {top_y:top,status_y:sy,status_h:sh,text_y:ty,text_h:th,status:st,rects:r}}
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
 if(type!=='clock'&&type!=='frame'&&type!=='games'){g.fillStyle=dm(70);g.fillText(title,10,2)}
 if(type==='clock'){const l={dw:56,dh:108,bar:12,gap:10,cw:26},w=4*l.dw+2*l.gap+l.cw,x0=(320-w)/2,xs=[x0,x0+l.dw+l.gap,x0+2*l.dw+l.gap+l.cw,x0+3*l.dw+2*l.gap+l.cw];
  [1,0,2,4].forEach((dg,i)=>pgDigit(g,dg,xs[i],10,l.dw,l.dh,l.bar,col));
  const cx=x0+2*l.dw+l.gap+(l.cw-l.bar)/2;pgRound(g,cx,10+l.dh/3-l.bar/2,l.bar,l.bar,4,col);pgRound(g,cx,10+2*l.dh/3-l.bar/2,l.bar,l.bar,4,col);
  g.font='20px system-ui,sans-serif';g.fillStyle=dm(70);g.textAlign='center';g.fillText('Tue Nov 17',160,10+l.dh+3);g.textAlign='left'}
 else if(type==='timers'){const rows=[[T('pg.sample.tea'),'4:32']];
  rows.forEach((r,i)=>{const y=24+i*46;pgRound(g,8,y,304,44,10,dm(16));g.fillStyle=col;g.font='18px system-ui,sans-serif';g.fillText(r[0],18,y+12);g.font='24px system-ui,sans-serif';g.fillText(r[1],142,y+9);pgRound(g,254,y,58,44,10,dm(30));g.font='20px system-ui,sans-serif';g.fillText('x',277,y+11)});
  [1,5,10].forEach((m,i)=>{pgRound(g,8+i*104,72,96,44,10,dm(16),dm(55));g.fillStyle=col;g.font='20px system-ui,sans-serif';g.textAlign='center';g.fillText('+'+m+' min',8+i*104+48,83);g.textAlign='left'})}
 else if(type==='games'){[['memory',14],['reaction',287],['whack',22]].forEach((r,i)=>{const y=10+i*46;pgRound(g,8,y,304,44,12,dm(16),dm(40));g.fillStyle=col;g.font='24px system-ui,sans-serif';g.fillText(T('pg.sample.'+r[0]),22,y+9);g.font='16px system-ui,sans-serif';g.fillStyle=dm(70);g.textAlign='right';g.fillText(T('pg.sample.best')+' '+r[1],262,y+13);g.textAlign='left';g.fillStyle=col;g.beginPath();g.moveTo(286,y+11);g.lineTo(286,y+33);g.lineTo(302,y+22);g.fill()})}
 else if(type==='actions'){const a=cfg.actions;a.forEach((nm,i)=>{const [x,y,w,hh]=pgCell(i,a.length,8,26,304,108,8);pgRound(g,x,y,w,hh,12,dm(16),dm(55));g.fillStyle=col;g.font='24px system-ui,sans-serif';g.textAlign='center';g.fillText(T('pg.action.'+nm),x+w/2,y+hh/2-13);g.textAlign='left'})}
 else if(type==='frame'){const gr=g.createLinearGradient(64,0,256,144);gr.addColorStop(0,'#1a3a8f');gr.addColorStop(.5,'#8a5a9a');gr.addColorStop(1,'#f0c040');g.fillStyle=gr;g.fillRect(64,0,192,144)}
 else{const tl=[['sun','weather','72 F'],['home','garage','Open'],['lamp','lights','3 on'],['temp','inside','68 F'],['bell','mail','1'],['heart','mom','Home']];
  tl.forEach((t,i)=>{const [x,y,w,hh]=pgCell(i,6,8,26,304,108,8);pgRound(g,x,y,w,hh,12,dm(16));g.font='14px system-ui,sans-serif';g.fillStyle=dm(70);g.fillText(T('pg.sample.'+t[1]),x+7,y+3);pgIcon(g,t[0],x+6,y+22,1,col,dm(16));g.font='20px system-ui,sans-serif';g.fillStyle=col;g.fillText(t[2],x+34,y+21)});
  g.font='14px system-ui,sans-serif';g.fillStyle=dm(55);g.textAlign='right';g.fillText('5 min',310,5);g.textAlign='left'}
 if(n>=2)for(let i=0;i<n;i++){const on=i===idx,x=160+(i*2-(n-1))*7;g.fillStyle=dm(on?100:32);g.beginPath();g.arc(x,150,on?4:3,0,7);g.fill()}
 pgRound(g,136,2,48,5,3,dm(70));
 g.restore()}
function pgSheetIcon(g,name,x,y,col,bg){for(const [k,sx,sy,w,hh] of (PGT.sheet_icons[name]||[])){const X=x+sx,Y=y+sy;
 if(k===0){g.fillStyle=col;g.beginPath();g.ellipse(X+w/2,Y+hh/2,w/2,hh/2,0,0,7);g.fill()}
 else if(k===1){g.strokeStyle=col;g.lineWidth=2;g.beginPath();g.ellipse(X+w/2,Y+hh/2,w/2-1,hh/2-1,0,0,7);g.stroke()}
 else if(k===4){g.fillStyle=bg;g.fillRect(X,Y,w,hh)}
 else if(k===5){g.fillStyle=bg;g.beginPath();g.ellipse(X+w/2,Y+hh/2,w/2,hh/2,0,0,7);g.fill()}
 else pgRound(g,X,Y,w,hh,k===3?1:0,col)}}
function pgDrawSheet(g,fg,cfg,dim){const C=pgShades(fg),d=dim?35:100,L=pgLayout(cfg.sheet_items),dm=p=>C(p*d/100);
 g.fillStyle=C(10*d/100);g.beginPath();g.roundRect(0,L.top_y,320,260-L.top_y,14);g.fill();g.fillStyle=dm(45);g.fillRect(14,L.top_y,292,2);pgRound(g,136,L.top_y+4,48,5,3,dm(70));
 g.textBaseline='top';
 if(L.status_h){const has=n=>L.status.includes(PGT.sheet.indexOf(n));g.font='20px system-ui,sans-serif';g.fillStyle=dm(90);g.textAlign='center';g.fillText('10:24',160,L.status_y);g.textAlign='left';
  if(has('wifi'))[6,10,14,18].forEach((bh,k)=>pgRound(g,12+k*8,L.status_y+20-bh,6,bh,2,k<3?'#46dc78':dm(22)));
  if(has('battery')){g.font='16px system-ui,sans-serif';g.fillStyle='#46dc78';g.textAlign='right';g.fillText('82%',276,L.status_y+2);g.textAlign='left';pgRound(g,280,L.status_y+4,26,14,3,null,dm(80));pgRound(g,282,L.status_y+6,17,10,1,'#46dc78')}}
 if(L.text_h){g.font='16px system-ui,sans-serif';g.fillStyle=dm(85);const txt={9:'Private net up',10:'Settings: 192.0.2.10'};g.fillText(L.status.filter(i=>txt[i]).map(i=>txt[i]).join('    '),8,L.text_y)}
 for(const [it,x,y,w,hh] of L.rects){const name=PGT.sheet[it];
  if(it<=1){g.font='16px system-ui,sans-serif';g.fillStyle=dm(90);g.fillText(T('pg.item.'+name),x,y);pgRound(g,x+8,y+26,w-16,16,8,dm(28));pgRound(g,x+8,y+26,(w-16)*(it===0?.7:.8),16,8,dm(100));g.fillStyle=dm(100);g.beginPath();g.arc(x+8+(w-16)*(it===0?.7:.8),y+34,16,0,7);g.fill()}
  else{const on=name==='light',bg=on?dm(100):dm(16);pgRound(g,x,y,w,hh,10,bg,dm(40));pgSheetIcon(g,it===PGT.sheet.length?'more':name,x+10,y+10,on?'#000':dm(100),bg)}}}
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
 const acts=pgList(T('pg.add_action'),T('pg.actions_help'),vals.actions,()=>PGT.actions,2,4,a=>T('pg.action.'+a),()=>{draw();put({actions:vals.actions})});
 const items=pgList(T('pg.add_item'),T('pg.items_help'),vals.sheet_items,()=>PGT.sheet,0,11,a=>T('pg.item.'+a),()=>{draw();put({sheet_items:vals.sheet_items})});
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
