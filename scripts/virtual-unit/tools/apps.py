"""Clock, game, lock, and timer tools for the virtual unit."""
from __future__ import annotations

import base64
import calendar
import datetime as dt
import json
import re

import posixtz
from tools import tool

ZONES = [("pacific_honolulu", "Honolulu", "HST10"), ("america_anchorage", "Anchorage", "AKST9AKDT,M3.2.0,M11.1.0"),
 ("america_los_angeles", "Los Angeles", "PST8PDT,M3.2.0,M11.1.0"), ("america_denver", "Denver", "MST7MDT,M3.2.0,M11.1.0"),
 ("america_phoenix", "Phoenix", "MST7"), ("america_chicago", "Chicago", "CST6CDT,M3.2.0,M11.1.0"), ("america_mexico_city", "Mexico City", "CST6"),
 ("america_new_york", "New York", "EST5EDT,M3.2.0,M11.1.0"), ("america_bogota", "Bogota", "<-05>5"), ("america_halifax", "Halifax", "AST4ADT,M3.2.0,M11.1.0"),
 ("america_sao_paulo", "Sao Paulo", "<-03>3"), ("atlantic_azores", "Azores", "<-01>1<+00>,M3.5.0/0,M10.5.0/1"), ("utc", "UTC", "UTC0"),
 ("europe_london", "London", "GMT0BST,M3.5.0/1,M10.5.0"), ("europe_lisbon", "Lisbon", "WET0WEST,M3.5.0/1,M10.5.0"),
 ("europe_paris", "Paris", "CET-1CEST,M3.5.0,M10.5.0/3"), ("europe_berlin", "Berlin", "CET-1CEST,M3.5.0,M10.5.0/3"),
 ("europe_madrid", "Madrid", "CET-1CEST,M3.5.0,M10.5.0/3"), ("europe_rome", "Rome", "CET-1CEST,M3.5.0,M10.5.0/3"),
 ("europe_athens", "Athens", "EET-2EEST,M3.5.0/3,M10.5.0/4"), ("africa_cairo", "Cairo", "EET-2"), ("europe_moscow", "Moscow", "MSK-3"),
 ("asia_dubai", "Dubai", "<+04>-4"), ("asia_karachi", "Karachi", "PKT-5"), ("asia_kolkata", "Delhi", "IST-5:30"),
 ("asia_dhaka", "Dhaka", "<+06>-6"), ("asia_bangkok", "Bangkok", "<+07>-7"), ("asia_shanghai", "Beijing", "CST-8"),
 ("asia_tokyo", "Tokyo", "JST-9"), ("australia_sydney", "Sydney", "AEST-10AEDT,M10.1.0,M4.1.0/3"), ("pacific_auckland", "Auckland", "NZST-12NZDT,M9.5.0,M4.1.0/3")]
GAMES = [("memory", "Color memory", False), ("whack", "Whack-a-mole", False), ("tictactoe", "Tic-tac-toe", False), ("bopit", "Do It", False), ("rps", "Rock paper scissors", False), ("eightball", "Magic 8 Ball", False), ("dice", "Dice and coin", False)]  # Latest game table, patch GM06.

def app(u):
    a = u.state.setdefault("apps", {})
    a.setdefault("zone", "utc"); a.setdefault("epoch", None); a.setdefault("timers", []); a.setdefault("next_id", 1)
    a.setdefault("game", None); a.setdefault("scores", {}); a.setdefault("locked", False); a.setdefault("code", None)
    a.setdefault("keypad", False); a.setdefault("entered", ""); a.setdefault("pending_pack", "")
    a.setdefault("tones", 0); a.setdefault("saves", 0); a.setdefault("events", 0); a.setdefault("gaps", [])
    return a

