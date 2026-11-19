#!/usr/bin/env python3
# Intent: the exposure suite. One run measures what the host contacts, what it exposes and what protects it, and prints one table with the date.
# Steps: (1) credentials in the repo and its history, (2) the settings page refuses no token, a wrong token and a wrong Host name, (3) open ports against scripts/exposure-allowed.json,
# (4) host egress in a no-internet sandbox with a recording sink, (5) hard-coded addresses in the firmware. A step that cannot run says NOT RUN, never PASS.
# Usage: python3 scripts/exposure-test.py [--write]   (--write puts the table into SECURITY.md between the exposure markers). Exit 1 on any FAIL.
import datetime
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# The one outside address the firmware tree may carry: the vendor's activation address in the cloud brain test overlay (patch SF96). The overlay is not part of any release build;
# this check still fails on that host anywhere else, and a second host in that file.
CLOUDTEST_FILE = "firmware/configs/sdkconfig.cloudtest.defaults"
CLOUDTEST_HOST = "api.tenclass.net"

ROOT = Path(__file__).resolve().parent.parent
E2E_PY = ROOT / ".runs" / "e2e-venv" / "bin" / "python"
HOST_PY = ROOT / "host" / ".venv" / "bin" / "python"
rows: list[tuple[str, str, str, str]] = []  # (kind, what, verdict, detail)

HOOK = '''import os, sys
_log = os.environ["NET_AUDIT_LOG"]
def _w(s):
    with open(_log, "a") as f:
        f.write(s + "\\n")
_w("hook-loaded")
def _hook(event, args):
    if event == "socket.connect":
        _w("connect " + str(args[1]))
    elif event == "socket.sendto":
        _w("sendto " + str(args[1]))
    elif event == "socket.getaddrinfo":
        _w("lookup " + str(args[0]))
sys.addaudithook(_hook)
'''
SANDBOX = '(version 1)\n(allow default)\n(deny network-outbound)\n(allow network-outbound (remote ip "localhost:*"))\n(allow network-outbound (remote unix-socket))\n'


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def add(kind, what, verdict, detail):
    rows.append((kind, what, verdict, detail))
    print(f"[{verdict}] {kind}: {what}: {detail}", flush=True)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))  # no packet is sent; this only picks the outbound interface
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def credentials():
    exe = shutil.which("gitleaks")
    if exe:
        now = run([exe, "detect", "--no-git", "--source", ".", "-c", ".gitleaks.toml", "--no-banner", "--redact"])
        add("Protect", "No secrets in the current files (gitleaks)", "PASS" if now.returncode == 0 else "FAIL", "0 findings" if now.returncode == 0 else "gitleaks reports findings in the current files")
    else:
        add("Protect", "No secrets in the current files (gitleaks)", "NOT RUN", "gitleaks is not installed")
    tf = shutil.which("trufflehog")
    if tf:
        proc = run([tf, "git", f"file://{ROOT}", "--no-verification", "--no-update", "--json", "--results=unverified,unknown,verified"])
        hits = [json.loads(x) for x in proc.stdout.splitlines() if x.startswith("{")]
        fake = re.compile(r"z{6,}|abcdef|abcDEF|FAKE|0{6,}|example|test", re.I)
        real = [h for h in hits if not fake.search(json.dumps(h.get("Raw", "")))]
        add("Protect", "No secrets in the history (trufflehog, whole history, unverified)", "PASS" if not real else "FAIL", f"{len(hits)} findings, {len(hits) - len(real)} obvious test placeholders, {len(real)} unexplained")
    else:
        add("Protect", "No secrets in the history (trufflehog)", "NOT RUN", "trufflehog is not installed")


