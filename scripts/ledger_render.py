"""Rendering for the feature ledger: the markdown page and the one self-contained HTML page (data embedded as JSON, images as data URIs, no outside scripts or styles; dark and light by the
reader's setting; filters and search; phone friendly). Placement: docs tooling. Upstream: none."""
from __future__ import annotations

import base64
import html
import json
import mimetypes
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ["idea", "designed", "built", "proven virtual", "proven on unit", "needs person"]
AUDIENCES = {"user": "Everyday user", "maker": "Maker and tech"}


def counts(rows: list[dict]) -> dict[str, Counter]:
    out = {a: Counter() for a in AUDIENCES}
    for r in rows:
        out[r["audience"]][r["status"]] += 1
    return out


def average(rows: list[dict], audience: str) -> int:
    pts = [r["percent"] for r in rows if r["audience"] == audience]
    return round(sum(pts) / len(pts)) if pts else 0


def markdown(rows: list[dict], meta: dict) -> str:
    c = counts(rows)
    lines = ["# Feature ledger", "", "Made by `python3 scripts/feature-ledger.py` from the repository; do not edit by hand. The page to read first is `feature-ledger.html` (searchable, filters). "
             f"Rows: {len(rows)}. How a status and a percent are worked out: {meta['rule']}", "", "## Progress", "", "| Audience | " + " | ".join(STATUSES) + " | Rows | Average percent |", "|---|" + "---|" * (len(STATUSES) + 2)]
    for a, label in AUDIENCES.items():
        lines.append(f"| {label} | " + " | ".join(str(c[a][s]) for s in STATUSES) + f" | {sum(c[a].values())} | {average(rows, a)} |")
    for a, label in AUDIENCES.items():
        lines += ["", f"## {label}", ""]
        by_area: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            if r["audience"] == a:
                by_area[r["area"]].append(r)
        for area in sorted(by_area):
            lines += [f"### {area} ({len(by_area[area])})", "", "| Feature | What it does | Status | % | Where | Evidence | Doc |", "|---|---|---|---|---|---|---|"]
            for r in by_area[area]:
                img = f" ![]({r['image']})" if r["image"] else ""
                where = "<br>".join(f"`{w}`" for w in r["where"][:3]) or ""
                ev = ", ".join(f"`{b}`" for b in r["bench"][:2]) or r["rule"]
                doc = f"[{r['doc']}]({r['doc'].split('#')[0].replace('docs/', '../')}{('#' + r['doc'].split('#')[1]) if '#' in r['doc'] else ''})" if r["doc"] else "doc missing"
                lines.append(f"| **{r['name']}**{img} | {r['desc'].replace('|', '/')} | {r['status']} | {r['percent']} | {where} | {ev.replace('|', '/')} | {doc} |")
            lines.append("")
    lines += ["## Patches that no feature row names", ""] + (["| Patch | What it does |", "|---|---|"] + [f"| `{p['name']}` | {p['intent']} |" for p in meta["unmapped"]] if meta["unmapped"] else ["Every patch in `firmware/patches/ORDER` is named by at least one row."])
    return "\n".join(lines) + "\n"


