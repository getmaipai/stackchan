#!/usr/bin/env python3
"""Check the built documentation site: links, pictures, captions and the phone, dark and print styles.

Usage: python3 scripts/docs-site/build.py && python3 scripts/docs-site/check-site.py [--out DIR]

It reads docs-site/out (or DIR) and fails when:
  - an internal link, script, stylesheet or picture points at a file that is not in the site (case counts, as on a web host), or at a #fragment
    the target page does not have;
  - a link or picture leaves the site (the site loads nothing from other addresses);
  - a picture file is empty, has no alt text, or has no visible caption (a figure with a non-empty figcaption, or a table row with words next to it);
  - a page has no viewport tag, or the style sheet breaks a phone, dark mode or print rule listed in check_css().
ledger-app.html is a generated, self-contained file shown inside ledger.html; it is left out of the page checks.
Standard library only; about a second on the full site. Placement: host-side development tool; no firmware change. Upstream: none.
"""

import argparse
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "docs-site" / "out"
EMBEDDED = {"ledger-app.html"}
# The one outside link the site carries: the sponsor line in every footer (the account in .github/FUNDING.yml). Nothing loads from it.
ALLOWED_OUTSIDE = {"https://github.com/sponsors/JesseWebDotCom"}
SKIP_SCHEMES = ("mailto:", "javascript:", "data:", "blob:")
MAX_SHOWN = 40


