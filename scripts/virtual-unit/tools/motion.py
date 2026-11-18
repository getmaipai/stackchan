"""Virtual handlers for motion, look, reactions and basic robot tools."""
import json
import re

from . import tool

BUILTIN_REACTIONS = [
    {"say": "hello", "face": "happy", "sound": "none", "decor": "sparkles", "dance": "none"},
    {"say": "thanks", "face": "happy", "sound": "success", "decor": "sparkles", "dance": "none"},
    {"say": "thank you", "face": "happy", "sound": "success", "decor": "sparkles", "dance": "none"},
    {"say": "love", "face": "happy", "sound": "none", "decor": "heart", "dance": "happy"},
    {"say": "sorry", "face": "sad", "sound": "none", "decor": "sweat", "dance": "none"},
    {"say": "good night", "face": "sleepy", "sound": "goodbye", "decor": "zzz", "dance": "none"},
]


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
    if not re.fullmatch(r"[a-z0-9._-]{1,23}", owner): return {"ok":False,"error":"owner must be 1 to 23 of a-z 0-9 dash dot underscore"}
    if s["lease"] and s["until"]>u.now_ms and owner != s["lease"]: return {"ok":False,"error":"another host holds the lease"}
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
    if args.get("detail",False):
        result = _state(u).get("detect_result")
        if result is None: return {"ok":False,"error":"no test has run yet"}
        return result
    return {"ok":True,"built":True,"loaded":False,"model":"none","runs":0,"runs_with_face":0,"refused":0,"errors":0,"camera_busy":0,"last_infer_ms":0,"last_total_ms":0,"stream_left_ms":0,"test_state":0,"face":{"valid":False,"cx":0,"cy":0,"w":0,"score_pct":0,"age_ms":-1}}


@tool("self.look.detect_test")
def detect_test(u,args):
    model=args.get("model","") or "msrmnp"; crop=args.get("crop","") or ("center" if model=="pico224" else "full")
    if model not in ("msrmnp","pico224"): return {"ok":False,"error":"model must be msrmnp or pico224"}
    if crop not in ("full","center","follow"): return {"ok":False,"error":"crop must be full, center or follow"}
    if args.get("order","rgb") not in ("rgb","bgr",""): return {"ok":False,"error":"order must be rgb or bgr"}
    # Camera and memory measurements need hardware. Keep their documented zeros; do not fabricate counters.
    result = {"ok":True,"done":True,"ms":{"grab":0,"conv":0,"infer":0,"total":0,"cycle":[0,0],"first":0,"wall":0},"mem":{"before":0,"during_min":0,"after":0},"faces":0,"score_min_pct":0,"score_max_pct":0,"score_avg_pct":0,"fmt":"rgb565","window":crop}
    _state(u)["detect_result"] = result
    return result


@tool("self.look.detect_track")
def detect_track(u,args):
    s=_state(u); s["armed"]=bool(args.get("on",False)); return {"ok":True,"armed":s["armed"],"state":s.get("track_state","idle"),"own":bool(s.get("track_own",False))}


@tool("self.motion.force")
def motion_force(u,args):
    s=_state(u); s["force"]=[args.get(k,-1) for k in ("carried","usb","level","orient")]; return {"ok":True}