def _data_uri(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        return ""
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def page(rows: list[dict], meta: dict) -> str:
    images = {}
    for r in rows:
        if r["image"] and r["image"] not in images:
            images[r["image"]] = _data_uri(r["image"])
    slim = [{k: r[k] for k in ("id", "audience", "area", "name", "desc", "status", "percent", "where", "image", "bench", "doc", "rule", "tags")} for r in rows]
    data = json.dumps({"rows": slim, "images": images, "meta": {"rule": meta["rule"], "unmapped": meta["unmapped"]}}, ensure_ascii=False).replace("</", "<\\/")
    return HTML.replace("__DATA__", data).replace("__TITLE__", html.escape("Feature ledger"))


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--fg:#1d232b;--mut:#5b6672;--card:#fff;--line:#dde1e6;--acc:#1d6fd6;--idea:#9aa5b1;--designed:#8d6fd6;--built:#d99a00;--pv:#2f8f5b;--pu:#0b6b3a;--np:#c2543a}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#12161b;--fg:#e6eaee;--mut:#a3adb8;--card:#1b2128;--line:#2c343d;--acc:#6aa8ff;--idea:#6b7683;--designed:#a99bff;--built:#f0b429;--pv:#4cc38a;--pu:#2fa56a;--np:#ef8a70}}
:root[data-theme=dark]{--bg:#12161b;--fg:#e6eaee;--mut:#a3adb8;--card:#1b2128;--line:#2c343d;--acc:#6aa8ff;--idea:#6b7683;--designed:#a99bff;--built:#f0b429;--pv:#4cc38a;--pu:#2fa56a;--np:#ef8a70}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:16px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--mut);font-size:13px}
main{max-width:1100px;margin:0 auto;padding:0 16px 48px}
.tabs,.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
button,select,input{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
input[type=search]{flex:1;min-width:160px}
.bar{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--line);margin:6px 0}
.bar i{display:block;height:100%}
.prog{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin:14px 0}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.pcard h2{margin:0 0 4px;font-size:16px}.big{font-size:28px;font-weight:700}
.leg{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--mut)}.leg b{color:var(--fg)}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px}
section.area h3{margin:22px 0 6px;font-size:17px;border-bottom:1px solid var(--line);padding-bottom:4px}
.row{display:grid;grid-template-columns:84px 1fr;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;margin:8px 0}
.row img{width:84px;height:auto;border-radius:6px;border:1px solid var(--line);background:#000;image-rendering:auto}.noimg{width:84px}
.name{font-weight:650}.desc{margin:2px 0;color:var(--fg)}.meta{font-size:12px;color:var(--mut);word-break:break-word}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;color:#fff;margin-right:6px;white-space:nowrap}
.pct{height:6px;background:var(--line);border-radius:3px;margin:6px 0;max-width:260px}.pct i{display:block;height:100%;border-radius:3px;background:var(--acc)}
.miss{color:var(--np)}a{color:var(--acc)}
@media (max-width:560px){.row{grid-template-columns:1fr}.row img,.noimg{width:100%;max-width:240px}}
details{margin:18px 0}summary{cursor:pointer}
</style></head><body>
<header><h1>Feature ledger</h1><div class="sub" id="sub"></div>
<div class="tabs" id="tabs"></div>
<div class="chips" id="chips"></div>
<div class="chips"><input type="search" id="q" placeholder="Search features, patches, files" aria-label="Search"><select id="area" aria-label="Area"></select><button id="theme" type="button">Light/dark</button></div>
</header>
<main><div class="prog" id="prog"></div><details><summary>How a status and a percent are worked out</summary><p class="meta" id="rule"></p></details><div id="list"></div><details id="unm"><summary>Patches that no feature row names</summary><div id="unmlist" class="meta"></div></details></main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const ST=["idea","designed","built","proven virtual","proven on unit","needs person"];
const COL={"idea":"var(--idea)","designed":"var(--designed)","built":"var(--built)","proven virtual":"var(--pv)","proven on unit":"var(--pu)","needs person":"var(--np)"};
const AUD={user:"Everyday user",maker:"Maker and tech"};
let aud="user",sts=new Set(),area="",q="";
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function prog(){let h="";for(const a of Object.keys(AUD)){const rs=D.rows.filter(r=>r.audience===a);const c={};ST.forEach(s=>c[s]=rs.filter(r=>r.status===s).length);const avg=rs.length?Math.round(rs.reduce((x,r)=>x+r.percent,0)/rs.length):0;
h+=`<div class="pcard"><h2>${AUD[a]}</h2><div><span class="big">${avg}%</span> average, ${rs.length} rows</div><div class="bar">${ST.map(s=>`<i style="width:${rs.length?100*c[s]/rs.length:0}%;background:${COL[s]}" title="${s}: ${c[s]}"></i>`).join("")}</div><div class="leg">${ST.map(s=>`<span><span class="dot" style="background:${COL[s]}"></span>${s} <b>${c[s]}</b></span>`).join("")}</div></div>`}
$("prog").innerHTML=h}
function chips(){$("tabs").innerHTML=Object.keys(AUD).map(a=>`<button type="button" class="${aud===a?"on":""}" data-a="${a}">${AUD[a]} (${D.rows.filter(r=>r.audience===a).length})</button>`).join("");
$("chips").innerHTML=ST.map(s=>`<button type="button" class="${sts.has(s)?"on":""}" data-s="${s}"><span class="dot" style="background:${COL[s]}"></span>${s}</button>`).join("");
const areas=[...new Set(D.rows.filter(r=>r.audience===aud).map(r=>r.area))].sort();$("area").innerHTML='<option value="">All areas</option>'+areas.map(a=>`<option ${a===area?"selected":""}>${esc(a)}</option>`).join("")}
function draw(){const rs=D.rows.filter(r=>r.audience===aud&&(!sts.size||sts.has(r.status))&&(!area||r.area===area)&&(!q||(r.name+" "+r.desc+" "+r.where.join(" ")+" "+r.area).toLowerCase().includes(q)));
$("sub").textContent=`${rs.length} of ${D.rows.filter(r=>r.audience===aud).length} rows shown`;
const g={};rs.forEach(r=>(g[r.area]=g[r.area]||[]).push(r));let h="";
for(const a of Object.keys(g).sort()){h+=`<section class="area"><h3>${esc(a)} (${g[a].length})</h3>`;for(const r of g[a]){const im=r.image&&D.images[r.image];
const doc=r.doc?`<a href="../${esc(r.doc.replace(/^docs\//,""))}">${esc(r.doc)}</a>`:'<span class="miss">doc missing</span>';
h+=`<div class="row">${im?`<img loading="lazy" src="${im}" alt="${esc(r.name)}">`:'<div class="noimg"></div>'}<div><div class="name">${esc(r.name)}</div><div class="desc">${esc(r.desc)}</div>
<div><span class="badge" style="background:${COL[r.status]}">${r.status}</span><b>${r.percent}%</b></div><div class="pct"><i style="width:${r.percent}%"></i></div>
<div class="meta">Where: ${r.where.length?r.where.map(w=>"<code>"+esc(w)+"</code>").join(" "):"none"}<br>Evidence: ${r.bench.length?r.bench.map(b=>"<code>"+esc(b)+"</code>").join(" "):esc(r.rule)}<br>Doc: ${doc}</div></div></div>`}h+="</section>"}
$("list").innerHTML=h||'<p class="meta">Nothing matches.</p>';
$("unmlist").innerHTML=D.meta.unmapped.length?D.meta.unmapped.map(p=>`<div><code>${esc(p.name)}</code> ${esc(p.intent)}</div>`).join(""):"Every patch is named by a row."}
$("tabs").onclick=e=>{const a=e.target.closest("button")?.dataset.a;if(a){aud=a;area="";chips();draw()}};
$("chips").onclick=e=>{const s=e.target.closest("button")?.dataset.s;if(s){sts.has(s)?sts.delete(s):sts.add(s);chips();draw()}};
$("area").onchange=e=>{area=e.target.value;draw()};$("q").oninput=e=>{q=e.target.value.toLowerCase();draw()};
$("theme").onclick=()=>{const r=document.documentElement;const cur=r.dataset.theme||(matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");r.dataset.theme=cur==="dark"?"light":"dark"};
$("rule").textContent=D.meta.rule;prog();chips();draw();
</script></body></html>
"""
