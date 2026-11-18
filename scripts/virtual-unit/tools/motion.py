"""Virtual handlers for motion, look, reactions and basic robot tools."""
import json
import re

from . import tool


def _state(u):
    return u.state.setdefault("motion", {"usb_limit": "limited", "force": [-1, -1, -1, -1], "lease": "", "until": 0,
        "events": [], "reminders": [], "next_id": 1, "table": None, "armed": False, "idle": False, "dance": ""})


@tool("self.look.bench_address")
def bench_address(u, args):
    return {"ok": True}


@tool("self.look.claim")
def claim(u, args):
    s=_state(u); owner=args.get("owner", ""); ttl=args.get("ttl_s", 0) or 15
    if not re.fullmatch(r"[a-z0-9._-]{1,23}", owner): return {"ok":False,"error":"owner must be 1 to 23 of a-z 0-9 dash dot underscore"}
    if s["lease"] and s["until"] > u.now_ms and s["lease"] != owner: return {"ok":False,"error":"another host holds the lease"}
    renewed=s["lease"] == owner and s["until"] > u.now_ms; s["lease"]=owner; s["until"]=u.now_ms+max(5,min(60,ttl))*1000
    return {"ok":True,"owner":owner,"ttl_s":max(5,min(60,ttl)),"renewed":renewed}


@tool("self.look.release")
def release(u,args):
    s=_state(u); owner=args.get("owner", "")
    if s["lease"] and s["until"]>u.now_ms and owner != s["lease"]: return {"ok":False,"error":"another host holds the lease"}
    if not re.fullmatch(r"[a-z0-9._-]{1,23}", owner): return {"ok":False,"error":"owner must be 1 to 23 of a-z 0-9 dash dot underscore"}
    s["lease"]=""; s["until"]=u.now_ms; return {"ok":True}


@tool("self.look.status")
def look_status(u,args):
    s=_state(u); return {"owner":"host" if s["lease"] and s["until"]>u.now_ms else "none","setting":"off","enabled":False,"state":"idle","face_ms":-1,"mover_ms":-1,"fd_track":0,"fd_moves":0,"fd_stalls":0,"fd_end":0,"sign":1,"fov_deg":0,"calibration":{}}


@tool("self.look.calibrate")
def calibrate(u,args):
    return {"ok":True,"started":True}


@tool("self.look.detect_status")
def detect_status(u,args):
    # Camera pixels are unavailable; expose the firmware status shape with a fixed empty detector.
    if args.get("detail",False): return {"ok":False,"error":"no test has run yet"}
    return {"ok":True,"built":True,"loaded":False,"model":"none","runs":0,"runs_with_face":0,"refused":0,"errors":0,"camera_busy":0,"last_infer_ms":0,"last_total_ms":0,"stream_left_ms":0,"test_state":0,"face":{"valid":False,"cx":0,"cy":0,"w":0,"score_pct":0,"age_ms":-1}}


@tool("self.look.detect_test")
def detect_test(u,args):
    model=args.get("model","") or "msrmnp"; crop=args.get("crop","") or ("center" if model=="pico224" else "full")
    if model not in ("msrmnp","pico224"): return {"ok":False,"error":"model must be msrmnp or pico224"}
    if crop not in ("full","center","follow"): return {"ok":False,"error":"crop must be full, center or follow"}
    if args.get("order","rgb") not in ("rgb","bgr",""): return {"ok":False,"error":"order must be rgb or bgr"}
    # Camera pixels and inference hardware are unavailable; report a deterministic empty result.
    return {"ok":True,"done":True,"ms":{"grab":0,"conv":0,"infer":0,"total":0,"cycle":[0,0],"first":0,"wall":0},"mem":{"before":0,"during_min":0,"after":0},"faces":0,"score_min_pct":0,"score_max_pct":0,"score_avg_pct":0,"fmt":"rgb565","window":crop}


@tool("self.look.detect_track")
def detect_track(u,args):
    s=_state(u); s["armed"]=bool(args.get("on",False)); return {"ok":True,"armed":s["armed"],"state":"idle","own":False}


@tool("self.motion.force")
def motion_force(u,args):
    s=_state(u); s["force"]=[args.get(k,-1) for k in ("carried","usb","level","orient")]; return {"ok":True}