def _motion(u):
    s=_state(u); c,b,l,o=s["force"]; carried=(c==1); usb=(b==1); level=75 if l<0 else l; orient=("upright","tilted","side","inverted","unknown")[o] if 0<=o<=4 else "upright"
    band="none" if level>50 else "mild" if level>=30 else "limited" if level>=15 else "minimal" if level>=8 else "hold"
    state="carried" if carried or orient in ("side","inverted") else "orientation_limited" if orient in ("tilted","unknown") else "usb_limited" if usb and s["usb_limit"]=="limited" else "battery_limited" if band!="none" else "free"
    scale,speed,dance=(0,0,0) if state=="carried" else (30,400,2) if orient=="tilted" else (50,600,3) if orient=="unknown" else (100,1000,4) if state=="free" else (50,600,3) if state=="usb_limited" else (80,800,4) if band=="mild" else (50,600,3) if band=="limited" else (25,500,0) if band=="minimal" else (0,0,0)
    reasons=[]
    if carried: reasons.append("held or carried")
    if orient!="upright": reasons.append({"tilted":"tilted","side":"on its side or face down","inverted":"upside down","unknown":"no orientation reading"}[orient])
    if usb and s["usb_limit"]=="limited": reasons.append("on a USB cable")
    if not usb and band!="none": reasons.append("the battery is low")
    # Live sensor values and servo counters require firmware hardware; expose fixed documented placeholders.
    return {"ok":True,"state":state,"reasons":", ".join(reasons),"usb":usb,"carried":carried,"orientation":orient,"tilt_deg":0,"usb_limit":s["usb_limit"],"battery":level,"battery_band":band,"scale":scale,"speed_cap":speed,"dance_max":dance,"refused_count":0,"limited_count":0}


@tool("self.motion.status")
def motion_status(u,args): return _motion(u)


@tool("self.motion.set")
def motion_set(u,args):
    value=args.get("usb_limit","limited")
    if value not in ("limited","off"): return {"ok":False,"error":"usb_limit is limited or off"}
    _state(u)["usb_limit"]=value  # NVS persistence is unavailable in the virtual unit.
    return {"ok":True,"usb_limit":value}


@tool("self.reaction.get_table")
def reaction_get(u,args):
    s=_state(u); return {"ok":True,"builtin":s["table"] is None,"table":s["table"] if s["table"] is not None else BUILTIN_REACTIONS}


@tool("self.reaction.set_table")
def reaction_set(u,args):
    try: rows=json.loads(args.get("table","[]"))
    except Exception: return {"ok":False,"error":"table is not a JSON list: send rows like {\"say\":\"hello\",\"face\":\"happy\"}"}
    if not isinstance(rows,list) or len(rows)>40: return {"ok":False,"error":"table must be a JSON list with at most 40 rows"}
    allowed={"face":{"none","happy","sad","angry","doubtful","sleepy"},"sound":{"none","success","popup","goodbye","charged","needs_you","vibration"},"decor":{"none","sweat","shy","dizzy","heart","anger","tears","sparkles","stars","zzz"},"dance":{"none","happy","robot","panic","look_around"}}
    for i,row in enumerate(rows,1):
        if not isinstance(row,dict): return {"ok":False,"error":f"row {i}: the words must be 2 to 23 letters or numbers"}
        phrase=" ".join(re.findall(r"[a-z0-9]+",str(row.get("say", "")).lower()))
        if not 2 <= len(phrase) <= 23: return {"ok":False,"error":f"row {i}: the words must be 2 to 23 letters or numbers"}
        row["say"]=phrase
        for field in allowed:
            val=row.get(field,"") or "none"
            if val not in allowed[field]: return {"ok":False,"error":f"row {i}: the {field} must be a valid {field}"}
            row[field]=val
        if all(row[x]=="none" for x in allowed): return {"ok":False,"error":f"row {i}: a reaction needs at least a face, a sound, a decorator or a dance"}
        if any(existing.get("say")==phrase for existing in rows[:i-1]): return {"ok":False,"error":f"row {i}: those words are already in the table"}
    _state(u)["table"]=rows; return {"ok":True,"builtin":False,"table":rows}


@tool("self.reaction.reset")
def reaction_reset(u,args):
    _state(u)["table"]=None; return {"ok":True,"builtin":True,"table":BUILTIN_REACTIONS}


@tool("self.reaction.test")
def reaction_test(u,args):
    text=" "+" ".join(re.findall(r"[a-z0-9]+", args.get("text", "").lower()))+" "
    rows = _state(u)["table"] if _state(u)["table"] is not None else BUILTIN_REACTIONS
    matches = [r for r in rows if " " + " ".join(re.findall(r"[a-z0-9]+", r["say"].lower())) + " " in text]
    if matches:
        row=max(matches,key=lambda r:len(r["say"]))
        return {"ok":True,"match":True,"say":row["say"],**{k:row.get(k,"none") for k in ("face","sound","decor","dance")}}
    return {"ok":True,"match":False}


