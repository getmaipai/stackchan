#!/usr/bin/env python3
"""Build the static documentation site into docs-site/out/ (git-ignored).

Usage: python3 scripts/docs-site/build.py [--out DIR]

Standard library only. It reads docs/user/*.md, README.md, docs/design/decisions.md, docs/dev/feature-ledger.html,
docs/dev/screens-contact-sheets.md, the golden frames under host/tests/golden and the 3D model under scripts/virtual-unit/,
and writes plain HTML, CSS and JavaScript that all load from the site itself: no tracking, no outside fonts, scripts or CDN.
It reads those files and never edits them. Placement: host-side development tool; no firmware change. Upstream: none.
"""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs-site"
DEFAULT_OUT = SRC / "out"

DISCLAIMER = ("MaiPai for StackChan is an independent project. It is not affiliated with, endorsed by or sponsored by M5Stack. "
              "StackChan and M5Stack are trademarks of their owners.")
SITE = "MaiPai for StackChan"

NAV = [("index.html", "Home"), ("docs/index.html", "Users"), ("playground/index.html", "Playground"), ("dev/index.html", "Developers"),
       ("viewer.html", "3D viewer"), ("ledger.html", "Feature ledger"), ("screens.html", "Screens"), ("decisions.html", "Decisions"),
       ("search.html", "Search")]

# What the Developers section publishes besides the playground developer pages. Everything else under docs/dev, docs/design and docs/plan stays
# in the repository only: dated working notes, audits and egress or protection analysis (security sensitive), owner plans and funding. See docs-site/EXCLUDED.md.
DEV_PAGES = [("docs/dev", n) for n in (
    "overview", "contributing", "build-from-source", "host-and-brains", "virtual-unit", "virtual-unit-3d", "virtual-unit-assets", "virtual-unit-dance",
    "virtual-unit-fidelity", "e2e-virtual-unit", "fuzzing-and-hostile-peer", "screen-audit", "version-page-fit", "memory-budget", "gate-numbers",
    "battery-and-power", "test-speed")] + [("docs/design", n) for n in (
    "architecture", "repo-boundaries", "firmware-base", "unit-protocol", "screen-style", "languages", "first-run-flow", "config")]
SECTION_OF = {"docs/user": "users", "docs/playground": "playground"}


class BuildError(Exception):
    pass


# ---------------------------------------------------------------- markdown (the subset these docs use)