def _motion(u):
    s=_state(u); c,b,l,o=s["force"]; carried=(c==1); usb=(b==1); level=75 if l<0 else l; orient=("upright","tilted","side","inverted","unknown")[o] if 0<=o<=4 else "upright"
    band="none" if level>=60 else "mild" if level>=40 else "limited" if level>=20 else "minimal" if level>=10 else "hold"
    state="carried" if carried or orient in ("side","inverted","unknown") else "usb_limited" if usb and s["usb_limit"]=="limited" else "battery_limited" if band!="none" else "free"
    scale,speed,dance=(0,0,0) if state=="carried" else (100,1000,4) if state=="free" else (70,600,3) if state in ("usb_limited","battery_limited") else (0,0,0)
    reasons=[]
    if carried: reasons.append("held or carried")
    if orient!="upright": reasons.append({"tilted":"tilted","side":"on its side or face down","inverted":"upside down","unknown":"no orientation reading"}[orient])
    if usb and s["usb_limit"]=="limited": reasons.append("on a USB cable")
    if not usb and band!="none": reasons.append("the battery is low")
    return {"ok":True,"state":state,"reasons":", ".join(reasons),"usb":usb,"carried":carried,"orientation":orient,"tilt_deg":0,"usb_limit":s["usb_limit"],"battery":level,"battery_band":band,"scale":scale,"speed_cap":speed,"dance_max":dance,"refused_count":0,"limited_count":0}


@tool("self.motion.status")
def motion_status(u,args): return _motion(u)


@tool("self.motion.set")
def motion_set(u,args):
    value=args.get("usb_limit","limited")
    if value not in ("limited","off"): return {"ok":False,"error":"usb_limit is limited or off"}
    _state(u)["usb_limit"]=value; return {"ok":True,"usb_limit":value}


@tool("self.reaction.get_table")
def reaction_get(u,args):
    s=_state(u); return {"ok":True,"builtin":s["table"] is None,"table":s["table"] or []}


@tool("self.reaction.set_table")
def reaction_set(u,args):
    try: rows=json.loads(args.get("table","[]"))
    except Exception: return {"ok":False,"error":"table is not a JSON list: send rows like {\"say\":\"hello\",\"face\":\"happy\"}"}
    if not isinstance(rows,list) or len(rows)>40: return {"ok":False,"error":"table must be a JSON list with at most 40 rows"}
    for row in rows:
        if not isinstance(row,dict) or not re.fullmatch(r"[A-Za-z0-9]{2,23}",str(row.get("say",""))): return {"ok":False,"error":"row phrase must be 2 to 23 letters or numbers"}
    _state(u)["table"]=rows; return {"ok":True,"builtin":False,"table":rows}


@tool("self.reaction.reset")
def reaction_reset(u,args):
    _state(u)["table"]=None; return {"ok":True,"builtin":True,"table":[]}


@tool("self.reaction.test")
def reaction_test(u,args):
    text=args.get("text","").lower()
    for row in _state(u)["table"] or []:
        if row.get("say","").lower() in text:
            return {"ok":True,"match":True,**{k:row.get(k,"") for k in ("say","face","sound","decor","dance")}}
    return {"ok":True,"match":False}


@tool("self.robot.dance")
def dance(u,args):
    name=args.get("name","happy"); valid=("happy","robot","panic","look_around","sway","nod_yes","shake_no","wiggle","bow","groove")
    if name not in valid: return {"ok":False}
    _state(u)["dance"]=name; return {"ok":True}


@tool("self.robot.dance_list")
def dance_list(u,args): return {"builtin":["happy","robot","panic","look_around"],"extra":[{"name":n,"ms":1000} for n in ("sway","nod_yes","shake_no","wiggle","bow","groove")]}


@tool("self.robot.stop_dance")
def stop_dance(u,args): _state(u)["dance"]=""; return {"ok":True}


@tool("self.robot.get_events")
def get_events(u,args):
    s=_state(u); events=s["events"]; s["events"]=[]; return {"events":events}


@tool("self.robot.set_idle_motion")
def idle(u,args): _state(u)["idle"]=bool(args.get("enabled",True)); return {"ok":True}


@tool("self.robot.create_reminder")
def reminder_create(u,args):
    s=_state(u); i=s["next_id"]; s["next_id"]+=1; item={"id":i,"duration_seconds":args.get("duration_seconds",0),"message":args.get("message",""),"repeat":args.get("repeat",False),"at_ms":u.now_ms+args.get("duration_seconds",0)*1000}; s["reminders"].append(item); return {"ok":True,"id":i}


@tool("self.robot.get_reminders")
def reminders_get(u,args): return {"reminders":_state(u)["reminders"]}


@tool("self.robot.stop_reminder")
def reminder_stop(u,args):
    s=_state(u); old=len(s["reminders"]); s["reminders"]=[r for r in s["reminders"] if r["id"]!=args.get("id")]; return {"ok":len(s["reminders"])<old}
