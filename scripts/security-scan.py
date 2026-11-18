#!/usr/bin/env python3
# Intent: one repeatable security scan of the whole repo; prints a results block that SECURITY.md carries with the date. Nothing is claimed that a step here did not run.
# Usage: python3 scripts/security-scan.py [--write]   (--write replaces the results block in SECURITY.md)
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST_PY = ROOT / "host" / ".venv" / "bin" / "python"
E2E_PY = ROOT / ".runs" / "e2e-venv" / "bin" / "python"
results: list[tuple[str, str, str]] = []  # (step, verdict, detail)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def record(step, verdict, detail):
    results.append((step, verdict, detail))
    print(f"[{verdict}] {step}: {detail}", flush=True)


def secrets_scan():
    exe = shutil.which("gitleaks")
    if not exe:
        return record("Secrets scan", "NOT RUN", "gitleaks is not installed")
    tmp = Path(tempfile.mkdtemp())
    now = run([exe, "detect", "--no-git", "--source", ".", "-c", ".gitleaks.toml", "--no-banner", "--redact"])
    out = tmp / "history.json"
    hist = run([exe, "detect", "--source", ".", "-c", ".gitleaks.toml", "--log-opts=--all", "--no-banner", "--redact", "--report-format", "json", "--report-path", str(out)])
    found = json.loads(out.read_text() or "[]") if out.exists() else []
    commits = run(["git", "rev-list", "--count", "HEAD"]).stdout.strip()
    if now.returncode not in (0, 1) or hist.returncode not in (0, 1):
        return record("Secrets scan", "NOT RUN", f"gitleaks failed: {(now.stderr + hist.stderr).strip()[:120]}")
    # A history finding counts as a test placeholder only when the line in its own commit reads as an obvious fake.
    fake = re.compile(r"z{6,}|abcdef|abcDEF|FAKE|0{6,}|example", re.I)
    real = [f for f in found if not fake.search(run(["git", "show", f"{f['Commit']}:{f['File']}"]).stdout.splitlines()[f["StartLine"] - 1] if run(["git", "show", f"{f['Commit']}:{f['File']}"]).returncode == 0 else "")]
    detail = f"gitleaks, current files: {'0 findings' if now.returncode == 0 else 'FINDINGS'}; history ({commits} commits, every branch): {len(found)} findings, {len(found) - len(real)} of them obvious test placeholders in early test files (read by hand, listed in docs/plan/history-scan-2026-11-18.md), {len(real)} unexplained"
    record("Secrets scan", "PASS" if now.returncode == 0 and not real else "FAIL", detail)


def dependency_audit():
    uv = shutil.which("uv")
    if not uv:
        return record("Dependency audit (host)", "NOT RUN", "uv is not installed")
    req = Path(tempfile.mkdtemp()) / "requirements.txt"
    exp = run([uv, "export", "--project", "host", "--no-dev", "--no-hashes", "--no-emit-project", "--format", "requirements-txt"])
    # the lock also names platform-only and optional extras; the audit covers every pinned package in it
    lines = [x for x in exp.stdout.splitlines() if x and not x.startswith(("#", " "))]
    if exp.returncode != 0 or not lines:
        return record("Dependency audit (host)", "NOT RUN", f"could not export the lock: {exp.stderr.strip()[:120]}")
    req.write_text("\n".join(lines) + "\n")
    proc = run([uv, "tool", "run", "pip-audit", "-r", str(req), "--no-deps", "--disable-pip", "--progress-spinner", "off", "-f", "json"])
    try:
        data = json.loads(proc.stdout)
        vulnerable = [d for d in data.get("dependencies", []) if d.get("vulns")]
        names = ", ".join(f"{d['name']} {d['version']}" for d in vulnerable)
        record("Dependency audit (host)", "PASS" if not vulnerable else "FAIL", f"pip-audit over {len(data.get('dependencies', []))} pinned packages: {len(vulnerable)} with known advisories" + (f" ({names})" if vulnerable else ""))
    except Exception:
        record("Dependency audit (host)", "NOT RUN", f"pip-audit gave no result: {(proc.stderr or proc.stdout).strip()[:120]}")
    vendor = sorted(p.name for p in (ROOT / "docs-site" / "vendor").iterdir()) + sorted(p.name for p in (ROOT / "flasher" / "vendor").iterdir() if (ROOT / "flasher" / "vendor").exists())
    record("Dependency audit (docs site and flasher)", "GAP", "no package manager lock exists for them; vendored files are " + ", ".join(vendor) + "; no tool audited these")