def slug(text):
    """The anchor a heading gets: lower case, words joined by hyphens, punctuation dropped (the form the docs link to)."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_]", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return re.sub(r" ", "-", text)


ALLOWED_TAG = re.compile(r'<(/?)(span|br|kbd|sub|sup)(\s+class="[\w\- ]*")?\s*/?>')


class Renderer:
    def __init__(self, links, images, ids, here):
        self.links = links          # repo path (str) -> output url relative to site root
        self.images = images        # repo path (str) -> output url relative to site root
        self.ids = ids              # output url -> set of heading ids, from the first pass
        self.here = here            # the repo path of the file being rendered
        self.out_url = links[here]
        self.headings = []          # (level, id, text)
        self.used = set()
        self.problems = []

    # -- paths
    def resolve(self, target):
        """Return (kind, value): ('site', url) when the target is a page of the site, ('image', url) for an image, ('ext', None) or ('gone', path)."""
        if re.match(r"^[a-z][a-z0-9+.\-]*:", target, re.I):
            return "ext", None
        base = Path(self.here).parent
        p = (base / target).as_posix()
        parts = []
        for seg in p.split("/"):
            if seg == "..":
                if parts:
                    parts.pop()
            elif seg and seg != ".":
                parts.append(seg)
        p = "/".join(parts)
        if p in self.images:
            return "image", self.images[p]
        if p in self.links:
            return "site", self.links[p]
        return "gone", p

    def rel(self, url):
        """Make a site-root url relative to the page being written."""
        here_dir = Path(self.out_url).parent
        up = len(here_dir.parts)
        return ("../" * up) + url

    # -- inline
    def inline(self, s):
        stash = []

        def keep(x):
            stash.append(x)
            return "\x00%d\x00" % (len(stash) - 1)

        s = re.sub(r"`([^`]+)`", lambda m: keep("<code>%s</code>" % html.escape(m.group(1), quote=False)), s)
        s = re.sub(r"<[^<>]*>", lambda m: keep(m.group(0) if ALLOWED_TAG.fullmatch(m.group(0)) else html.escape(m.group(0))), s)

        def img(m):
            alt, target = m.group(1), m.group(2).split()[0]
            kind, val = self.resolve(target)
            if kind != "image":
                self.problems.append("image not published: %s in %s" % (target, self.here))
                return keep('<span class="nolink">[picture: %s]</span>' % html.escape(alt))
            return keep('<img src="%s" alt="%s" loading="lazy">' % (self.rel(val), html.escape(alt, quote=True)))

        s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", img, s)

        def link(m):
            label, target = m.group(1), m.group(2).strip()
            frag = ""
            if "#" in target:
                target, frag = target.split("#", 1)
            if not target and frag:
                return keep('<a href="#%s">%s</a>' % (html.escape(frag, quote=True), "\x01" + label + "\x01"))
            kind, val = self.resolve(target)
            if kind == "site":
                if frag and frag not in self.ids.get(val, {frag}):
                    self.problems.append("anchor #%s missing in %s (linked from %s)" % (frag, val, self.here))
                    frag = ""
                href = self.rel(val) + ("#" + frag if frag else "")
                return keep('<a href="%s">%s</a>' % (html.escape(href, quote=True), "\x01" + label + "\x01"))
            if kind == "image":
                return keep('<a href="%s">%s</a>' % (self.rel(val), "\x01" + label + "\x01"))
            # an outside address or a file that is not part of the site: the words stay, the address does not
            return keep('<span class="nolink">%s</span>' % ("\x01" + label + "\x01"))

        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+(?:\s+\"[^\"]*\")?)\)", link, s)
        s = re.sub(r"<?(https?://[^\s<>)]+)>?", lambda m: keep('<span class="nolink">%s</span>' % html.escape(m.group(1))), s)
        s = html.escape(s, quote=False)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<em>\1</em>", s)
        s = re.sub(r"(?<![\w])_([^_\s][^_]*)_(?![\w])", r"<em>\1</em>", s)

        def unstash(t):
            for _ in range(3):
                t = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], t)
            return t

        s = unstash(s)
        # link labels were fenced with \x01 so emphasis could run inside them; their text is already escaped by the pass above
        return s.replace("\x01", "")

    # -- blocks
    def render(self, text):
        lines = text.replace("\r\n", "\n").split("\n")
        out = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            m = re.match(r"^```(\w*)", line)
            if m:
                buf = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    buf.append(lines[i])
                    i += 1
                i += 1
                out.append('<pre><code>%s</code></pre>' % html.escape("\n".join(buf)))
                continue
            m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
            if m:
                level, raw = len(m.group(1)), m.group(2)
                hid = base = slug(raw) or "section"
                n = 1
                while hid in self.used:
                    n += 1
                    hid = "%s-%d" % (base, n)
                self.used.add(hid)
                plain = re.sub(r"<[^>]+>|[`*]", "", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", raw))
                self.headings.append((level, hid, plain))
                out.append('<h%d id="%s">%s</h%d>' % (level, hid, self.inline(raw), level))
                i += 1
                continue
            if re.match(r"^(-{3,}|\*{3,})\s*$", line):
                out.append("<hr>")
                i += 1
                continue
            if line.startswith(">"):
                buf = []
                while i < len(lines) and lines[i].startswith(">"):
                    buf.append(re.sub(r"^>\s?", "", lines[i]))
                    i += 1
                out.append("<blockquote>%s</blockquote>" % self.render_inner("\n".join(buf)))
                continue
            if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|\-]+\|?\s*$", lines[i + 1]):
                head = self.cells(line)
                i += 2
                rows = []
                while i < len(lines) and lines[i].startswith("|"):
                    rows.append(self.cells(lines[i]))
                    i += 1
                t = "<div class=\"tablewrap\"><table><thead><tr>%s</tr></thead><tbody>" % "".join("<th>%s</th>" % self.inline(c) for c in head)
                for r in rows:
                    t += "<tr>%s</tr>" % "".join("<td>%s</td>" % self.inline(c) for c in r)
                out.append(t + "</tbody></table></div>")
                continue
            if re.match(r"^\s*([-*+]|\d+[.)])\s+", line):
                block, i = self.list_block(lines, i)
                out.append(block)
                continue
            buf = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6}\s|```|>|\||\s*([-*+]|\d+[.)])\s+|-{3,}\s*$)", lines[i]):
                buf.append(lines[i])
                i += 1
            out.append("<p>%s</p>" % self.inline(" ".join(x.strip() for x in buf)))
        return "\n".join(out)

    def render_inner(self, text):
        sub = Renderer(self.links, self.images, self.ids, self.here)
        sub.used = self.used
        sub.headings = self.headings
        sub.problems = self.problems
        return sub.render(text)

    @staticmethod
    def cells(line):
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]

    def list_block(self, lines, i):
        """A (possibly nested) list. Items continue on following indented lines."""
        items = []   # (indent, ordered, text lines)
        while i < len(lines):
            line = lines[i]
            m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
            if m:
                items.append([len(m.group(1).expandtabs(4)), bool(re.match(r"\d", m.group(2))), [m.group(3)]])
                i += 1
            elif line.strip() and re.match(r"^\s+\S", line) and items:
                items[-1][2].append(line.strip())
                i += 1
            elif not line.strip() and items and i + 1 < len(lines) and re.match(r"^\s+\S", lines[i + 1]) and not re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[i + 1]):
                items[-1][2].append("\x02")   # a paragraph break inside an item
                i += 1
            elif not line.strip() and i + 1 < len(lines) and re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[i + 1]) and items:
                i += 1
            else:
                break
        return self.build_list(items, 0)[0], i

    def build_list(self, items, pos):
        indent = items[pos][0]
        ordered = items[pos][1]
        tag = "ol" if ordered else "ul"
        html_out = "<%s>" % tag
        while pos < len(items) and items[pos][0] >= indent:
            if items[pos][0] > indent:
                sub, pos = self.build_list(items, pos)
                html_out = html_out[:-5] + sub + "</li>" if html_out.endswith("</li>") else html_out + sub
                continue
            parts = " ".join(items[pos][2]).split("\x02")
            body = "".join("<p>%s</p>" % self.inline(p.strip()) for p in parts[1:] if p.strip())
            html_out += "<li>%s%s</li>" % (self.inline(parts[0].strip()), body)
            pos += 1
        return html_out + "</%s>" % tag, pos


# ---------------------------------------------------------------- page chrome

def side_nav(label, items, out_url):
    """The left tab column of a section: items are (url, title); the current page is marked."""
    up = "../" * len(Path(out_url).parent.parts)
    li = "".join('<li><a href="%s%s"%s>%s</a></li>' % (up, u, ' aria-current="page"' if u == out_url else "", html.escape(t)) for u, t in items)
    return '<nav class="tabs" aria-label="%s pages"><strong>%s</strong><ul>%s</ul></nav>' % (html.escape(label), html.escape(label), li)


def page(out_url, title, body, description="", extra_head="", body_class="", side=""):
    up = "../" * len(Path(out_url).parent.parts)
    section = out_url.split("/")[0] if "/" in out_url else out_url
    section_url = {"docs": "docs/index.html", "playground": "playground/index.html", "dev": "dev/index.html"}.get(section, out_url)
    if side:
        body = '<div class="split">%s<div class="pane">%s</div></div>' % (side, body)
        body_class = (body_class + " has-split").strip()
    def cur(u):
        return u == out_url or (u == section_url)
    nav = "".join('<a href="%s%s"%s>%s</a>' % (up, u, ' aria-current="page"' if cur(u) else "", html.escape(t)) for u, t in NAV)
    desc = '<meta name="description" content="%s">' % html.escape(description, quote=True) if description else ""
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
%(desc)s
<link rel="stylesheet" href="%(up)sassets/site.css">
<script src="%(up)sassets/theme.js"></script>
%(extra)s</head>
<body class="%(cls)s">
<a class="skip" href="#main">Skip to the page</a>
<header class="top"><div class="bar">
<a class="brand" href="%(up)sindex.html">%(site)s</a>
<nav aria-label="Site">%(nav)s</nav>
<button type="button" id="theme" class="themebtn" aria-label="Switch between light and dark">Light/dark</button>
</div></header>
<main id="main">
%(body)s
</main>
<footer class="foot"><div class="wrap"><p>%(disc)s</p>
<p class="small">This site sets no cookies and loads nothing from other sites. Draft until the first release.</p></div></footer>
<script src="%(up)sassets/theme-button.js"></script>
</body>
</html>
""" % dict(title=html.escape(title) + " | " + SITE, desc=desc, up=up, extra=extra_head, cls=body_class, site=SITE, nav=nav, body=body, disc=DISCLAIMER)


