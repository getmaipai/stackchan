#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BASE=${1:?Usage: patch-replay.sh CLEAN_NEW_BASE_WORKTREE}
python3 - "$ROOT" "$BASE" <<'PY'
import re, subprocess, sys
from pathlib import Path
root, base = Path(sys.argv[1]), Path(sys.argv[2])
recipe = (root/'host/maipai_body/bodies/stackchan/firmware/recipe.sh').read_text()
patchdir = root/'host/maipai_body/bodies/stackchan/firmware/patches'
rows=[]
for name, target in re.findall(r'apply_repo_patch\s+(\S+)\s+"\$(SRC|FW/xiaozhi-esp32)"', recipe):
    p=patchdir/name
    text=p.read_text(errors='replace')
    files=[]
    for x in re.findall(r'^diff --git a/(.*?) b/', text, re.M):
        files.append(x)
    sub=base if target=='SRC' else base/'firmware/xiaozhi-esp32'
    missing=[f for f in files if not (sub/f).exists() and not re.search(r'^--- /dev/null$', text, re.M)]
    # Identify genuinely added files separately from missing existing paths.
    added=set()
    for block in re.split(r'(?=^diff --git )', text, flags=re.M):
        m=re.search(r'^diff --git a/(.*?) b/', block, re.M)
        if m and re.search(r'^--- /dev/null$', block, re.M): added.add(m.group(1))
    missing=[f for f in files if not (sub/f).exists() and f not in added]
    payload=text[text.find('diff --git'):] if 'diff --git' in text else ''
    chk=subprocess.run(['git','-C',str(sub),'apply','--check','--unidiff-zero','-'],input=payload,text=True,capture_output=True)
    status='CLEAN'; hunks=0; conflicts=[]
    patch_no=name.split('-',1)[0]
    if patch_no in ('009','044'):
        status='OBSOLETE'
    elif missing:
        status='MISSING_FILE'; conflicts=missing
    elif chk.returncode:
        # Count rejected file hunks from git's diagnostics; count patch hunk headers as fallback.
        dry=subprocess.run(['git','-C',str(sub),'apply','--check','--verbose','--unidiff-zero','-'],input=payload,text=True,capture_output=True)
        conflicts=files
        hunks=len(re.findall(r'@@ ',payload))
        status='CONFLICT'
    else:
        ap=subprocess.run(['git','-C',str(sub),'apply','--verbose','--unidiff-zero','-'],input=payload,text=True,capture_output=True)
        if ap.returncode:
            status='CONFLICT'; conflicts=files; hunks=len(re.findall(r'@@ ',payload))
        else:
            status='FUZZY' if re.search(r'offset|fuzz', ap.stdout+ap.stderr, re.I) else 'CLEAN'
    rows.append((name,p,files,status,hunks,conflicts))
out=['patch\tname\tfiles_touched\tstatus\thunks\tconflicting_files']
for name,p,files,status,hunks,conflicts in rows:
    out.append(f"{name.split('-')[0]}\t{name}\t{','.join(files)}\t{status}\t{hunks}\t{','.join(conflicts)}")
(root/'.runs').mkdir(exist_ok=True)
(root/'.runs/patch-replay.tsv').write_text('\n'.join(out)+'\n')
print('\n'.join(out))
PY