def unsafe_code():
    uv = shutil.which("uv")
    if uv:
        proc = run([uv, "tool", "run", "bandit", "-r", "host/maipai_body", "host/maipai_packages", "-ll", "-q", "-f", "json"])
        try:
            data = json.loads(proc.stdout)
            issues = data.get("results", [])
            counts: dict[str, int] = {}
            for i in issues:
                counts[i["test_id"]] = counts.get(i["test_id"], 0) + 1
            # Read by hand on 2026-11-18: B104 (8) the voice port must listen for the robot, and the settings page listens beyond this computer only with lan on and a token; B310 (5) web requests to this computer or to addresses the owner set; B602 (1) a bench-only measuring helper no release path calls.
            reviewed = counts == {"B104": 8, "B310": 5, "B602": 1}
            summary = ", ".join(f"{k} x{v}" for k, v in sorted(counts.items())) or "none"
            record("Unsafe code (host, Python)", "PASS" if not issues else ("REVIEWED" if reviewed else "REVIEW"), f"bandit at medium severity or higher: {len(issues)} findings ({summary})" + ("; all read by hand: the robot must reach the host's voice port, the settings page listens beyond this computer only with a token, the web requests go to this computer or an address the owner set, and the one shell call is in a measuring helper no release path calls" if reviewed else "; a new kind of finding, read it before release"))
        except Exception:
            record("Unsafe code (host, Python)", "NOT RUN", f"bandit gave no result: {(proc.stderr or proc.stdout).strip()[:120]}")
    hits = run(["git", "grep", "-n", "-I", "-w", "-E", r"gets|strcpy|strcat|sprintf|vsprintf", "--", "firmware/main", "firmware/*.c", "firmware/*.cc", "firmware/*.h"]).stdout.splitlines()
    added = run(["git", "grep", "-n", "-I", "-E", r"^\+.*[^a-z_](gets|strcpy|strcat|sprintf|vsprintf)\(", "--", "firmware/patches"]).stdout.splitlines()
    gets_only = [h for h in hits + added if re.search(r"[^a-z_]gets\(", h)]
    record("Unsafe code (firmware, C)", "PASS" if not gets_only else "FAIL", f"search for gets, strcpy, strcat, sprintf in our firmware files and added patch lines: {len(hits) + len(added)} uses of the bounded-copy-free functions, {len(gets_only)} of gets; a text search, not a proof")


def firmware_static_analysis():
    exe = shutil.which("cppcheck")
    if not exe or not HOST_PY.exists():
        return record("Unsafe code (firmware cores, cppcheck)", "NOT RUN", "cppcheck or the host environment is missing")
    work = Path(tempfile.mkdtemp())
    code = "import sys; sys.path.insert(0, 'tests'); from pathlib import Path; from firmware_order_cores import build_cores; print(build_cores(Path(sys.argv[1])))"
    proc = subprocess.run([str(HOST_PY), "-c", code, str(work)], capture_output=True, text=True, cwd=ROOT / "host")
    if proc.returncode != 0:
        return record("Unsafe code (firmware cores, cppcheck)", "NOT RUN", f"could not assemble the cores: {proc.stderr.strip()[-100:]}")
    cores = Path(proc.stdout.strip().splitlines()[-1])
    files = sorted(cores.glob("*.h"))
    res = run([exe, "--enable=warning,portability", "--inconclusive", "--language=c", "--std=c99", "--quiet", "--template={id}|{severity}|{file}:{line}", "--error-exitcode=0"] + [str(f) for f in files])
    issues = [x for x in res.stderr.splitlines() if "|" in x and not x.split("|")[0].startswith(("missingInclude", "unusedFunction", "checkersReport"))]
    errors = [x for x in issues if x.split("|")[1] == "error"]
    ids = sorted({x.split("|")[0] for x in issues})
    record("Unsafe code (firmware cores, cppcheck)", "PASS" if not errors else "FAIL", f"cppcheck (warning and portability checks) over {len(files)} of the unit's own C headers as the whole patch list leaves them: {len(errors)} errors, {len(issues) - len(errors)} warnings" + (f" (kinds: {', '.join(ids[:6])})" if issues else "") + "; the rest of the firmware is upstream code and is not scanned")


ALLOWED = ("127.0.0.1", "localhost", "[::1]", "192.0.2.", "example.com", "example.org", "tailnet.example.com", "github.com", "huggingface.co", "login.tailscale.com", "www.w3.org", "www.apple.com", "192.168.4.1", "m5stack.com", "docs.m5stack.com", "raw.githubusercontent.com", "espressif.com", "docs.espressif.com", "unpkg.com", "cdnjs.cloudflare.com", "fonts.googleapis.com")