def clock_reply(u, a):
    z = next((z for z in ZONES if z[0] == a["zone"]), None)
    local = ""
    if a["epoch"] is not None:
        now = a["epoch"] + u.now_ms // 1000
        off = posixtz.utc_offset(z[2], now) if z else 0  # the zone's own POSIX rule, daylight saving included
        local = dt.datetime.fromtimestamp(now + off, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    return {"ok": True, "zone": z[0] if z else "custom", "label": z[1] if z else "custom", "custom": z is None, "posix": z[2] if z else "", "clock_set": a["epoch"] is not None, "local": local}

@tool("self.clock.get")
def clock_get(u, args): return clock_reply(u, app(u))
@tool("self.clock.zones")
def clock_zones(u, args): return {"ok": True, "zones": [{"id": x, "label": y} for x,y,_ in ZONES]}
@tool("self.clock.set_zone")
def clock_zone(u, args):
    a=app(u); z=args.get("zone", "utc")
    if z not in {x[0] for x in ZONES}: return {"ok":False,"error":"that time zone is not in the list. Call self.clock.zones and choose an id."}
    a["zone"]=z; return clock_reply(u, a)
@tool("self.clock.set")
def clock_set(u, args):
    a=app(u); e=args.get("epoch",1893456000)
    if not 1704067200 <= e < 2147483647: return {"ok":False,"error":"time"}
    a["epoch"]=e; a["clock_at"]=u.now_ms; return clock_reply(u, a)

@tool("self.game.list")
def game_list(u,args):
    a=app(u); return {"ok":True,"playing":a["game"] is not None,"games":[{"id":n,"title":t,"lower_is_better":l,"scores":a["scores"].get(n,[])} for n,t,l in GAMES]}
@tool("self.game.start")
def game_start(u,args):
    a=app(u); n=args.get("name","memory")
    if n not in [g[0] for g in GAMES]: return {"ok":False,"error":"That game is not on this unit. Ask for memory, whack, tictactoe, bopit, rps, eightball or dice."}
    if a["game"]: return {"ok":False,"error":"A game is already running."}
    a["game"]={"name":n,"state":0,"ctr":[0]*8,"seq":[],"seq_pos":0,"steps":0,"finished":False}; return {"ok":True}
@tool("self.game.stop")
def game_stop(u,args): a=app(u); was=a["game"] is not None; a["game"]=None; return {"ok":True,"was":was}
@tool("self.game.scores")
def game_scores(u,args):
    a=app(u); n=args.get("name","memory"); g=next((x for x in GAMES if x[0]==n),None)
    if not g: return {"ok":False,"error":"That game is not on this unit. Ask for memory, whack, tictactoe, bopit, rps, eightball or dice."}
    return {"ok":True,"game":n,"lower_is_better":g[2],"scores":a["scores"].get(n,[])}
@tool("self.game.status")
def game_status(u,args):
    a=app(u); g=a["game"]
    # Heap counters and the live game board require hardware; fixed values are documented here.
    d={"ok":True,"active":g is not None,"tones":a["tones"],"saves":a["saves"],"internal_free":0,"psram_free":0}
    if g: d["inputs"]=a["events"]
    if g: d.update(game=g["name"],state=g["state"],ctr=g["ctr"],board="000000000",seq=g["seq"],seq_pos=g["seq_pos"],steps=g["steps"],finished=g["finished"])
    return d
@tool("self.game.bench_tap")
def game_tap(u,args):
    a=app(u); x=args.get("x",160); y=args.get("y",120)
    if x<8 or x>=312 or y<8 or y>=232:return {"ok":True,"edge":True}
    if not a["game"]:return {"ok":False,"error":"No game is running."}
    a["events"]+=1; return {"ok":True,"edge":False}
@tool("self.game.bench_event")
def game_event(u,args):
    a=app(u); event=args.get("event",5)
    if not isinstance(event,int) or not 3<=event<=11:return {"ok":False,"error":"bad_argument"}
    on=a["game"] is not None; a["events"]+=1; a["last_event"]=event; return {"ok":True,"posted":on}
@tool("self.game.bench_swipe")
def game_swipe(u,args):
    a=app(u)
    if not a["game"]:return {"ok":False,"error":"No game is running."}
    if any(k not in args for k in ("x0","y0","x1","y1","ms")):return {"ok":False,"error":"bad_argument"}
    if any(not isinstance(args[k],int) or not 0<=args[k]<=319 for k in ("x0","x1")) or any(not isinstance(args[k],int) or not 0<=args[k]<=239 for k in ("y0","y1")) or not isinstance(args["ms"],int) or not 1<=args["ms"]<=2000:return {"ok":False,"error":"bad_argument"}
    a["events"]+=1; return {"ok":True}
@tool("self.game.bench_request_stop")
def game_request_stop(u,args):
    a=app(u); asked=a["game"] is not None
    if asked:a["game"]["stop_requested"]=True
    return {"ok":True,"asked":asked}
@tool("self.game.bench_gaps")
def game_gaps(u,args):
    a=app(u); vals=a["gaps"]; a["gaps"]=[]
    def pct(p): return sorted(vals)[min(len(vals)-1,max(0,(len(vals)*p+99)//100-1))] if vals else 255
    return {"ok":True,"count":len(vals),"p50_ms":pct(50),"p99_ms":pct(99),"worst_ms":max(vals,default=0)}
@tool("self.game.bench_install")
def game_install(u,args):
    a=app(u); a["pending_pack"]+=args.get("pack","")
    if not args.get("done",True):return {"ok":True,"text":len(a["pending_pack"])}
    raw=a["pending_pack"]; a["pending_pack"]=""
    try: data=base64.b64decode(raw,validate=True)
    except Exception:return {"ok":False,"error":"The pack text is not base64. Send the pack file as base64."}
    try:
        pack=json.loads(data.decode("utf-8"))
        name=pack["name"]
        if not isinstance(name,str) or not name or len(name)>11:raise ValueError
    except Exception:return {"ok":False,"error":"The pack data is invalid. Send a valid game pack."}
    return {"ok":True,"id":name}

@tool("self.lock.status")
def lock_status(u,args): a=app(u); return {"ok":True,"has_code":a["code"] is not None,"locked":a["locked"],"auto_minutes":a.get("auto_minutes",0)}
@tool("self.lock.now")
def lock_now(u,args):
    a=app(u)
    if a["locked"]:return {"ok":True,"locked":True}
    if not a["code"]:return {"ok":False,"reason":"no_code"}
    a["locked"]=True; a["keypad"]=False; a["entered"]=""; return {"ok":True,"locked":True}
@tool("self.lock.bench_touch")
def lock_touch(u,args):
    a=app(u)
    if not a["locked"] or not a.get("ui_on",False):return {"ok":False,"reason":"not_locked"}
    if a.get("last_ring") is not None and u.now_ms-a.get("last_ring_at",-999999)<=120000:
        a["last_ring"]=None; a["last_ring_at"]=u.now_ms; return {"ok":True}
    a["keypad"]=True; a["keypad_since"]=u.now_ms; return {"ok":True}
@tool("self.lock.bench_key")
def lock_key(u,args):
    a=app(u); k=args.get("key","1")
    if not a["locked"] or not a.get("ui_on",False) or len(k)!=1:return {"ok":False,"reason":"not_locked"}
    if a["keypad"] and u.now_ms-a.get("keypad_since",u.now_ms)>=15000:a["entered"]=""; a["keypad"]=False   # the keypad goes back to the lock screen after 15 s with no key (LK_KEYPAD_TIMEOUT_MS)
    unlocked=False
    if not a["keypad"]:pass   # the keypad is not up: the core ignores the key
    elif k=="C":a["entered"]=""; a["keypad"]=False
    elif k=="B":a["entered"]=a["entered"][:-1]; a["keypad_since"]=u.now_ms
    elif k in "0123456789" and len(a["entered"])<6:
        a["keypad_since"]=u.now_ms; a["entered"]+=k
        unlocked=len(a["entered"])>=4 and a["entered"]==a["code"]    # every digit from the fourth on is checked against the code: no enter key, no early wrong
        if unlocked:a["locked"]=False; a["keypad"]=False; a["entered"]=""
        elif len(a["entered"])>=6:a["entered"]=""   # six digits and still wrong: the entry is cleared and the screen shows the wrong code look
    else: pass  # anything else is ignored, as the core does
    return {"ok":True,"unlocked":unlocked,"keypad":a["keypad"]}

def timer_add(a, due, label, silent):
    if len(a["timers"])>=8:return {"ok":False,"error":"full"}
    i=a["next_id"];a["next_id"]+=1;a["timers"].append({"id":i,"due":due,"label":label,"silent":silent,"ringing":False});return {"ok":True,"id":i}
def timer_update(a,u):
    now=u.now_ms
    for t in a["timers"]:
        if t["due"]<=now:t["ringing"]=True
@tool("self.timer.set")
def timer_set(u,args):
    a=app(u);s=args.get("seconds",1)
    if s<1:return {"ok":False,"error":"bad_argument"}
    if s>86400:return {"ok":False,"error":"too_long"}
    return timer_add(a,u.now_ms+s*1000,args.get("label",""),args.get("silent",False))
@tool("self.timer.alarm")
def timer_alarm(u,args):
    a=app(u)
    if a["epoch"] is None:return {"ok":False,"error":"no_clock"}
    h=args.get("hour",0);m=args.get("minute",0)
    if not 0<=h<=23 or not 0<=m<=59:return {"ok":False,"error":"bad_argument"}
    z=next((z for z in ZONES if z[0]==a["zone"]),None); rule=z[2] if z else "UTC0"
    now=a["epoch"]+u.now_ms//1000; local_now=now+posixtz.utc_offset(rule,now)
    cur=dt.datetime.fromtimestamp(local_now,dt.timezone.utc); target=cur.replace(hour=h,minute=m,second=0,microsecond=0)
    target_local=int(target.timestamp())
    if target_local<=local_now:target_local+=86400  # the next time the wall clock shows hh:mm
    target_utc=posixtz.local_to_utc(rule,target_local)
    return timer_add(a,u.now_ms+int(target_utc-now)*1000,args.get("label",""),args.get("silent",False))
@tool("self.timer.list")
def timer_list(u,args):
    a=app(u);timer_update(a,u);return {"clock":a["epoch"] is not None,"ringing":any(t["ringing"] for t in a["timers"]),"timers":[{"id":t["id"],"kind":"timer","left":max(0,(t["due"]-u.now_ms+999)//1000),"label":t["label"]} for t in a["timers"]]}
@tool("self.timer.cancel")
def timer_cancel(u,args):
    a=app(u);i=args.get("id",0)
    if not isinstance(i,int) or not 0<=i<=1000000:return {"ok":False,"error":"bad_argument"}
    old=len(a["timers"]);a["timers"]=[t for t in a["timers"] if i!=0 and t["id"]!=i]
    return {"ok":True} if len(a["timers"])<old else {"ok":False,"error":"not_found"}
@tool("self.timer.stop")
def timer_stop(u,args):
    a=app(u);timer_update(a,u)
    for t in a["timers"]:
        if t["ringing"]:t["ringing"]=False;a["last_ring"]=(t["label"],t["silent"]);a["last_ring_at"]=u.now_ms;return {"ok":True}
    return {"ok":False,"error":"not_ringing"}
@tool("self.timer.snooze")
def timer_snooze(u,args):
    a=app(u);s=args.get("seconds",300)
    if s<=0:return {"ok":False,"error":"bad_argument"}
    s=min(s,3600)
    last=a.get("last_ring")
    if last is None or u.now_ms-a.get("last_ring_at",-999999)>120000:return {"ok":False,"error":"not_found"}
    return timer_add(a,u.now_ms+s*1000,last[0],False)
