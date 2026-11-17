# ruff: noqa: E501
"""The banner row of the settings page preview (patch N01): the unit's banner geometry and rules in JavaScript.

The unit draws information in one row at the top of the screen from ``hal/maipai_banner_core.h`` (geometry, fitting, the
marquee, the eased shift of the face, when battery and Wi-Fi show). ``banner_table.json`` is the table of that core, printed by
``host/tests/firmware/banner_dump.c table``; the page's functions below are ported line for line, and
``tests/test_banner_preview_parity.py`` feeds the same inputs to the C core and to this JavaScript (node) and compares.
"""

from __future__ import annotations

import json
from pathlib import Path

TABLE_PATH = Path(__file__).with_name("banner_table.json")
BANNER_TABLE = json.loads(TABLE_PATH.read_text())

BANNER_JS = r"""
/* ---- the fixed zones, the banner row and the subtitle strip of the unit (hal/maipai_banner_core.h, maipai_subs_core.h) ---- */
const BT=__BANNER_TABLE__;
function mbStripW(bits){let n=0;for(let i=0;i<BT.flags.length;i++)n+=(bits>>i)&1;return n===0?0:n*BT.strip.glyph_w+(n-1)*BT.strip.gap}
function mbTextRoom(bits,icon){let w=BT.row.w-2*BT.pad_x-(icon!==0?BT.icon_w+4:0);const s=mbStripW(bits);if(s>0)w-=s+6;return w}
function mbFit(w,room){return w<=room?0:1}
function mbMarqueePass(o){return o<=0?0:2*BT.scroll_pause_ms+Math.trunc(o*1000/BT.scroll_px_s)}
function mbMarqueeX(t,o){if(o<=0)return 0;const scroll=Math.trunc(o*1000/BT.scroll_px_s),period=2*BT.scroll_pause_ms+scroll+400,u=t%period;if(u<BT.scroll_pause_ms)return 0;if(u<BT.scroll_pause_ms+scroll)return Math.trunc((u-BT.scroll_pause_ms)*BT.scroll_px_s/1000);return o}
function mbFadeStep(opa,visible,dt){const goal=visible?255:0;let step=Math.trunc(Math.min(dt,100)*255/BT.fade_ms);if(step<1)step=1;if(opa<goal)return opa+step>goal?goal:opa+step;if(opa>goal)return opa-step<goal?goal:opa-step;return opa}
function mbCaptionHold(chars){let ms=chars*55;if(ms<2600)ms=2600;if(ms>12000)ms=12000;return ms}
function mbBatteryShown(level,charging,onCable,mode,blip){if(level<0)return 0;if(mode===1)return 1;if(blip&&charging)return 1;return level<20&&!charging&&!onCable?1:0}
function mbWifiShown(wifi,hub,mode){if(mode===1)return 1;return!wifi||!hub?1:0}
function msPageMs(chars){let ms=chars*BT.subtitles.page_per_char_ms;if(ms<BT.subtitles.page_min_ms)ms=BT.subtitles.page_min_ms;if(ms>BT.subtitles.page_max_ms)ms=BT.subtitles.page_max_ms;return ms}
function msTextTop(lines,lineH){const z=BT.zones.subtitles;return z[0]+Math.trunc(((z[1]-z[0])-lines*lineH)/2)}
/* the row is ONE rectangle; bannerLayout only decides what is inside it: o = {text, icon (a name), kind 'msg' or 'chip', strip: [flag names]} */
function bannerLayout(ctx,o){ctx.save();ctx.font='600 '+BT.font_px+'px system-ui,sans-serif';try{const fl=BT.flags,bits=(o.strip||[]).reduce((a,n)=>a|(1<<fl.indexOf(n)),0),icon=BT.icons.indexOf(o.icon||'none');
 const room=mbTextRoom(bits,icon),w1=ctx.measureText(o.text).width;return{bits,icon,room,w1,fit:o.kind==='chip'?0:mbFit(w1,room),rect:BT.row}}finally{ctx.restore()}}
function paintBanner(c,o,t,opa){c.save();c.font='600 '+BT.font_px+'px system-ui,sans-serif';c.textBaseline='middle';c.textAlign='left';
 const L=bannerLayout(c,o),R=BT.row,chip=o.kind==='chip',vio=chip||o.icon==='remote',a=opa==null?1:opa;
 if(o.text){c.globalAlpha=.84*a;c.fillStyle='#0e1016';c.beginPath();rrPath(c,R.x,R.y,R.w,R.h,R.r);c.fill();c.globalAlpha=a;
  const hh=R.h-4,full=R.w-6-(mbStripW(L.bits)>0?mbStripW(L.bits)+6:0);let cw=full;if(chip)cw=Math.min(full,5+BT.icon_w+4+L.w1+12);
  if(chip){c.fillStyle='#302058';c.beginPath();rrPath(c,R.x+3,R.y+2,cw,hh,hh/2);c.fill();c.strokeStyle='#a070ff';c.lineWidth=1;c.beginPath();rrPath(c,R.x+3.5,R.y+2.5,cw-1,hh-1,hh/2);c.stroke()}
  bannerIcon(c,o.icon||'none',R.x+3+5,R.y+2+(hh-22)/2,vio?'#fff':(o.fg||'#fff'));
  const tx=R.x+3+(o.icon&&o.icon!=='none'?5+BT.icon_w+4:9),room=chip?cw-(tx-R.x-3)-8:L.room;
  c.fillStyle=vio?'#fff':(o.fg||'#fff');c.save();c.beginPath();c.rect(tx,R.y,room,R.h);c.clip();
  const ov=L.w1>room?L.w1-room+6:0,x=(!chip&&L.fit===1)?mbMarqueeX(Math.round(t*1000),ov):0;let txt=o.text;
  if(chip&&L.w1>room){while(txt.length>1&&c.measureText(txt+'...').width>room)txt=txt.slice(0,-1);txt+='...'}
  c.fillText(txt,tx-x,R.y+R.h/2+1);c.restore()}
 const sw=mbStripW(L.bits);let sx=R.x+R.w-BT.pad_x-sw;const sy=R.y+(R.h-18)/2;c.globalAlpha=1;
 BT.flags.forEach((n,i)=>{if(!(L.bits>>i&1))return;bannerGlyph(c,n,sx,sy,o.fg||'#fff');sx+=BT.strip.glyph_w+BT.strip.gap});
 c.restore();return L}
/* the subtitle strip: the fixed bottom zone, outlined text, centered; o = {text, size px} */
function paintSubtitles(c,text,fg,opa){c.save();const z=BT.zones.subtitles,S=BT.subtitles,px=S.font_px;c.font='600 '+px+'px system-ui,sans-serif';c.textAlign='center';c.textBaseline='middle';c.globalAlpha=opa==null?1:opa;
 const W=BT.screen_w-16,words=text.split(' '),lines=[];let cur='';for(const w of words){const tr=cur?cur+' '+w:w;if(c.measureText(tr).width<=W||!cur)cur=tr;else{lines.push(cur);cur=w}}if(cur)lines.push(cur);
 const shown=lines.slice(0,S.lines),lh=Math.round(px*1.15),top=msTextTop(shown.length,lh);
 shown.forEach((ln,i)=>{const y=top+i*lh+lh/2;c.lineJoin='round';c.lineWidth=4;c.strokeStyle='rgba(0,0,0,.85)';c.strokeText(ln,BT.screen_w/2,y);c.fillStyle=fg||'#fff';c.fillText(ln,BT.screen_w/2,y)});c.restore();return shown.length}
function bannerIcon(c,n,x,y,col){c.save();c.lineCap='round';c.lineJoin='round';c.strokeStyle=col;c.fillStyle=col;c.lineWidth=2;
 if(n==='remote'){c.strokeStyle='#a070ff';c.fillStyle='#a070ff';c.beginPath();rrPath(c,x+1,y+3,20,15,4);c.stroke();c.beginPath();c.arc(x+11,y+10.5,3,0,6.2832);c.fill()}
 else if(n==='check'){c.lineWidth=3;c.beginPath();c.moveTo(x+3,y+11);c.lineTo(x+8,y+16);c.lineTo(x+18,y+5);c.stroke()}
 else if(n==='battery'){c.beginPath();rrPath(c,x+1,y+5,17,11,3);c.stroke();c.fillRect(x+18,y+8,3,5);c.fillStyle='#ff5a50';c.fillRect(x+4,y+8,4,5)}
 else if(n==='wifi_off'||n==='bars'){for(let i=0;i<4;i++){const h=4+i*4;c.fillStyle=n==='bars'?(i<2?col:'#464c54'):'#78808c';c.fillRect(x+1+i*5,y+19-h,4,h)}if(n==='wifi_off'){c.strokeStyle='#ff5a50';c.beginPath();c.moveTo(x,y+15);c.lineTo(x+18,y+1);c.stroke()}}
 else if(n==='ring'){c.beginPath();c.arc(x+11,y+11,8,0,6.2832);c.stroke();c.beginPath();c.arc(x+11,y+11,4,0,6.2832);c.fill()}
 else if(n==='speech'){c.beginPath();rrPath(c,x+1,y+3,20,13,6);c.stroke();c.fillRect(x+5,y+15,4,4)}
 else if(n==='key'){c.beginPath();c.arc(x+6,y+11,4,0,6.2832);c.stroke();c.fillRect(x+10,y+10,11,2);c.fillRect(x+17,y+12,2,4)}
 c.restore()}
function bannerGlyph(c,n,x,y,col){c.save();c.lineCap='round';c.strokeStyle=col;c.fillStyle=col;c.lineWidth=2;
 if(n==='mic'){c.fillStyle='#ff5a50';c.strokeStyle='#ff5a50';c.beginPath();rrPath(c,x+7,y,6,10,3);c.fill();c.beginPath();c.arc(x+10,y+7,7,.1*Math.PI,.9*Math.PI);c.stroke();c.fillRect(x+9,y+13,2,4)}
 else if(n==='camera'){c.beginPath();rrPath(c,x+1,y+2,18,14,4);c.stroke();c.beginPath();c.arc(x+10,y+9,3.5,0,6.2832);c.fill()}
 else if(n==='remote'){c.fillStyle='#a070ff';c.beginPath();rrPath(c,x,y+1,20,15,4);c.fill();c.fillStyle='#302058';c.beginPath();c.arc(x+10,y+8.5,3,0,6.2832);c.fill()}
 else if(n==='battery'){c.beginPath();rrPath(c,x,y+3,17,11,3);c.stroke();c.fillRect(x+17,y+6,3,5);c.fillStyle='#ff5a50';c.fillRect(x+2,y+5,4,7)}
 else if(n==='wifi'){for(let i=0;i<4;i++){const h=4+i*3;c.fillStyle=i<3?col:'#505862';c.fillRect(x+i*5,y+16-h,4,h)}}
 c.restore()}
"""


def banner_js() -> str:
    """The banner functions with the table of the core filled in."""
    return BANNER_JS.replace("__BANNER_TABLE__", json.dumps(BANNER_TABLE, separators=(",", ":")))