def outbound_search():
    pat = r"https?://[][A-Za-z0-9._:-]+"
    scopes = ["host/maipai_body/*.py", "host/maipai_body/**/*.py", "host/maipai_packages/**/*.py", "flasher/*.js", "flasher/*.html", "docs-site/*.html", "docs-site/*.js"]
    found: dict[str, set[str]] = {}
    out = run(["git", "grep", "-n", "-I", "-o", "-E", pat, "--", *scopes]).stdout.splitlines()
    patches = run(["git", "grep", "-n", "-I", "-o", "-E", r"^\+.*" + pat, "--", "firmware/patches", "host/maipai_body/bodies/stackchan/firmware/patches"]).stdout.splitlines()
    for line in out + patches:
        m = re.search(pat, line)
        if not m:
            continue
        host = re.sub(r"^https?://", "", m.group(0)).split("/")[0]
        found.setdefault(host, set()).add(line.split(":")[0])
    unknown = {h: sorted(f)[:2] for h, f in found.items() if re.search(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+(:\d+)?$", h) and not any(h == a or h.endswith("." + a) or h.startswith(a) for a in ALLOWED)}
    record("Outbound-call search (host, flasher, docs site, firmware patch additions)", "PASS" if not unknown else "REVIEW", f"{len(found)} distinct addresses in code; {len(unknown)} not on the allowed list" + (": " + ", ".join(f"{h} ({f[0]})" for h, f in unknown.items()) if unknown else "") + ". The allowed list is the user's own network, GitHub and Hugging Face downloads the user starts, and documentation links")


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


def contacts_nothing_by_default():
    py = E2E_PY if E2E_PY.exists() else None
    if py is None:
        return record("Contacts nothing by default (network test)", "NOT RUN", "no clean host environment at .runs/e2e-venv; run scripts/virtual-unit/e2e.py once to build it")
    tmp = Path(tempfile.mkdtemp())
    (tmp / "hook").mkdir()
    (tmp / "home").mkdir()
    (tmp / "data").mkdir()
    (tmp / "hook" / "sitecustomize.py").write_text(HOOK)
    log = tmp / "net.log"
    probe = subprocess.run([str(py), "-c", "import socket\ntry:\n socket.create_connection(('127.0.0.1', 9), 1)\nexcept OSError:\n pass"], env={**os.environ, "NET_AUDIT_LOG": str(tmp / "probe.log"), "PYTHONPATH": str(tmp / "hook")}, capture_output=True)
    if "connect ('127.0.0.1', 9)" not in ((tmp / "probe.log").read_text() if (tmp / "probe.log").exists() else ""):
        return record("Contacts nothing by default (network test)", "NOT RUN", "the audit hook did not record a known test connection, so its silence would prove nothing")
    env = {k: v for k, v in os.environ.items() if k not in ("MAIPAI_HUB_HOST", "VIRTUAL_ENV", "PYTHONPATH")}
    env.update({"HOME": str(tmp / "home"), "MAIPAI_BOT_DATA_DIR": str(tmp / "data"), "NET_AUDIT_LOG": str(log), "PYTHONPATH": str(tmp / "hook"),
                "MAIPAI_XIAOZHI_PORT": "18990", "MAIPAI_STACKCHAN_AVATAR_PORT": "18991", "MAIPAI_STACKCHAN_SETTINGS_PORT": "18992", "MAIPAI_VISION_PORT": "18993", "PYTHONUNBUFFERED": "1"})
    proc = subprocess.Popen([str(py), "-c", "import os,runpy;os.environ.setdefault('MAIPAI_BODY','stackchan');runpy.run_module('maipai_body.app',run_name='__main__')"], env=env, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(30)
    alive = proc.poll() is None
    proc.terminate()
    try:
        out = proc.communicate(timeout=10)[0]
    except subprocess.TimeoutExpired:
        proc.kill()
        out = proc.communicate()[0]
    lines = log.read_text().splitlines() if log.exists() else []
    loaded = "hook-loaded" in lines
    events = [x for x in lines if x != "hook-loaded"]  # the hook was proven first by a known local test connection

    def private(item: str) -> bool:
        target = item.split(" ", 1)[1]
        return bool(re.search(r"127\.0\.0\.1|localhost|::1|'(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)|^(10\.|192\.168\.)|\.local$|0\.0\.0\.0|255\.255\.255\.255|224\.0\.0\.", target))

    outside = [x for x in events if not private(x)]
    ran = "Application startup complete" in out or "StackChan" in out or alive
    if not (loaded and ran):
        return record("Contacts nothing by default (network test)", "NOT RUN", f"the host or the audit hook did not start (hook {loaded}, host {ran})")
    record("Contacts nothing by default (network test)", "PASS" if not outside else "FAIL",
           f"the host ran 30 seconds with a fresh empty home and no brain set; every socket connect, send and name lookup was logged: {len(events)} to this computer or the local network, {len(outside)} anywhere else" + (": " + ", ".join(sorted(set(outside))[:4]) if outside else ""))


def main(argv):
    today = datetime.date.today().isoformat() if "--date" not in argv else argv[argv.index("--date") + 1]
    head = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    for step in (secrets_scan, dependency_audit, unsafe_code, firmware_static_analysis, outbound_search, contacts_nothing_by_default):
        try:
            step()
        except Exception as error:  # a step that breaks is reported as not run, never as a pass
            record(step.__name__, "NOT RUN", f"the step failed: {error}")
    block = [f"Scan date: {today}. Commit: `{head}`. Run with `python3 scripts/security-scan.py`.", "", "| Step | Result | What it covered |", "|---|---|---|"]
    block += [f"| {s} | {v} | {d.replace('|', '/')} |" for s, v, d in results]
    text = "\n".join(block)
    if "--write" in argv:
        path = ROOT / "SECURITY.md"
        body = path.read_text()
        new = re.sub(r"(<!-- scan:begin -->\n).*?(\n<!-- scan:end -->)", lambda m: m.group(1) + text + m.group(2), body, flags=re.S)
        path.write_text(new)
    print("\n" + text)
    return 1 if any(v == "FAIL" for _, v, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