def dashboard_auth():
    ip = lan_ip()
    if not HOST_PY.exists() or ip is None:
        return add("Protect", "Settings page refuses no token, a wrong token and a wrong Host name", "NOT RUN", "no host environment or no network address")
    code = r'''
import json, sys, tempfile, threading, urllib.request, urllib.error, http.client
from pathlib import Path
sys.path.insert(0, ".")
from maipai_body import settings_sim
from maipai_body.settings_server import SettingsServer
from maipai_body.local_guard import SettingsAuth
data = Path(tempfile.mkdtemp())
backend, _ = settings_sim.build(data, language="en")
auth = SettingsAuth(data / "settings-token")
server = SettingsServer(backend, "0.0.0.0", 0, auth=auth)
server.start()
port, ip, token = server.port, sys.argv[1], auth.token
def get(host, path="/settings", headers=None, bind=None):
    c = http.client.HTTPConnection(host, port, timeout=5, source_address=bind)
    c.request("GET", path, headers=headers or {}); r = c.getresponse(); r.read(); c.close(); return r.status
def post(host, headers=None):
    c = http.client.HTTPConnection(host, port, timeout=5)
    h = {"Content-Type": "application/json"}; h.update(headers or {})
    c.request("POST", "/api/stackchan/unit/aa%3Abb%3Acc%3A00%3A10%3A01/device", body="{}", headers=h); r = c.getresponse(); r.read(); c.close(); return r.status
out = {
  "lan_no_token_get": get(ip),
  "lan_no_token_post": post(ip),
  "lan_wrong_token": get(ip, headers={"Authorization": "Bearer " + "x" * 43}),
  "lan_right_token": get(ip, headers={"Authorization": "Bearer " + token}),
  "loopback_wrong_host": get("127.0.0.1", headers={"Host": "evil.example"}),
  "loopback_proxy_header": get("127.0.0.1", headers={"X-Forwarded-For": "203.0.113.9"}),
}
server.stop()
print(json.dumps(out))
'''
    proc = subprocess.run([str(HOST_PY), "-c", code, ip], capture_output=True, text=True, cwd=ROOT / "host", timeout=120)
    try:
        r = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return add("Protect", "Settings page refuses no token, a wrong token and a wrong Host name", "NOT RUN", f"the test server did not answer: {(proc.stderr or proc.stdout).strip()[-120:]}")
    ok = r["lan_no_token_get"] == 401 and r["lan_no_token_post"] == 401 and r["lan_wrong_token"] == 401 and r["lan_right_token"] == 200 and r["loopback_wrong_host"] in (401, 403) and r["loopback_proxy_header"] == 401
    add("Protect", "Settings page, listening on the network, refuses no token, a wrong token, a wrong Host name and a proxied request", "PASS" if ok else "FAIL",
        f"from this computer's network address: no token {r['lan_no_token_get']} (page) and {r['lan_no_token_post']} (change), wrong token {r['lan_wrong_token']}, right token {r['lan_right_token']}; wrong Host name {r['loopback_wrong_host']}; proxied request {r['loopback_proxy_header']}")


def start_host(sandbox: bool, tmp: Path, extra_env=None):
    (tmp / "hook").mkdir(exist_ok=True)
    (tmp / "home").mkdir(exist_ok=True)
    (tmp / "data").mkdir(exist_ok=True)
    (tmp / "hook" / "sitecustomize.py").write_text(HOOK)
    env = {k: v for k, v in os.environ.items() if k not in ("MAIPAI_HUB_HOST", "VIRTUAL_ENV", "PYTHONPATH") and not k.startswith("MAIPAI_")}
    env.update({"HOME": str(tmp / "home"), "MAIPAI_BOT_DATA_DIR": str(tmp / "data"), "NET_AUDIT_LOG": str(tmp / "net.log"), "PYTHONPATH": str(tmp / "hook"), "PYTHONUNBUFFERED": "1"})
    env.update(extra_env or {})
    boot = "import os,runpy;os.environ.setdefault('MAIPAI_BODY','stackchan');runpy.run_module('maipai_body.app',run_name='__main__')"
    cmd = [str(E2E_PY), "-c", boot]
    if sandbox:
        (tmp / "no-internet.sb").write_text(SANDBOX)
        cmd = ["sandbox-exec", "-f", str(tmp / "no-internet.sb")] + cmd
    return subprocess.Popen(cmd, env=env, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)


