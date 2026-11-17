# ruff: noqa: E501
"""The overlays of the settings page preview (patch O01): the unit's sizes and colors in JavaScript.

The unit draws overlays from ``hal/maipai_overlay_core.h`` (three layers, ten named combinations, every element at least as big as
the owner's arm's-length rule says). ``overlay_table.json`` is the table of that core, printed by
``host/tests/firmware/overlay_dump.c``: the names, the layer and the particle caps of each overlay, the combinations, the size of
every element and the palette. The page draws every overlay and every picker thumbnail from that table, so the preview, the
thumbnails and the unit agree; ``tests/test_overlay_preview_parity.py`` checks the table against the core and runs the drawing in
node (no browser) to check that every overlay paints and keeps its sizes.
"""

from __future__ import annotations

import json
from pathlib import Path

TABLE_PATH = Path(__file__).with_name("overlay_table.json")
OVERLAY_TABLE = json.loads(TABLE_PATH.read_text())
NAMES: tuple[str, ...] = tuple(OVERLAY_TABLE["names"])

OVERLAY_JS = r"""
/* ---- the overlays of the unit (hal/maipai_overlay_core.h): one table of sizes and colors, drawn behind the face on the 320 by 240 screen ---- */
const OT=__OVERLAY_TABLE__;
const OVN=OT.names;
const ovR=(i,j)=>{const x=Math.sin(i*127.1+j*311.7)*43758.5453;return x-Math.floor(x)};
const ovLevel=l=>({light:1,normal:2,heavy:3}[l]||2);
function ovStar(c,x,y,r){c.beginPath();c.moveTo(x,y-r);c.quadraticCurveTo(x,y,x+r,y);c.quadraticCurveTo(x,y,x,y+r);c.quadraticCurveTo(x,y,x-r,y);c.quadraticCurveTo(x,y,x,y-r);c.closePath()}
function ovHeartPath(c,x,y,s){c.beginPath();c.moveTo(x,y+s*.46);c.bezierCurveTo(x-s*.66,y+s*.02,x-s*.56,y-s*.5,x,y-s*.2);c.bezierCurveTo(x+s*.56,y-s*.5,x+s*.66,y+s*.02,x,y+s*.46);c.closePath()}
function ovZ(c,cx,cy,S,a){const o=S>=40?3:2,si=S-2*o,t=si/4,hw=t*2/3+1,x0=cx-S/2+o,y0=cy-S/2+o,P=OT.colors;
 const shapes=()=>{c.beginPath();c.rect(x0,y0,si,t);c.rect(x0,y0+si-t,si,t);c.moveTo(x0+si-1-t+hw,y0+t);c.lineTo(x0+si-1-t-hw,y0+t);c.lineTo(x0+t-1-hw,y0+si-t);c.lineTo(x0+t-1+hw,y0+si-t);c.closePath()};
 c.save();c.globalAlpha*=a;c.lineJoin='round';c.strokeStyle=P.zzz_edge;c.lineWidth=2*o;shapes();c.stroke();c.fillStyle=P.zzz;shapes();c.fill();c.restore()}
function ovCloud(c,x,y,size,dark,front,a){const w=OT.sizes.clouds[size%3],P=OT.colors,k=w/120,pal=P['cloud_'+(dark?'dark':'light')+'_'+(front?'front':'back')],S=v=>v*k;
 c.save();c.globalAlpha*=a;
 const disc=(cx,cy,r,col)=>{c.fillStyle=col;c.beginPath();c.arc(x+S(cx),y+S(cy),S(r),0,6.2832);c.fill()};
 c.fillStyle=pal[2];c.fillRect(x+S(20),y+S(54),S(84),S(8)+1);
 c.fillStyle=pal[1];c.fillRect(x+S(22),y+S(41),S(80),S(21)+1);
 disc(22,45,17,pal[1]);disc(46,32,25,pal[1]);disc(76,29,29,pal[1]);disc(102,43,19,pal[1]);
 disc(21,42,13,pal[0]);disc(45,28,20,pal[0]);disc(75,25,24,pal[0]);disc(101,40,15,pal[0]);
 c.restore()}
function ovClouds(c,tt,lvl,dark,a){const n=OT.caps.clouds[lvl-1];for(let pass=1;pass>=0;pass--)for(let i=0;i<n;i++){if((i&1)!==pass)continue;const sz=(i+Math.floor(ovR(i,9)*2))%3,w=OT.sizes.clouds[sz],sp=pass?5.5:2.6,x0=(i*(320+100))/n-90+ovR(i,1)*30,x=((x0+tt*sp+w+10)%(320+w+20))-w-10,y=pass?6+ovR(i,2)*14:-8+ovR(i,3)*12;ovCloud(c,Math.round(x/2)*2,y,sz,dark,!!pass,a)}}
function ovRain(c,tt,n,from,a){const P=OT.colors,R=OT.sizes.rain;c.save();c.lineCap='butt';for(let i=0;i<n;i++){const len=R.len[0]+ovR(i,3)*(R.len[1]-R.len[0]),vy=210+ovR(i,2)*70,x=ovR(i,1)*340,y=((ovR(i,4)*(240-from)+tt*vy)%(240-from+40))+from-len,dx=len*.13;const g=c.createLinearGradient(x+dx,y-len,x,y);g.addColorStop(0,'rgba(166,206,255,.45)');g.addColorStop(1,P.rain);c.globalAlpha=a;c.strokeStyle=g;c.lineWidth=R.width;c.beginPath();c.moveTo(x+dx,y-len);c.lineTo(x,y);c.stroke()}c.restore()}
function ovSnow(c,tt,n,from,a){const P=OT.colors,D=OT.sizes.snow;c.save();c.globalAlpha=a;for(let i=0;i<n;i++){const d=D[Math.floor(ovR(i,4)*4)%4],x=ovR(i,1)*320+Math.sin(tt*1.3+i)*(3+d/2),y=((ovR(i,2)*(240-from)+tt*(30+ovR(i,3)*28))%(240-from+16))+from;c.fillStyle=P.snow_rim;c.globalAlpha=a*.5;c.beginPath();c.arc(x,y,d/2+1,0,6.2832);c.fill();c.globalAlpha=a;c.fillStyle=P.snow;c.beginPath();c.arc(x,y,d/2,0,6.2832);c.fill();if(d>=8){c.strokeStyle=P.snow;c.lineWidth=1;c.beginPath();c.moveTo(x-d/2-2,y);c.lineTo(x+d/2+2,y);c.moveTo(x,y-d/2-2);c.lineTo(x,y+d/2+2);c.stroke()}}c.restore()}
function ovSun(c,tt,a){const S=OT.sizes.sun,P=OT.colors,turn=tt*.5;c.save();c.globalAlpha=a;c.fillStyle=P.sun_rim;c.beginPath();c.arc(S.x,S.y,S.r,0,6.2832);c.fill();c.fillStyle=P.sun;c.beginPath();c.arc(S.x,S.y,S.r-4,0,6.2832);c.fill();c.strokeStyle=P.sun_ray;c.lineCap='round';c.lineWidth=5;
 for(let k=0;k<S.rays;k++){const ang=(k+turn)*6.2832/S.rays,len=(k&1)?12:19;c.beginPath();c.moveTo(S.x+Math.cos(ang)*32,S.y+Math.sin(ang)*32);c.lineTo(S.x+Math.cos(ang)*(32+len),S.y+Math.sin(ang)*(32+len));c.stroke()}
 c.globalAlpha=a*.18;c.fillStyle=P.sun_glow;c.beginPath();c.arc(S.x,S.y,34,0,6.2832);c.fill();c.restore()}
function ovMoon(c,a){const M=OT.sizes.moon,P=OT.colors;c.save();c.globalAlpha=a;c.beginPath();c.arc(M.x,M.y,M.r,0,6.2832);c.arc(M.x+11,M.y-5,19,0,6.2832,true);c.fillStyle=P.moon;c.fill('evenodd');c.globalAlpha=a*.18;c.beginPath();c.arc(M.x,M.y,M.r+8,0,6.2832);c.fillStyle=P.moon_glow;c.fill();c.restore()}
function ovWind(c,tt,n,a){const P=OT.colors,W=OT.sizes.wind;c.save();c.lineCap='round';c.globalAlpha=a;for(let i=0;i<n;i++){const len=W[0]+ovR(i,1)*(W[1]-W[0]),x=((tt*(150+ovR(i,2)*60)+ovR(i,3)*400)%(320+len+40))-len+10,y=50+ovR(i,4)*140;
  c.strokeStyle=P.wind;c.lineWidth=2.5;c.beginPath();c.arc(x,y-8,8,.25*Math.PI,2.1*Math.PI);c.stroke();
  c.lineWidth=7;c.beginPath();c.moveTo(x-len,y+Math.sin(tt*3+i)*3);c.quadraticCurveTo(x-len/2,y-6,x,y);c.stroke();
  c.strokeStyle=P.wind2;c.lineWidth=5;c.beginPath();c.moveTo(x-len*.6-10,y+11);c.quadraticCurveTo(x-len*.3-10,y+6,x-10,y+11);c.stroke()}c.restore()}
function ovFog(c,tt,lvl,a){const P=OT.colors,base=[.5,.66,.84][lvl-1];c.save();for(let b=0;b<4;b++){const y=52+b*54,g=c.createLinearGradient(0,y-32,0,y+32);g.addColorStop(0,'rgba(224,232,242,0)');g.addColorStop(.5,'rgba(224,232,242,'+(base*a*(.75+.25*Math.sin(tt*.8+b))).toFixed(3)+')');g.addColorStop(1,'rgba(224,232,242,0)');c.fillStyle=g;c.fillRect(0,y-32,320,64)}c.restore()}
function ovStars(c,tt,n,a){const P=OT.colors,R=OT.sizes.stars;c.save();for(let i=0;i<n;i++){const tw=.45+.55*Math.abs(Math.sin(tt*1.7+i*2.3)),x=8+ovR(i,1)*304,y=8+ovR(i,2)*224;c.globalAlpha=a*tw;c.fillStyle=P.star;if(ovR(i,3)<.5){ovStar(c,x,y,R[Math.floor(tw*3.99)]);c.fill()}else{c.fillRect(x-1,y-1,3,3)}}c.restore()}
function ovDisco(c,tt,n,a){const P=OT.colors,D=OT.sizes.disco;c.save();c.globalAlpha=a;for(let i=0;i<n+2;i++){c.globalAlpha=a*.55;c.fillStyle=P.disco[i%6];c.beginPath();c.arc(30+((ovR(i,1)*260+tt*(14+ovR(i,2)*10))%260),60+Math.abs(((ovR(i,3)*150+tt*(10+ovR(i,4)*8))%300)-150),D.dots[0]+ovR(i,5)*(D.dots[1]-D.dots[0]),0,6.2832);c.fill()}
 c.globalAlpha=a;c.strokeStyle=P.string;c.lineWidth=3;c.beginPath();c.moveTo(160,0);c.lineTo(160,16);c.stroke();c.fillStyle='#c8cfdc';c.beginPath();c.arc(160,36,D.ball_r,0,6.2832);c.fill();c.fillStyle='#8f99b0';for(let k=0;k<14;k++){const ax=160+Math.cos(k*2.1)*D.ball_r*.6,ay=36+Math.sin(k*3.3)*D.ball_r*.6;c.fillRect(ax-2,ay-2,5,5)}
 for(let k=0;k<4;k++){c.globalAlpha=a*(.4+.6*Math.abs(Math.sin(tt*3+k)));c.fillStyle=P.white;ovStar(c,160+Math.cos(tt+k*1.6)*32,36+Math.sin(tt*1.2+k*2)*28,5);c.fill()}c.restore()}
function ovLeaves(c,tt,n,a){const P=OT.colors;c.save();c.globalAlpha=a;for(let i=0;i<n;i++){const x=ovR(i,1)*300+Math.sin(tt*1.4+i)*14,y=((ovR(i,2)*240+tt*(34+ovR(i,3)*22))%(240+20))-10,ang=tt*1.5+i;c.save();c.translate(x,y);c.rotate(ang);c.fillStyle=P.leaf[i%4];c.beginPath();c.moveTo(-7,0);c.quadraticCurveTo(0,-8,7,0);c.quadraticCurveTo(0,8,-7,0);c.fill();c.strokeStyle=P.leaf_vein;c.lineWidth=1.5;c.beginPath();c.moveTo(-9,0);c.lineTo(6,0);c.stroke();c.restore()}c.restore()}
function ovConfetti(c,tt,n,a){const P=OT.colors,D=OT.sizes.confetti;c.save();c.globalAlpha=a;for(let i=0;i<n;i++){const x=ovR(i,1)*300+10+Math.sin(tt*2+i)*6,y=((ovR(i,2)*260+tt*(34+ovR(i,3)*26))%(260))-12,d=D[(Math.floor(tt*4)+i)%4];c.fillStyle=P.party[i%6];c.fillRect(x-d[0]/2,y-d[1]/2,d[0],d[1])}c.restore()}
function ovFireworks(c,tt,n,a){const P=OT.colors,F=OT.sizes.fireworks;c.save();c.lineCap='round';for(let b=0;b<2;b++){const q=tt*.55+b*.5,k=Math.floor(q),ph=q%1,cx=70+ovR(b,k)*180,cy=44+ovR(b,k+7)*40,R=F.radius[0]+ovR(b,k+3)*(F.radius[1]-F.radius[0]);if(ph<.22)continue;const e=Math.min(1,(ph-.22)/.28),fade=ph<.6?1:Math.max(0,1-(ph-.6)/.4);
  for(let i=0;i<F.sparks[0];i++){const ang=i*6.2832/F.sparks[0],r=(i&1?R*.62:R)*e,x=cx+Math.cos(ang)*r,y=cy+Math.sin(ang)*r+ph*10*ph;c.globalAlpha=a*fade;c.strokeStyle=P.firework[(b*2+(i&1)*3)%6];c.lineWidth=5;c.beginPath();c.moveTo(x-Math.cos(ang)*14*(1-e*.5),y-Math.sin(ang)*14*(1-e*.5));c.lineTo(x,y);c.stroke();c.fillStyle=P.white;c.beginPath();c.arc(x,y,3,0,6.2832);c.fill()}}c.restore()}
function ovHearts(c,tt,n,a){const P=OT.colors,H=OT.sizes.hearts;c.save();for(let i=0;i<n;i++){const ph=(tt*.2+ovR(i,1))%1,s=H[i%3],x=28+ovR(i,2)*264+Math.sin(tt*1.5+i)*4,y=216-ph*200;c.globalAlpha=a*Math.min(1,ph*6,(1-ph)*4);ovHeartPath(c,x,y,s);c.fillStyle=P.heart;c.fill();c.lineWidth=2;c.strokeStyle=P.heart_edge;c.stroke();c.fillStyle=P.heart_shine;c.beginPath();c.arc(x-s*.2,y-s*.12,s*.07,0,6.2832);c.fill()}c.restore()}
function ovSparkles(c,tt,n,a){const P=OT.colors,S=OT.sizes.sparkles;c.save();for(let i=0;i<n;i++){const ph=(tt*.9+ovR(i,1)*3)%1,tri=ph<.5?ph*2:(1-ph)*2,r=3+tri*(S[0]+ovR(i,4)*(S[1]-S[0])-3),k=Math.floor(tt*.9+ovR(i,1)*3);c.globalAlpha=a;c.fillStyle=P.sparkle[i%3];ovStar(c,16+ovR(i,2+k)*288,36+ovR(i,3+k)*160,r);c.fill()}c.restore()}
function ovSteam(c,tt,n,a){const P=OT.colors;c.save();for(let i=0;i<n;i++){const ph=(tt*.3+ovR(i,1))%1,r=12+ph*22,x=(i&1?236:58)+ovR(i,2)*26+Math.sin(tt*2+i)*5,y=214-ph*100;c.globalAlpha=a*(1-ph)*.9;for(const[k,col]of[[1,P.steam_out],[.66,P.steam_mid],[.33,P.steam_in]]){c.fillStyle=col;c.beginPath();c.arc(x,y,r*k,0,6.2832);c.fill()}}c.restore()}
function ovBalloons(c,tt,n,a){const P=OT.colors;c.save();c.globalAlpha=a;for(let i=0;i<n;i++){const ph=(tt*.1+ovR(i,1))%1,x=(i&1?264:16)+ovR(i,2)*40+Math.sin(tt+i)*5,y=270-ph*320;c.fillStyle=P.balloon[i%6];c.beginPath();c.ellipse(x,y,9,11,0,0,6.2832);c.fill();c.strokeStyle='rgba(220,220,220,.7)';c.lineWidth=1;c.beginPath();c.moveTo(x,y+11);c.quadraticCurveTo(x+4,y+24,x,y+34);c.stroke()}c.restore()}
function ovZzz(c,tt,a){const Z=OT.sizes.zzz;c.save();for(let i=0;i<4;i++){const q=tt/4+i*.25,k=Math.floor(q),ph=q%1,right=(k+i)%2===0,S=ph<.3?Z.sizes[0]:ph<.65?Z.sizes[1]:Z.sizes[2],x=Z.x[right?1:0],y=Z.y[0]+2-ph*Z.rise;ovZ(c,x,y,S,a*Math.min(1,ph*9,(1-ph)*7))}c.restore()}
function ovThunder(c,tt,lvl,a){ovRain(c,tt,OT.caps.thunder[lvl-1],0,a);const ph=(tt%2.6)/2.6;if(ph<.05||(ph>.08&&ph<.11)){c.save();const g=c.createLinearGradient(0,0,0,130);g.addColorStop(0,'rgba(238,242,255,.6)');g.addColorStop(1,'rgba(238,242,255,0)');c.fillStyle=g;c.fillRect(0,0,320,130);c.restore()}if(ph<.08){const P=OT.colors,x0=70+(Math.floor(tt/2.6)*83)%180;c.save();c.lineJoin='round';c.strokeStyle=P.bolt_glow;c.globalAlpha=.5;c.lineWidth=11;c.beginPath();c.moveTo(x0,30);c.lineTo(x0-8,60);c.lineTo(x0+6,80);c.lineTo(x0-6,124);c.stroke();c.globalAlpha=1;c.strokeStyle=P.bolt;c.lineWidth=5;c.stroke();c.restore()}}
function ovPart(c,name,lvl,tt,a,combo){const caps=OT.caps[name]?OT.caps[name][lvl-1]:0;
 switch(name){case'rain':ovRain(c,tt,caps,combo?44:0,a);break;case'snow':ovSnow(c,tt,caps,combo?50:0,a);break;case'sun':ovSun(c,tt,a);break;case'clouds':ovClouds(c,tt,lvl,lvl===3,a);break;case'wind':ovWind(c,tt,caps,a);break;case'thunder':ovThunder(c,tt,lvl,a);break;case'fog':ovFog(c,tt,lvl,a);break;case'stars':ovStars(c,tt,caps,a);break;case'disco':ovDisco(c,tt,caps,a);break;case'leaves':ovLeaves(c,tt,caps,a);break;case'confetti':ovConfetti(c,tt,caps,a);break;case'fireworks':ovFireworks(c,tt,caps,a);break;case'hearts':ovHearts(c,tt,caps,a);break;case'steam':ovSteam(c,tt,caps,a);break;case'balloons':ovBalloons(c,tt,caps,a);break;case'zzz':ovZzz(c,tt,a);break;case'moon':ovMoon(c,a);break;case'sparkles':ovSparkles(c,tt,caps,a);break}}
/* draws an overlay (or a named combination) onto a context that is already scaled to the 320 by 240 screen; the caller draws the face on top */
function drawOv(c,ov,t){const tt=t-ov.t0,lvl=ovLevel(ov.intensity),a=Math.min(1,tt/.5),parts=OT.presets[ov.name];
 if(parts){const adj=ovLevel(ov.intensity)-2;parts.forEach(([n,l])=>ovPart(c,n,Math.max(1,Math.min(3,l+adj)),tt,a,true))}else ovPart(c,ov.name,lvl,tt,a,false)}
/* a picker thumbnail: the overlay behind a small face, on a canvas of any size (animated by ovThumbLoop) */
function ovThumb(cv,name,t){const d=cv.getContext('2d'),s=cv.width/320;d.setTransform(1,0,0,1,0,0);d.fillStyle='#000';d.fillRect(0,0,cv.width,cv.height);d.setTransform(s,0,0,s,0,0);
 drawOv(d,{name,intensity:'normal',t0:0},t+.9);d.fillStyle='#fff';for(const sx of[-1,1]){d.beginPath();d.ellipse(160+sx*70,92,39.5,42.5,0,0,6.2832);d.fill()}d.lineCap='round';d.strokeStyle='#fff';d.lineWidth=7;d.beginPath();d.moveTo(143,160);d.quadraticCurveTo(160,176,177,160);d.stroke()}
const ovThumbs=new Map();let ovThumbOn=false;
function ovThumbLoop(){if(ovThumbOn)return;ovThumbOn=true;let last=0;const f=now=>{if(now-last>=90&&!document.hidden){last=now;for(const[cv,nm]of ovThumbs){if(!cv.isConnected){ovThumbs.delete(cv);continue}ovThumb(cv,nm,REDUCED?3:now/1000)}}requestAnimationFrame(f)};requestAnimationFrame(f)}
"""


def overlay_js() -> str:
    """The overlay functions with the table of the core filled in."""
    return OVERLAY_JS.replace("__OVERLAY_TABLE__", json.dumps(OVERLAY_TABLE, separators=(",", ":")))
