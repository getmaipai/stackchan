# ruff: noqa: E501
"""The face of the settings page preview: the unit's face model in JavaScript (patch V10).

The unit draws its face from ``hal/maipai_look_core.h`` (a pose per emotion, a spring, and shape lists for the eyes, the brows
and the mouth). The page draws the same model. Two things keep them from drifting apart:

* ``face_table.json`` is the table of the core (styles, the stock looks, the pose targets of every style and emotion), printed
  by ``host/tests/firmware/look_shapes_dump.c table``. A test prints it again from the firmware headers and compares.
* ``FACE_JS`` below is the code of the shape builders, ported line for line from the core. A test feeds the same inputs to the
  C core and to this JavaScript (node) for every style and checks that the shapes agree in kind, count and position.

Nothing here draws on a canvas by itself except ``paintShapes``; the Face class of the page (``settings_ui``) owns the timing.
"""

from __future__ import annotations

import json
from pathlib import Path

TABLE_PATH = Path(__file__).with_name("face_table.json")
FACE_TABLE = json.loads(TABLE_PATH.read_text())

FACE_JS = r"""
/* ---- the face model of the unit (hal/maipai_look_core.h), as shapes ---- */
const FT=__FACE_TABLE__;
const ZC=FT.zone_cy; /* the middle of the face zone (y 28 to 184): the style offsets are from here, patch N04 */
const FST={};FT.styles.forEach((s,i)=>{s.id=i;FST[s.name]=s});
const FEMO={};FT.emotions.forEach((e,i)=>{FEMO[e]=i});
const MP={EW:0,EH:1,DY:2,LID:3,SLANT:4,CHEEK:5,RSCALE:6,RLIFT:7,MCURVE:8,MOPEN:9,MW:10,MON:11,MTILT:12,MX:13,BROW:14,BLIFT:15,BTILT:16,BR:17,HEART:18,DIM:19,GX:20,GY:21,N:22};
const f01=x=>x<0?0:x>1?1:x;
function fsh(out,kind,col,opa,v){const r=[kind,col,Math.round(f01(opa)*255)];for(let i=0;i<8;i++)r.push(v[i]||0);out.push(r)}
/* an eye around its own center: kind 0 rounded box, 1 circle, 2 mask ring, 3 quad, 4 line, 5 heart; color 0 face, 1 screen, 2 highlight */
function eyeShapes(st,a){const out=[];let ew=a.ew,eh=a.eh;
 if(st.mouth===0&&a.voice>0){eh*=1+.14*a.voice;ew*=1-.04*a.voice}
 const bl=a.blink;
 if(a.heart>.02){const sz=Math.min(ew,eh)*(st.ew<=28?1.5:1.05)*a.beat;fsh(out,5,0,f01(a.heart),[0,2,sz])}
 const eyeA=1-(a.heart>a.closed?a.heart:a.closed);
 if(eyeA>.02){
  const ww=ew*(1+.06*bl),hh=Math.max(2,eh*(1-bl*.97)),sm=Math.min(ww,hh),rad=sm*.5*st.r_pct/100;
  fsh(out,0,0,eyeA,[0,0,ww,hh,rad]);
  if(st.pupil){const pr=sm*.37*(1-bl*.2);let px=a.gx*1.3,py=a.gy*1.2+hh*.02;const lim=sm*.5-pr+16,dist=Math.hypot(px,py);if(dist>lim){px*=lim/dist;py*=lim/dist}
   fsh(out,1,1,eyeA,[px,py,pr]);fsh(out,1,2,eyeA,[px-pr*.34,py-pr*.38,pr*.26]);fsh(out,1,2,eyeA,[px+pr*.38,py+pr*.34,pr*.12]);
   if(Math.hypot(px,py)+pr>sm*.5-.5)fsh(out,2,1,1,[0,0,ww,hh,rad,18])}
  const top=-hh*.5;
  if(a.lid>.005||Math.abs(a.slant)>.005){const x0=-ww*.5-3,x1=ww*.5+3,k=a.slant*hh*.45*(-a.side)/(ww*.5),y0=top+a.lid*hh+k*x0,y1=top+a.lid*hh+k*x1,T=top-6;
   if(y0>T||y1>T){let q=[x0,T,x1,T,x1,y1,x0,y0];
    if(y0<=T){const xc=x0+(T-y0)/(y1-y0)*(x1-x0);q=[xc,T,x1,T,x1,y1,xc,T]}
    else if(y1<=T){const xc=x0+(T-y0)/(y1-y0)*(x1-x0);q=[x0,T,xc,T,xc,T,x0,y0]}
    fsh(out,3,1,1,q)}}
  if(a.cheek>.01){const cyy=hh*(1.05-.45*a.cheek),rx=ww*.85,ry=hh*.55,xa=-ww*.5-3,xb=ww*.5+3,bot=hh*.5+3,N=10;let px0=xa,py0=0;
   for(let i=0;i<=N;i++){const x=xa+(xb-xa)*i/N,u=x/rx,yt=cyy-ry*Math.sqrt(1-(u*u>1?1:u*u));
    if(i>0)fsh(out,3,1,1,[px0,py0,x+.5,yt,x+.5,bot,px0,bot]);px0=x;py0=yt}}}
 if(a.closed>.02){const w=a.ew*.8;let lw=a.ew*.12;lw=lw<5?5:lw>9?9:lw;let lx=-w*.5,ly=-2;
  for(let i=1;i<=6;i++){const t=i/6,u=1-t,x=u*u*(-w*.5)+t*t*(w*.5),y=u*u*-2+2*u*t*16+t*t*-2;fsh(out,4,0,f01(a.closed),[lx,ly,x,y,lw]);lx=x;ly=y}}
 return out}
function browShapes(st,side,ew,eh,es,gx,rlift,br,on,blift,btilt){const out=[];if(on<=.02||!st.brows)return out;
 const cx=gx*.6,y=(side>0?rlift:0)-(eh*es)*.5-st.blw*2.4-blift-(side>0?br:0),len=ew*es*.78,ang=btilt*.38*(-side),ca=Math.cos(ang),sa=Math.sin(ang);
 const y0=y-len*.5*sa,y1=y+len*.5*sa,lim=FT.zone_eye_top+st.blw*.5+2-(FT.zone_cy+st.eye_y),lo=Math.min(y0,y1),push=lo<lim?lim-lo:0; /* patch N04: never above the zone's eye line */
 fsh(out,4,0,f01(on),[cx-len*.5*ca,y0+push,cx+len*.5*ca,y1+push,st.blw]);return out}
/* the mouth (patch V12): one stroke along a curve, the same pieces as the unit's ml_mouth_shapes; m = {w,bend,t,wob,split,tilt} */
const hround=x=>x<0?-Math.round(-x):Math.round(x);
function mouthPoints(m,ph){const s=m.split<0?0:m.split>1?1:m.split,ca=Math.cos(m.tilt*.0174533),sa=Math.sin(m.tilt*.0174533),out=[];
 for(let i=0;i<17;i++){const u=i/16,ux=u*2-1,x1=ux*m.w*.5,y1=m.bend*(.5-ux*ux),half=u<.5?u*2:(u-.5)*2,hx=half*2-1,x2=(u<.5?-.25:.25)*m.w+hx*m.w*.25,y2=m.bend*(.5-hx*hx);
  const x=x1+(x2-x1)*s;let y=y1+(y2-y1)*s;if(m.wob>.01)y+=m.wob*Math.sin(6.2831853*(ux*1.25+ph));
  out.push([hround(x*ca-y*sa),hround(x*sa+y*ca)])}return out}
function mouthShapes(m,ph,on){const out=[];if(on<=.02)return out;const p=mouthPoints(m,ph),t=Math.max(2,hround(m.t));
 const xs=p.map(q=>q[0]),ys=p.map(q=>q[1]),minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(...ys),maxy=Math.max(...ys);
 if(maxx-minx<Math.trunc(t/3)&&maxy-miny<Math.trunc(t/3)){fsh(out,1,0,on,[Math.trunc((minx+maxx)/2),Math.trunc((miny+maxy)/2),t*.5]);return out}
 for(let i=0;i+1<17;i++){if(p[i][0]===p[i+1][0]&&p[i][1]===p[i+1][1])continue;fsh(out,4,0,on,[p[i][0],p[i][1],p[i+1][0],p[i+1][1],t])}return out}
function mouthOf(a){return{w:a[0],bend:a[1],t:a[2],wob:a[3],split:a[4],tilt:a[5]}}
const MOUTH_TAU=90;
function mouthFollow1(c,t,dt,tau){if(tau<=0||dt>=12*tau)return t;if(dt<=0)return c;return c+(t-c)*(dt/(tau+dt))}
function mouthFollow(c,t,dt,tau){return{w:mouthFollow1(c.w,t.w,dt,tau),bend:mouthFollow1(c.bend,t.bend,dt,tau),t:mouthFollow1(c.t,t.t,dt,tau*.8),wob:mouthFollow1(c.wob,t.wob,dt,tau),split:mouthFollow1(c.split,t.split,dt,tau),tilt:mouthFollow1(c.tilt,t.tilt,dt,tau)}}
function mouthSpeaking(b,open,scale){const o=Object.assign({},b);open=open<0?0:open>1?1:open;
 const tOpen=34*scale,wOpen=12*scale;o.t=b.t+open*(tOpen-b.t);o.w=b.w+open*(wOpen-b.w);const flat=Math.min(1,open*2.2);o.bend=b.bend*(1-flat);o.split=b.split*(1-flat);o.wob=b.wob*(1-flat);return o}
function mouthYawn(b,ms){const k=(ms%6000)/6000,x=(k-.1)/.5;let open=0;if(x>0&&x<1){open=Math.sin(3.14159265*x);open*=open}const o=Object.assign({},b);o.t=b.t+open*18;o.w=b.w-open*4;return o}
/* the shape the mouth eases toward: the emotion's resting mouth scaled to the style, calm when sealed, yawning when tired, opened by the voice */
function mouthTarget(st,emo,sealed,speaking,open,ms){const kw=(sealed&&st.mouth_w===0)?1:st.mouth_w/36,kt=.5+.5*(st.mouth_t/8);  /* patch UX03a: a muted face with no mouth style draws the shut line */
 const b=mouthOf(FT.looks[emo>=0&&emo<FT.emotions.length?emo:0].stock.mouth);b.w*=kw;b.t*=kt;
 if(sealed){b.bend=0;b.wob=0;b.split=0;b.w=30*kw;b.t=5*kt}
 let t=b;if(!sealed&&emo===FEMO.tired&&!speaking)t=mouthYawn(b,ms);
 if(open>0&&!sealed)t=mouthSpeaking(t,open,st.mouth_w/46);return t}
function mouthTauFor(cur,t,speaking,open){return(t.t>cur.t&&(speaking||open>0))?40:(speaking?105:MOUTH_TAU)}
function blinkFactor(ms){if(ms<55)return ms/55;if(ms<140){const u=1-(ms-55)/85;return u*u}return 0}
function dotOf(st,i,elapsed){const period=1200,ph=(elapsed+(3-i)*400)%period,half=600,up=ph<half?ph:period-ph,k=up/half;
 if(st.stock)return[(i-1)*24,st.mouth_y-Math.round(k*5),8+Math.round(k*4),90+Math.round(k*165)];
 return[(i-1)*26,st.mouth_y-Math.round(k*8),13,89+Math.round(k*166)]}
/* the spring of the pose: k 900 (patch V20, was 420), damping ratio 0.62, sub steps of at most 8 ms, steps capped at 50 ms */
function springStep(sp,t,dt){if(dt>.05)dt=.05;const k=900,cz=2*Math.sqrt(900)*.62;
 const steps=Math.floor(dt/.008)+1,h=dt/steps;
 for(let n=0;n<steps;n++){for(let i=0;i<MP.N;i++){sp.v[i]+=(k*(t[i]-sp.x[i])-cz*sp.v[i])*h;sp.x[i]+=sp.v[i]*h;if(i===MP.LID||i===MP.CHEEK||i===MP.MON||i===MP.BROW||i===MP.HEART)sp.x[i]=f01(sp.x[i])}}}
function newSpring(t){return{x:Array.from(t),v:new Array(MP.N).fill(0)}}
function rrPath(c,x,y,w,h,r){r=Math.min(r,w/2,h/2);c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath()}
/* paint a shape list around (cx, cy): fg the face color, bg the screen color */
function paintShapes(c,sh,cx,cy,fg,bg){
 for(const s of sh){const col=s[1]===1?bg:fg,v=s.slice(3);c.globalAlpha=s[2]/255;c.fillStyle=col;c.strokeStyle=col;
  if(s[0]===0){rr(c,cx+v[0]-v[2]/2,cy+v[1]-v[3]/2,v[2],v[3],v[4]);c.fill()}
  else if(s[0]===1){c.beginPath();c.arc(cx+v[0],cy+v[1],Math.max(0,v[2]),0,6.2832);c.fill()}
  else if(s[0]===2){const b=v[5];c.beginPath();rrPath(c,cx+v[0]-v[2]/2-b,cy+v[1]-v[3]/2-b,v[2]+2*b,v[3]+2*b,v[4]+b);rrPath(c,cx+v[0]-v[2]/2,cy+v[1]-v[3]/2,v[2],v[3],v[4]);c.fill('evenodd')}
  else if(s[0]===3){c.beginPath();c.moveTo(cx+v[0],cy+v[1]);c.lineTo(cx+v[2],cy+v[3]);c.lineTo(cx+v[4],cy+v[5]);c.lineTo(cx+v[6],cy+v[7]);c.closePath();c.fill()}
  else if(s[0]===4){c.lineWidth=Math.max(1,v[4]);c.lineCap='round';c.beginPath();c.moveTo(cx+v[0],cy+v[1]);c.lineTo(cx+v[2],cy+v[3]);c.stroke()}
  else if(s[0]===5){const x=cx+v[0],y=cy+v[1],z=v[2];c.beginPath();c.moveTo(x,y+z*.48);c.bezierCurveTo(x-z*.95,y-z*.05,x-z*.52,y-z*.72,x,y-z*.22);c.bezierCurveTo(x+z*.52,y-z*.72,x+z*.95,y-z*.05,x,y+z*.48);c.closePath();c.fill()}}
 c.globalAlpha=1}
"""


def face_js() -> str:
    """The shape engine with the table of the core filled in."""
    return FACE_JS.replace("__FACE_TABLE__", json.dumps(FACE_TABLE, separators=(",", ":")))