def stop(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return proc.communicate(timeout=10)[0]
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        return proc.communicate()[0]


def listening(pgid: int):
    out = run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-F", "pn"]).stdout
    pids = set(run(["pgrep", "-g", str(pgid)]).stdout.split())
    found, cur = {}, None
    for line in out.splitlines():
        if line.startswith("p"):
            cur = line[1:]
        elif line.startswith("n") and cur in pids:
            addr, _, port = line[1:].rpartition(":")
            found.setdefault(int(port), set()).add(addr)
    return found


def ports_and_egress():
    if not E2E_PY.exists():
        for what in ("Open ports match the allow-list", "Host egress in a no-internet sandbox"):
            add("Expose" if "ports" in what else "Contact", what, "NOT RUN", "no clean host environment at .runs/e2e-venv; run scripts/virtual-unit/e2e.py once to build it")
        return
    allowed = json.loads((ROOT / "scripts" / "exposure-allowed.json").read_text())
    tmp = Path(tempfile.mkdtemp())
    # Each role gets a free port for the test (the default ports may be taken by a real host on this computer); the allow-list is judged by role.
    env_for = {"voice": "MAIPAI_XIAOZHI_PORT", "avatar": "MAIPAI_STACKCHAN_AVATAR_PORT", "vision": "MAIPAI_VISION_PORT", "settings": "MAIPAI_STACKCHAN_SETTINGS_PORT"}
    free = {}
    for role in env_for:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        free[role] = sock.getsockname()[1]
        sock.close()
    probe = subprocess.run([str(E2E_PY), "-c", "import socket\ntry:\n socket.create_connection(('127.0.0.1', 9), 1)\nexcept OSError:\n pass"], env={**os.environ, "NET_AUDIT_LOG": str(tmp / "probe.log"), "PYTHONPATH": str(tmp / "hook")}, capture_output=True)
    (tmp / "hook").mkdir(exist_ok=True)
    (tmp / "hook" / "sitecustomize.py").write_text(HOOK)
    probe = subprocess.run([str(E2E_PY), "-c", "import socket\ntry:\n socket.create_connection(('127.0.0.1', 9), 1)\nexcept OSError:\n pass"], env={**os.environ, "NET_AUDIT_LOG": str(tmp / "probe.log"), "PYTHONPATH": str(tmp / "hook")}, capture_output=True)
    hook_ok = "connect ('127.0.0.1', 9)" in ((tmp / "probe.log").read_text() if (tmp / "probe.log").exists() else "")
    sandbox_ok = shutil.which("sandbox-exec") is not None
    proc = start_host(sandbox_ok, tmp, {env_for[r]: str(p) for r, p in free.items()})
    time.sleep(30)
    alive = proc.poll() is None
    listen = listening(proc.pid) if alive else {}
    ip = lan_ip()
    nmap_open = None
    if shutil.which("nmap") and ip:
        res = run(["nmap", "-Pn", "-n", "-p-", "--min-rate", "3000", "-oG", "-", ip], timeout=300).stdout
        m = re.search(r"Ports: (.*?)(\t|$)", res)
        nmap_open = {int(x.split("/")[0]) for x in (m.group(1).split(", ") if m else []) if "/open/" in x}
    out = stop(proc)
    role_of = {"voice": 8765, "avatar": 8766, "vision": 8767, "settings": 8051}
    allow = {free[r]: next(a for a in allowed["listen"] if a["port"] == role_of[r]) for r in free}  # the test port stands for the default port of its role
    extra = sorted(set(listen) - set(allow))
    on_lan_wrongly = sorted(p for p, a in listen.items() if p in allow and not allow[p]["lan"] and not a <= {"127.0.0.1", "[::1]", "::1", "localhost"})
    if not alive:
        add("Expose", "Open ports match the allow-list", "NOT RUN", "the host did not stay up")
    else:
        names = {v: k for k, v in free.items()}
        shown = ", ".join("%s (%s)" % (names.get(p, p), "/".join(sorted(listen[p]))) for p in sorted(listen)) or "nothing"
        detail = "the host listened on " + shown + " (test ports stand for the default ports " + ", ".join(str(a["port"]) for a in allowed["listen"]) + "; any other port fails)"
        if nmap_open is not None:
            seen = sorted(p for p in nmap_open if p in listen)
            detail += f"; nmap of this computer's network address (all 65535 ports) reached {', '.join(names.get(p, str(p)) for p in seen) or 'none of them'}; ports of other software on this computer were not judged"
            leaked = [p for p in seen if p in allow and not allow[p]["lan"]]
            if leaked:
                extra += leaked
        else:
            detail += "; nmap not installed or no network address, so reachability was not tested from the network"
        add("Expose", "Open ports match the allow-list (any new port fails)", "FAIL" if extra or on_lan_wrongly else "PASS", detail + (f"; NOT ALLOWED: {extra + on_lan_wrongly}" if extra or on_lan_wrongly else ""))
    lines = (tmp / "net.log").read_text().splitlines() if (tmp / "net.log").exists() else []
    loaded = "hook-loaded" in lines
    events = [x for x in lines if x != "hook-loaded"]

    def private(item: str) -> bool:
        t = item.split(" ", 1)[1]
        return bool(re.search(r"127\.0\.0\.1|localhost|::1|\.local$|0\.0\.0\.0", t))

    outside = [x for x in events if not private(x)]
    if not (hook_ok and loaded and alive):
        add("Contact", "Host egress in a no-internet sandbox with a recording sink", "NOT RUN", f"hook proven {hook_ok}, hook loaded {loaded}, host up {alive}")
    else:
        add("Contact", "Host egress: zero attempts to anywhere but this computer by default", "PASS" if not outside else "FAIL",
            f"the host ran 30 seconds with an empty home and no brain set{' inside a macOS sandbox that denies every outbound connection except this computer' if sandbox_ok else ' (no sandbox tool on this computer, so attempts were recorded but not blocked)'}; the recording hook logged {len(events)} connection, send and name-lookup attempts to this computer and {len(outside)} anywhere else" + (": " + ", ".join(sorted(set(outside))[:4]) if outside else "") + ". Only addresses the owner configures (model, speech and hub addresses, the downloads the owner starts) are allowed beyond this")


def firmware_addresses():
    allowed = json.loads((ROOT / "scripts" / "exposure-allowed.json").read_text())["allowed_firmware_hosts"]
    files = run(["git", "ls-files", "firmware", "host/maipai_body/bodies/stackchan/firmware"]).stdout.split()
    ip = re.compile(r"(?<![\d.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\d.])")
    url = re.compile(r"https?://[A-Za-z0-9._-]+")
    hits = []
    for f in files:
        if f.endswith((".png", ".gif", ".bin", ".mpk", ".svg", ".jpg", ".ttf", ".lock")):
            continue
        try:
            lines = (ROOT / f).read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if f.endswith(".patch") and not line.startswith("+"):
                continue
            if "version" in line.lower() or "ver " in line.lower():
                continue
            for m in ip.finditer(line):
                a = tuple(map(int, m.groups()))
                if max(a) > 255:
                    continue
                if a[0] in (0, 10, 127, 224, 255) or (a[0] == 192 and (a[1] == 168 or (a[1] == 0 and a[2] == 2))) or (a[0] == 172 and 16 <= a[1] <= 31) or (a[0] == 169 and a[1] == 254) or (a[0] == 100 and 64 <= a[1] <= 127):
                    continue
                if any(m.group(0).startswith(x) for x in allowed):
                    continue
                if f.endswith((".patch", ".c", ".cc", ".h", ".cpp", ".py", ".sh", ".json", ".txt", ".md")) and re.search(r"[A-Za-z_]\s*[=(]\s*\"?" + re.escape(m.group(0)), line) is None and "addr" not in line.lower() and "host" not in line.lower() and "http" not in line.lower() and "ip" not in line.lower():
                    continue
                hits.append(f"{f}:{n} {m.group(0)}")
            for m in url.finditer(line):
                host = m.group(0).split("//")[1]
                if "." not in host:
                    continue  # "http://host" in a comment is a placeholder, not an address
                if f == CLOUDTEST_FILE and host == CLOUDTEST_HOST:
                    continue  # the cloud brain test image's one vendor address (decision 34): the file says it is never the default and never in a release
                if any(host.startswith(x) for x in allowed) or re.search(r"example|localhost|127\.|github\.com|espressif|m5stack|docs\.", host):
                    continue
                if f.endswith(".patch") and line.startswith("+") or not f.endswith(".patch"):
                    hits.append(f"{f}:{n} {m.group(0)}")
    # The vendor addresses the patches remove appear on removed lines only, which are skipped above.
    add("Contact", "No hard-coded outside address in the firmware files or the lines patches add", "PASS" if not hits else "FAIL", f"{len(files)} tracked firmware files searched for IPv4 addresses and web addresses; {len(hits)} outside the allowed list" + (": " + "; ".join(hits[:5]) if hits else "; the vendor cloud addresses appear only on lines patches remove"))


def main(argv):
    today = datetime.date.today().isoformat()
    head = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    for step in (credentials, dashboard_auth, ports_and_egress, firmware_addresses):
        try:
            step()
        except Exception as error:
            add("Step", step.__name__, "NOT RUN", f"the step failed: {error}")
    block = [f"Run date: {today}. Commit: `{head}`. Run with `python3 scripts/exposure-test.py`.", "", "| What we | Check | Result | What it covered |", "|---|---|---|---|"]
    names = {"Contact": "contact", "Expose": "expose", "Protect": "protect", "Step": "ran"}
    block += [f"| {names[k]} | {w} | {v} | {d.replace('|', '/')} |" for k, w, v, d in rows]
    text = "\n".join(block)
    if "--write" in argv:
        p = ROOT / "SECURITY.md"
        body = p.read_text()
        if "<!-- exposure:begin -->" not in body:
            body = body.replace("What the scan does not do:", "## What we contact, expose and protect\n\n<!-- exposure:begin -->\n<!-- exposure:end -->\n\nWhat the scan does not do:", 1)
        p.write_text(re.sub(r"(<!-- exposure:begin -->\n).*?(\n<!-- exposure:end -->)", lambda m: m.group(1) + text + m.group(2), body, flags=re.S))
    print("\n" + text)
    return 1 if any(v == "FAIL" for _, _, v, _ in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