class Page(HTMLParser):
    """Collects ids, references and the picture and caption facts of one page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.refs = set(), []     # refs: (tag, attr, value)
        self.pictures = []                  # (src, alt or None)
        self.problems = []                  # caption problems found while reading
        self.viewport = False
        self._stack = []                    # open figure and tr records
        self._caption_depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ("id", "name"):
            if a.get(k):
                self.ids.add(a[k])
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        for k in ("href", "src", "poster"):
            if a.get(k) is not None and tag in ("a", "img", "link", "script", "iframe", "source", "video", "audio", "area"):
                self.refs.append((tag, k, a[k]))
        if tag == "figure":
            self._stack.append({"kind": "figure", "imgs": [], "text": ""})
        elif tag == "figcaption":
            self._caption_depth += 1
        elif tag == "tr":
            self._stack.append({"kind": "row", "imgs": [], "text": ""})
        elif tag == "img":
            src = a.get("src") or ""
            self.pictures.append((src, a.get("alt")))
            host = next((r for r in reversed(self._stack) if r["kind"] in ("figure", "row")), None)
            if host is None:
                self.problems.append("picture outside a figure or table row, so it has no caption: %s" % src)
            else:
                host["imgs"].append(src)

    def handle_endtag(self, tag):
        if tag == "figcaption":
            self._caption_depth = max(0, self._caption_depth - 1)
        elif tag in ("figure", "tr"):
            kind = "figure" if tag == "figure" else "row"
            for i in range(len(self._stack) - 1, -1, -1):
                if self._stack[i]["kind"] == kind:
                    rec = self._stack.pop(i)
                    if rec["imgs"] and not rec["text"].strip():
                        what = "figure without a figcaption" if kind == "figure" else "table row with a picture and no words beside it"
                        self.problems.append("%s: %s" % (what, rec["imgs"][0]))
                    break

    def handle_data(self, data):
        if not data.strip():
            return
        for rec in self._stack:
            if rec["kind"] == "row":
                rec["text"] += data
            elif self._caption_depth:
                rec["text"] += data


def parse(path):
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    p.close()
    return p


def luminance(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    chans = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        chans.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chans[0] + 0.7152 * chans[1] + 0.0722 * chans[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def palette(css, selector_pattern):
    m = re.search(selector_pattern + r"\{([^}]*)\}", css)
    if not m:
        return None
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,6})", m.group(1)))


def check_css(css):
    """Phone, dark mode and print rules that the style sheet must keep. Returns a list of problems."""
    bad = []
    light = palette(css, r":root(?!\[|:)")
    dark_media = palette(css, r':root:not\(\[data-theme="light"\]\)')
    dark_attr = palette(css, r':root\[data-theme="dark"\]')
    if not (light and dark_media and dark_attr):
        return ["style sheet: the light palette, the system dark palette or the chosen dark palette is missing"]
    if dark_media != dark_attr:
        bad.append("style sheet: the dark palette that follows the system differs from the one the Light/dark button sets")
    pairs = (("fg", "bg"), ("fg", "card"), ("mut", "bg"), ("mut", "card"), ("mut", "code"), ("acc", "bg"), ("acc", "card"),
             ("acc-fg", "acc"), ("warn", "bg"), ("warn", "card"))
    for name, pal in (("light", light), ("dark", dark_attr)):
        for fg, bg in pairs:
            if fg in pal and bg in pal and contrast(pal[fg], pal[bg]) < 4.5:
                bad.append("style sheet: %s palette --%s on --%s has contrast %.1f, under 4.5" % (name, fg, bg, contrast(pal[fg], pal[bg])))
    m = re.search(r"@media print\{(.*)\n\}", css, re.S)
    if not m:
        bad.append("style sheet: no print rules")
    else:
        pr = m.group(1)
        for need, why in ((".top", "the header must drop out"), ("body.has-split main", "the scrolling pane must print in full"),
                          ("overflow:visible", "the scrolling pane must not clip"), ("--bg:#fff", "print must be black on white even in dark mode")):
            if need not in pr:
                bad.append("style sheet: print rules lack %r (%s)" % (need, why))
    ph = re.search(r"@media \(max-width:820px\)\{(.*?)\n\}\n", css, re.S)
    if not ph:
        bad.append("style sheet: no phone rules at max-width 820px")
    else:
        for need, why in (("min-height:44px", "tap targets of 44 px"), ("overflow-x:auto", "the site tabs scroll inside their own row"),
                          ("grid-template-columns:minmax(0,1fr)", "the viewer panel must not push the page wider")):
            if need not in ph.group(1):
                bad.append("style sheet: phone rules lack %r (%s)" % (need, why))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    started = time.time()
    out = Path(a.out).resolve()
    if not (out / "index.html").is_file():
        print("check-site: FAIL no built site in %s. Run: python3 scripts/docs-site/build.py" % out, file=sys.stderr)
        return 1
    files = {f.relative_to(out).as_posix() for f in out.rglob("*") if f.is_file()}
    pages = sorted(f for f in files if f.endswith(".html") and f not in EMBEDDED)
    scans = {f: parse(out / f) for f in pages}
    problems = []
    links = pictures = 0
    for f, s in scans.items():
        if not s.viewport:
            problems.append("%s: no viewport tag, so a phone shows it zoomed out" % f)
        problems += ["%s: %s" % (f, x) for x in s.problems]
        for src, alt in s.pictures:
            pictures += 1
            if alt is None or not alt.strip():
                problems.append("%s: picture without alt text: %s" % (f, src))
        here = Path(f).parent
        for tag, attr, val in s.refs:
            val = val.strip()
            if not val or val.startswith(SKIP_SCHEMES):
                continue
            links += 1
            if val in ALLOWED_OUTSIDE and tag == "a":
                continue
            if urlparse(val).scheme or val.startswith("//"):
                problems.append("%s: <%s %s=%s> leaves the site" % (f, tag, attr, val))
                continue
            target, frag = urldefrag(val)
            target = unquote(target.split("?", 1)[0])
            if not target:
                dest = f
            else:
                parts = []
                for seg in (here / target).as_posix().split("/"):
                    if seg == "..":
                        if parts:
                            parts.pop()
                    elif seg not in ("", "."):
                        parts.append(seg)
                dest = "/".join(parts)
                if dest + "/index.html" in files and dest not in files:
                    dest += "/index.html"
                elif dest == "":
                    dest = "index.html"
            if dest not in files:
                problems.append("%s: <%s %s=%s> does not exist in the site (check the name and its capital letters)" % (f, tag, attr, val))
                continue
            if tag == "img" and (out / dest).stat().st_size == 0:
                problems.append("%s: picture file is empty: %s" % (f, val))
            if frag and dest in scans and unquote(frag) not in scans[dest].ids:
                problems.append("%s: #%s is not on %s" % (f, frag, dest))
    css_file = out / "assets" / "site.css"
    problems += check_css(css_file.read_text(encoding="utf-8")) if css_file.is_file() else ["assets/site.css is missing from the site"]
    took = time.time() - started
    if problems:
        print("check-site: FAIL %d problem(s) in %d pages (%.1f s)" % (len(problems), len(pages), took))
        for p in sorted(set(problems))[:MAX_SHOWN]:
            print("  " + p)
        if len(set(problems)) > MAX_SHOWN:
            print("  ... and %d more" % (len(set(problems)) - MAX_SHOWN))
        return 1
    print("check-site: PASS %d pages, %d links and files, %d pictures with captions, phone, dark and print styles (%.1f s)" % (len(pages), links, pictures, took))
    return 0


if __name__ == "__main__":
    sys.exit(main())