def toc(headings):
    hs = [h for h in headings if h[0] == 2]
    if len(hs) < 4:
        return ""
    return '<nav class="toc" aria-label="On this page"><strong>On this page</strong><ul>%s</ul></nav>' % "".join(
        '<li><a href="#%s">%s</a></li>' % (i, html.escape(t)) for _, i, t in hs)


# ---------------------------------------------------------------- the build

def read(p):
    return Path(p).read_text(encoding="utf-8")


def write(out, rel, text):
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def copy(out, rel, src):
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, p)


def first_title(md, fallback):
    m = re.search(r"^#\s+(.+?)\s*$", md, re.M)
    return re.sub(r"[`*]", "", m.group(1)) if m else fallback


def summary(md):
    """The first plain paragraph after the title, for the page list."""
    for block in re.split(r"\n\s*\n", md):
        b = block.strip()
        if not b or b.startswith(("#", "|", "```", ">", "!", "<", "-", "*")) or re.match(r"^\d+\.", b):
            continue
        b = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", b)
        b = re.sub(r"[`*_]|<[^>]+>", "", b)
        b = " ".join(b.split())
        return b[:220] + ("..." if len(b) > 220 else "")
    return ""


def plain_text(md):
    t = re.sub(r"```.*?```", " ", md, flags=re.S)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"<[^>]+>|[`*_#>|]", " ", t)
    return " ".join(t.split())


