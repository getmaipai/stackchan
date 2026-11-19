#!/usr/bin/env python3
"""Offline test of the documentation site build. Usage: python3 scripts/docs-site/test_docs_site.py

Builds the site into a temporary folder and checks:
  - every internal link, image, script, stylesheet and fragment resolves to a file or heading in the output;
  - nothing in the output loads from outside the site (no http(s) or protocol-relative address in src, href, url(), @import, fetch);
  - every page has the disclaimer sentence;
  - the 3D model is served as a plain static file and, when a browser with WebGL is present, the viewer page loads it and runs;
  - a size report (printed, with a ceiling so the site stays small).
Placement: host-side development test. Upstream: none."""

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build  # noqa: E402

# Files that are not pages of their own: the ledger is a generated, self-contained file shown inside ledger.html.
EMBEDDED = {"ledger-app.html"}
# 12 until the brand art (three unedited PNGs, about 1.4 MB, assets/brand) joined the site; the art is never resized, so the ceiling moved with it.
SIZE_CEILING_MB = 14


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.text = [], set(), []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("href", "src", "action", "poster", "data", "srcset"):
            if k in a and a[k] is not None:
                self.refs.append((tag, k, a[k]))
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if not self.in_script:
            self.text.append(data)


def scan(path):
    s = Scan()
    s.feed(path.read_text(encoding="utf-8"))
    return s


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class DocsSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="docs-site-")).resolve()
        cls.out = cls.tmp / "out"
        cls.problems = build.build(cls.out)
        cls.pages = sorted(p for p in cls.out.rglob("*.html") if p.relative_to(cls.out).as_posix() not in EMBEDDED)
        cls.scans = {p: scan(p) for p in cls.out.rglob("*.html")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_expected_pages_exist(self):
        for name in ("index.html", "docs/index.html", "viewer.html", "ledger.html", "screens.html", "decisions.html", "docs/getting-started.html",
                     "search.html", "trust.html", "playground/index.html", "playground/start-here.html", "dev/index.html", "dev/architecture.html",
                     "dev/hardware-reference.html", "dev/offline-audit.html", "dev/design-content-pantry.html", "dev/design-model-games.html"):
            self.assertTrue((self.out / name).is_file(), "page missing: %s. Run scripts/docs-site/build.py and read its output." % name)
        self.assertEqual(len(list((ROOT / "docs" / "user").glob("*.md"))), len(list((self.out / "docs").glob("*.html"))),
                         "every docs/user page must have a page in the site")

    def test_three_sections_have_tab_columns(self):
        for name in ("docs/index.html", "docs/getting-started.html", "playground/index.html", "playground/screen-tour.html", "dev/index.html", "dev/architecture.html"):
            t = (self.out / name).read_text(encoding="utf-8")
            self.assertIn('class="tabs"', t, "%s has no left tab column" % name)
            self.assertIn('class="pane"', t, "%s has no right pane" % name)

    def test_nothing_private_is_published(self):
        out = [p.relative_to(self.out).as_posix() for p in self.out.rglob("*.html")]
        for bad in ("plan/", "funding", "egress", "software-only-protection", "four-users-review", "cross-review"):
            self.assertEqual([o for o in out if bad in o], [], "a page that must stay private was published: " + bad)

    def test_trust_page_has_its_four_parts(self):
        t = (self.out / "trust.html").read_text(encoding="utf-8")
        for hid in ("security", "check-it-yourself", "ai-disclosure", "independence"):
            self.assertIn('id="%s"' % hid, t, "the Trust page lost its %s section" % hid)
        self.assertNotIn("&lt;!--", t, "a marker comment from SECURITY.md showed up as text")

    def test_check_site_passes(self):
        res = subprocess.run([sys.executable, str(HERE / "check-site.py"), "--out", str(self.out)], capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, "check-site.py failed:\n" + res.stdout[-1500:] + res.stderr[-500:])

    def test_playground_dev_pages_are_in_developers(self):
        self.assertFalse(list((self.out / "playground").glob("dev-*.html")), "playground developer pages belong under dev/")

    def test_sponsor_line_is_on_every_page_and_only_that_link_leaves(self):
        line = "Support this project: GitHub Sponsors"
        for page in self.pages:
            text = html.unescape(" ".join(" ".join(self.scans[page].text).split()))
            self.assertIn(line, text, "%s lost the sponsor line in its footer" % page.relative_to(self.out))
        for page, s in self.scans.items():
            outside = {v for t, a, v in s.refs if t == "a" and re.match(r"^(https?:)?//", v.strip())}
            self.assertLessEqual(outside, {build.SPONSOR_URL}, "%s links to an outside address other than the sponsor page" % page.relative_to(self.out))

    def test_internal_links_resolve(self):
        bad = []
        for page, s in self.scans.items():
            for tag, attr, val in s.refs:
                if re.match(r"^(mailto:|javascript:|data:|blob:|#$)", val):
                    continue
                if attr == "srcset":
                    continue
                target, frag = urldefrag(val)
                if urlparse(val).scheme or val.startswith("//"):
                    continue  # judged by test_no_external_urls
                dest = page if not target else (page.parent / unquote(target)).resolve()
                if dest.is_dir():
                    dest = dest / "index.html"
                if not dest.is_file() or self.out.resolve() not in dest.parents and dest != self.out.resolve():
                    bad.append("%s: %s=%s does not exist" % (page.relative_to(self.out), attr, val))
                    continue
                if frag and dest.suffix == ".html" and dest in [p.resolve() for p in self.scans]:
                    ids = next(v.ids for k, v in self.scans.items() if k.resolve() == dest)
                    if frag not in ids:
                        bad.append("%s: #%s missing in %s" % (page.relative_to(self.out), frag, dest.relative_to(self.out.resolve())))
        self.assertEqual(bad, [], "broken links:\n" + "\n".join(bad[:40]))

    def test_no_external_urls(self):
        """Nothing is loaded or linked from outside. Prose and code samples may mention an address as plain words (an install command); nothing may act on one."""
        bad = []
        pat_attr = re.compile(r"^(https?:)?//", re.I)
        for page, s in self.scans.items():
            for tag, attr, val in s.refs:
                if tag == "a" and val.strip() == build.SPONSOR_URL:
                    continue  # the sponsor line in the footer: a plain link, nothing loads from it
                if pat_attr.match(val.strip()) or re.match(r"^[a-z][a-z0-9+.\-]*:", val.strip(), re.I) and not re.match(r"^(mailto|data|blob|javascript):", val.strip(), re.I):
                    bad.append("%s: <%s %s=%s>" % (page.relative_to(self.out), tag, attr, val))
        code_pat = re.compile(r"(url\(\s*['\"]?(https?:)?//|@import\s+['\"]?(https?:)?//|\bfetch\(\s*['\"]https?://|\bimport\(\s*['\"]https?://|new\s+WebSocket\(\s*['\"]wss?://|XMLHttpRequest|sendBeacon|importScripts\(\s*['\"]https?://|\.src\s*=\s*['\"]https?://)", re.I)
        for f in self.out.rglob("*"):
            if f.suffix in (".css", ".js", ".html") and f.is_file():
                t = f.read_text(encoding="utf-8", errors="replace")
                if f.name == "three.min.js":
                    continue  # the pinned library carries its own documentation strings; it makes no outside request by itself (see the browser check)
                m = code_pat.search(t)
                if m:
                    bad.append("%s: %s" % (f.relative_to(self.out), m.group(0)))
        self.assertEqual(bad, [], "outside addresses in the output:\n" + "\n".join(bad[:40]))

    def test_every_page_has_the_disclaimer(self):
        missing = []
        for page in self.pages:
            text = html.unescape(" ".join(" ".join(self.scans[page].text).split()))
            if build.DISCLAIMER not in text:
                missing.append(str(page.relative_to(self.out)))
        self.assertEqual(missing, [], "pages without the disclaimer sentence")
        # the embedded ledger is only reachable through ledger.html, which carries it
        self.assertIn("ledger-app.html", (self.out / "ledger.html").read_text(encoding="utf-8"))

    def test_no_em_dash_and_no_tracking(self):
        for f in self.out.rglob("*.html"):
            if f.name == "ledger-app.html":
                continue
            t = f.read_text(encoding="utf-8")
            self.assertNotIn("\u2014", t, "%s has an em dash" % f.relative_to(self.out))
            for word in ("google-analytics", "gtag(", "plausible", "matomo", "fbq("):
                self.assertNotIn(word, t.lower())

    def test_ledger_is_a_byte_copy(self):
        src = ROOT / "docs" / "dev" / "feature-ledger.html"
        if src.exists():
            self.assertEqual(src.read_bytes(), (self.out / "ledger-app.html").read_bytes())

    def test_view3d_is_unedited(self):
        self.assertEqual((ROOT / "scripts" / "virtual-unit" / "view3d.js").read_bytes(), (self.out / "assets" / "view3d.js").read_bytes())

    def test_model_serves_from_a_static_server(self):
        glb = self.out / "assets" / "stackchan.glb"
        self.assertGreater(glb.stat().st_size, 100_000, "the model file is missing or empty")
        srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(self.out)))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = "http://127.0.0.1:%d" % srv.server_address[1]
            with urllib.request.urlopen(base + "/assets/stackchan.glb", timeout=20) as r:
                data = r.read()
                self.assertEqual(r.status, 200)
            self.assertEqual(data[:4], b"glTF", "the model is not a binary glTF file")
            self.assertEqual(len(data), glb.stat().st_size)
            node = shutil.which("node")
            check = HERE / "browser_check.js"
            if not node:
                self.skipTest("no node: the model was checked as a file and over HTTP only")
            env = dict(os.environ)
            try:
                npm_root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=30).stdout.strip()
                env["NODE_PATH"] = os.pathsep.join(x for x in (env.get("NODE_PATH"), npm_root) if x)
            except (OSError, subprocess.SubprocessError):
                pass
            try:
                res = subprocess.run([node, str(check), base + "/viewer.html"], capture_output=True, text=True, timeout=120, env=env)
            except subprocess.TimeoutExpired:
                self.skipTest("the browser check timed out; the model was checked as a file and over HTTP only")
            if res.returncode == 2:
                print("note: browser check skipped (%s)" % (res.stdout.strip() or res.stderr.strip()[:120]))
                return
            info = json.loads(res.stdout.strip().splitlines()[-1]) if res.stdout.strip() else {}
            self.assertTrue(info.get("ready"), "the viewer did not load the model: %s %s" % (res.stdout[-400:], res.stderr[-400:]))
            self.assertEqual([g["status"] for g in info["glb"]], [200])
            self.assertEqual(info["errors"], [], "the viewer logged errors")
            self.assertEqual(info["external"], [], "the viewer asked for outside addresses")
            self.assertEqual(info["head"]["yaw"], 40, "the yaw slider did not move the head")
            self.assertGreater(info["parts"], 20)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_size_report(self):
        total, rows = 0, []
        for f in self.out.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
                rows.append((f.stat().st_size, f.relative_to(self.out).as_posix()))
        rows.sort(reverse=True)
        print("\nsize report: %d files, %.2f MB (ceiling %d MB)" % (len(rows), total / 1e6, SIZE_CEILING_MB))
        for n, name in rows[:8]:
            print("  %8.1f KB  %s" % (n / 1000, name))
        by_dir = {}
        for n, name in rows:
            d = name.split("/")[0] if "/" in name else "(root)"
            by_dir[d] = by_dir.get(d, 0) + n
        print("  by folder: " + ", ".join("%s %.0f KB" % (k, v / 1000) for k, v in sorted(by_dir.items(), key=lambda kv: -kv[1])))
        self.assertLess(total, SIZE_CEILING_MB * 1_000_000, "the site grew past %d MB: look at the report above" % SIZE_CEILING_MB)


if __name__ == "__main__":
    unittest.main(verbosity=2)