@tool("self.robot.dance")
def dance(u,args):
    name=args.get("name","happy"); valid=("happy","robot","panic","look_around","bob","sway","nod_yes","shake_no","wiggle","bow","groove")
    if name not in valid: return {"ok":False}
    if name in ("sway","nod_yes","shake_no","wiggle","bow","groove"):
        return {"ok":False,"error":"dance extras are unavailable in this build"}
    if _motion(u)["state"]=="carried" or _motion(u)["battery_band"] in ("minimal","hold"):
        return {"ok":False,"error":"movement is limited: put the unit upright and charge the battery"}
    sim=getattr(u,"dance",None)   # the music dance simulation (dance_sim.py); a bare test unit has none
    if name=="bob":   # patch MD01: the nod on the beat, step 2 of the ladder, until the dance is stopped
        return {"ok":bool(sim and sim.bob())}
    if sim and name in ("happy","robot","panic","look_around") and sim.start_session(name,0,45,4):   # patch SF51: a ladder session on a synthetic beat (90, 120, 140 and 80 BPM)
        return {"ok":True}
    _state(u)["dance"]=name   # muted or in full quiet: the keyframe dance as before
    if sim: sim.keyframe_start(name)
    return {"ok":True}


@tool("self.robot.dance_list")
def dance_list(u,args): return {"builtin":["happy","robot","panic","look_around"],"extra":[]}


@tool("self.robot.stop_dance")
def stop_dance(u,args):
    _state(u)["dance"]=""
    if getattr(u,"_dance",None) is not None: u.dance.stop(); u.dance.kf=None   # patch MD01: also ends the beat dance (eyes ahead, head level, ring dark)
    return {"ok":True}


@tool("self.robot.get_events")
def get_events(u,args):
    s=_state(u); events=s["events"]; s["events"]=[]; return events


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


@tool("self.bench.set_head")
def bench_set_head(u, args):
    """Bench builds: move the head whatever the idle rule says (the limiter still applies) and answer the angles read back. -9999 keeps an axis. Here it is the
    ordinary head move; hold_ms is not waited for, so the answer is the head's angles at the moment of the call."""
    move = {k: int(args[k]) for k in ("yaw", "pitch") if int(args.get(k, -9999)) != -9999}
    if "speed" in args:
        move["speed"] = int(args["speed"])
    if move:
        out = u.call("self.robot.set_head_angles", move)
        if out.get("ok") is False:
            return out
    head = u.head()
    return {"ok": True, "yaw": head["yaw"], "pitch": head["pitch"], "read_back": True}


@tool("sim.music")
def sim_music(u,args):
    """Virtual only (not a firmware tool): start, stop or change the simulated song of the music dance. action start|stop|song|status; song slow|fast|loud_peak|quiet|fades; mode home|unit; max_stage 1 to 4."""
    action=args.get("action","status"); d=u.dance
    if action=="start":
        d.start(args.get("song"),args.get("mode"),int(args.get("max_stage",4))); return {"ok":True,**d.status()}
    if action=="stop":
        d.stop(); return {"ok":True}
    if action=="song":
        try: d.song(args.get("song","fast"))
        except ValueError as e: return {"ok":False,"error":str(e)}
        return {"ok":True}
    return {"ok":True,**d.status()}


@tool("self.dance.session")
def dance_session(u,args):
    """Patch SF51: a dance session on a synthetic beat: name (happy, robot, panic, look_around) or bpm 40 to 200, seconds 10 to 120, max_stage 1 to 4."""
    name=args.get("name",""); bpm=int(args.get("bpm",100)); seconds=int(args.get("seconds",45)); stage=int(args.get("max_stage",4))
    if not name and not 40<=bpm<=200: return {"ok":False,"error":"bpm must be from 40 to 200: choose a tempo in range"}
    ok=bool(getattr(u,"dance",None) and u.dance.start_session(name,bpm,seconds,stage))
    return {"ok":True} if ok else {"ok":False,"error":"a dance may not run now: the unit is carried, its battery is very low, or it is muted or in full quiet"}