def gather_gallery():
    """Golden frames, faces and contact sheets with their captions."""
    gold = ROOT / "host" / "tests" / "golden"
    sheets = []
    cs = ROOT / "docs" / "dev" / "screens-contact-sheets.md"
    names = {}
    if cs.exists():
        for m in re.finditer(r"^## (\w+)\s+\(\[sheet-\w+\.png\]\([^)]*\)\)\s*\n\s*\n(.+)$", read(cs), re.M):
            names[m.group(1)] = m.group(2).strip()
    for f in sorted((ROOT / "docs" / "dev" / "screens").glob("sheet-*.png")):
        lang = f.stem.split("-", 1)[1]
        sheets.append((lang, f, names.get(lang, "")))
    screens = sorted((gold / "screens").glob("*.png"))
    faces = sorted((gold / "face").glob("*.png"))
    before = sorted((gold / "before-ux").glob("*.png"))
    return sheets, screens, faces, before


def build(out):
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    user_docs = sorted((ROOT / "docs" / "user").glob("*.md"))
    readme = ROOT / "README.md"
    decisions = ROOT / "docs" / "design" / "decisions.md"
    cs_md = ROOT / "docs" / "dev" / "screens-contact-sheets.md"
    ledger = ROOT / "docs" / "dev" / "feature-ledger.html"

    rel = lambda p: p.relative_to(ROOT).as_posix()
    links = {rel(readme): "index.html", rel(decisions): "decisions.html", rel(ledger): "ledger.html", rel(cs_md): "screens.html"}
    for d in user_docs:
        links[rel(d)] = "docs/%s.html" % d.stem
    pg_docs = sorted((ROOT / "docs" / "playground").glob("*.md"))
    pg_user = [d for d in pg_docs if not d.stem.startswith("dev-")]
    pg_dev = [d for d in pg_docs if d.stem.startswith("dev-")]
    dev_docs = [ROOT / a / (n + ".md") for a, n in DEV_PAGES if (ROOT / a / (n + ".md")).exists()]
    for d in pg_user:
        links[rel(d)] = "playground/index.html" if d.stem == "index" else "playground/%s.html" % d.stem
    for d in pg_dev:
        links[rel(d)] = "dev/%s.html" % d.stem[4:]
    for d in dev_docs:
        links[rel(d)] = "dev/%s%s.html" % ("design-" if d.parent.name == "design" else "", d.stem)
    if len(set(links.values())) != len(links.values()):
        raise BuildError("two source files map to one page address")
    # a file that was moved or removed after the docs were written still resolves to the nearest page, never to a dead link
    images = {}
    img_dir = ROOT / "docs" / "images"
    if img_dir.exists():
        for f in sorted(img_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in (".png", ".svg", ".gif", ".jpg", ".jpeg", ".webp"):
                images[rel(f)] = "images/" + f.name

    sources = [(readme, rel(readme))] + [(d, rel(d)) for d in user_docs + pg_user + pg_dev + dev_docs] + [(decisions, rel(decisions))]
    ids = {}
    problems = []
    rendered = {}
    for pass_no in (1, 2):
        for path, key in sources:
            r = Renderer(links, images, ids, key)
            body = r.render(read(path))
            ids[links[key]] = {h[1] for h in r.headings}
            if pass_no == 2:
                rendered[key] = (body, r)
                problems += r.problems

    used_images = set()
    for body, _ in rendered.values():
        used_images.update(re.findall(r'src="(?:\.\./)*(images/[^"]+)"', body))

    # ---- assets
    for name in ("site.css", "theme.js", "theme-button.js", "search.js"):
        copy(out, "assets/" + name, SRC / "assets" / name)
    for u in sorted(used_images):
        copy(out, u, img_dir / Path(u).name)

    # ---- home
    readme_body, rr = rendered[rel(readme)]
    readme_body = re.sub(r"<h1[^>]*>.*?</h1>", "", readme_body, count=1, flags=re.S)
    home_intro = (SRC / "home-intro.html").read_text(encoding="utf-8")
    write(out, "index.html", page("index.html", SITE, home_intro + '<div class="wrap prose">' + readme_body + "</div>",
                                  "Firmware and a host program for the StackChan desk robot: private, local and yours."))

    # ---- one page per doc, in three sections, each with its own left tab column
    index_rows = []
    sections = {}   # name -> [(url, title, summary, path)]
    for name, docs in (("Users", user_docs), ("Playground", pg_user), ("Developers", pg_dev + dev_docs)):
        rows = []
        for d in docs:
            md = read(d)
            rows.append((links[rel(d)], first_title(md, d.stem.replace("-", " ").capitalize()), summary(md), d))
        sections[name] = rows
    # the playground index leads its tab column; the developer index and the user list are generated
    sections["Users"].sort(key=lambda r: (r[0] != "docs/index.html", r[1].lower()))
    sections["Playground"].sort(key=lambda r: (r[0] != "playground/index.html", r[0] != "playground/start-here.html", r[1].lower()))
    dev_rows = sections["Developers"]
    side_for = {}
    for name, label, first in (("Users", "Users", None), ("Playground", "Playground", None),
                               ("Developers", "Developers", ("dev/index.html", "All developer pages"))):
        side_for[name] = ([first] if first else []) + [(u, t) for u, t, _, _ in sections[name]]
    for name, rows in sections.items():
        for url, title, summ, d in rows:
            body, r = rendered[rel(d)]
            side = side_nav(name, side_for[name], url)
            write(out, url, page(url, title, '<div class="wrap prose">%s%s</div>' % (toc(r.headings), body), summ, side=side))
            index_rows.append({"title": title, "url": url, "summary": summ, "text": plain_text(read(d))})

    def card_list(rows, intro, up=""):
        li = "".join('<li><a href="%s">%s</a><span class="s">%s</span></li>' % (html.escape(up + u), html.escape(t), html.escape(sm)) for u, t, sm, _ in rows)
        return '<div class="wrap prose">%s<ul class="pagelist">%s</ul></div>' % (intro, li)

    ddoc = ("<h1>Developers</h1><p>How the playground and the virtual unit are built, and the design pages a contributor needs. "
            "Working notes, audits, security analysis and owner plans stay in the repository and are not published here.</p>")
    write(out, "dev/index.html", page("dev/index.html", "Developers", card_list(dev_rows, ddoc, "../"), "Architecture, tools, tests and design pages.",
                                      side=side_nav("Developers", side_for["Developers"], "dev/index.html")))
    index_rows += [{"title": "Developers", "url": "dev/index.html", "summary": "Architecture, tools, tests and design pages.", "text": ""}]

    # ---- searchable page list
    extra = {"Feature ledger": ("ledger.html", "Every feature with its status and how far it is proven."),
             "3D viewer": ("viewer.html", "Turn the robot, move the head, show the inside, plug the ports, light the bar."),
             "Screens": ("screens.html", "The robot's screens, drawn by the unit's own code, in six languages."),
             "Decisions": ("decisions.html", "The owner's decisions, in order.")}
    for t, (u, s) in extra.items():
        index_rows.append({"title": t, "url": u, "summary": s, "text": s})
    search_js = "window.SEARCH_INDEX=" + json.dumps(
        [{"t": r["title"], "u": r["url"], "s": r["summary"], "x": r["text"][:6000]} for r in index_rows], ensure_ascii=False) + ";\n"
    write(out, "assets/search-index.js", search_js)
    lst = "".join('<li data-t="%s"><a href="%s">%s</a><span class="s">%s</span></li>' % (
        html.escape((r["title"] + " " + r["summary"]).lower(), quote=True), html.escape(r["url"]), html.escape(r["title"]), html.escape(r["summary"]))
        for r in sorted(index_rows, key=lambda r: r["title"].lower()))
    body = ('<div class="wrap"><h1>Search</h1><p>Type to filter by title, or search the full text of every user page.</p>'
            '<p><label for="q" class="vh">Search the pages</label><input id="q" type="search" placeholder="Search the pages" autocomplete="off"></p>'
            '<p id="count" class="small" aria-live="polite"></p><ul id="pages" class="pagelist">%s</ul>'
            '<noscript><p>Search needs JavaScript. The list above shows every page.</p></noscript></div>'
            '<script src="assets/search-index.js"></script><script src="assets/search.js"></script>') % lst
    write(out, "search.html", page("search.html", "Search", body, "Every page of the documentation, with search."))

    # ---- decisions
    dbody, dr = rendered[rel(decisions)]
    write(out, "decisions.html", page("decisions.html", "Decisions log", '<div class="wrap prose">%s%s</div>' % (toc(dr.headings), dbody),
                                      "The decisions log, rendered from docs/design/decisions.md."))

    # ---- feature ledger: the generated file is copied as it is; a thin page around it carries the disclaimer
    if ledger.exists():
        copy(out, "ledger-app.html", ledger)
        body = ('<div class="wrap"><h1>Feature ledger</h1><p>Every feature, how far it is proven (idea, designed, built, proven on a virtual unit, '
                'proven on the robot) and where its code, test and page are. <a href="ledger-app.html">Open it full screen.</a></p></div>'
                '<iframe class="ledger" title="Feature ledger" src="ledger-app.html"></iframe>')
        write(out, "ledger.html", page("ledger.html", "Feature ledger", body, "Every feature with its status.", body_class="wide"))

    # ---- golden frames
    sheets, screens, faces, before = gather_gallery()
    g = ['<div class="wrap"><h1>Screens</h1><p>Every picture here is drawn by the unit\'s own screen code on a computer (the golden frames the tests compare against). '
         'They are not photos of a robot. Click a picture to see it at full size.</p>']
    g.append('<h2 id="sheets">Contact sheets by language</h2><p>Frames run left to right, top to bottom, at half size. The numbers in the caption name the frames in order.</p><div class="gallery big">')
    for lang, f, cap in sheets:
        copy(out, "gallery/sheet-%s.png" % lang, f)
        g.append('<figure><a href="gallery/sheet-%s.png"><img src="gallery/sheet-%s.png" alt="Contact sheet of the %s screens" loading="lazy"></a>'
                 '<figcaption><strong>%s</strong>%s</figcaption></figure>' % (lang, lang, lang, lang, " " + html.escape(cap) if cap else ""))
    g.append("</div>")

    def frames(title, hid, files, sub):
        g.append('<h2 id="%s">%s</h2><p>%s</p><div class="gallery">' % (hid, title, sub))
        for f in files:
            copy(out, "gallery/%s/%s" % (hid, f.name), f)
            cap = f.stem.replace("-", " ").replace("_", " ")
            g.append('<figure><a href="gallery/%s/%s"><img src="gallery/%s/%s" alt="%s" loading="lazy" width="320" height="240"></a><figcaption>%s</figcaption></figure>'
                     % (hid, f.name, hid, f.name, html.escape(cap), html.escape(cap)))
        g.append("</div>")

    frames("Golden screens", "screens", screens, "%d frames, English first, then the other languages." % len(screens))
    frames("Faces", "faces", faces, "The face styles and moods the robot draws.")
    frames("Earlier covers and first-run frames", "before-ux", before, "Kept as the baseline the later screens are compared with.")
    g.append("</div>")
    write(out, "screens.html", page("screens.html", "Screens", "".join(g), "The robot's screens in six languages, with captions."))

    # ---- 3D viewer (view-only, no unit): the same view3d.js, unedited, with a stub for the unit's state
    for name, src in (("three.min.js", SRC / "vendor" / "three-r128" / "three.min.js"), ("LICENSE-three.txt", SRC / "vendor" / "three-r128" / "LICENSE"),
                      ("view3d.js", ROOT / "scripts" / "virtual-unit" / "view3d.js"), ("viewer-stub.js", SRC / "viewer-stub.js")):
        copy(out, "assets/" + name, src)
    copy(out, "assets/stackchan.glb", ROOT / "scripts" / "virtual-unit" / "model" / "stackchan.glb")
    copy(out, "assets/face.png", ROOT / "docs" / "images" / "unit-face-big-eyes.png")
    tpl = (SRC / "viewer.html").read_text(encoding="utf-8")
    shell = page("viewer.html", "3D viewer", "@@BODY@@", "Turn the StackChan model, move its head, show the inside, plug its ports and light its bar.", body_class="wide")
    body_start = tpl.split("@@SPLIT@@")
    inner = body_start[0]
    scripts = body_start[1] if len(body_start) > 1 else ""
    write(out, "viewer.html", shell.replace("@@BODY@@", inner).replace("</body>", scripts + "\n</body>"))

    write(out, ".nojekyll", "")
    return problems


def report(out, problems):
    total = 0
    biggest = []
    for f in Path(out).rglob("*"):
        if f.is_file():
            n = f.stat().st_size
            total += n
            biggest.append((n, f.relative_to(out).as_posix()))
    biggest.sort(reverse=True)
    print("docs-site built: %s" % out)
    print("files: %d, total %.2f MB" % (len(biggest), total / 1e6))
    for n, name in biggest[:5]:
        print("  %8.1f KB  %s" % (n / 1000, name))
    for p in sorted(set(problems)):
        print("note: " + p)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    try:
        problems = build(a.out)
    except (BuildError, OSError) as e:
        print("docs-site build failed: %s. Run it from a full checkout of the repository." % e, file=sys.stderr)
        return 1
    report(a.out, problems)
    return 0


if __name__ == "__main__":
    sys.exit(main())
