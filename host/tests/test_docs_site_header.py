"""The docs site header, search box, favicon, social image and sponsor line, checked on a fresh build (no browser, no network).

Placement: host-side test of the docs site tooling (scripts/docs-site/build.py); no firmware change. Upstream: none.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def site():
    spec = importlib.util.spec_from_file_location("docs_site_build", ROOT / "scripts" / "docs-site" / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    out = Path(tempfile.mkdtemp(prefix="docs-site-header-")) / "out"
    build.build(out)
    yield out, build
    shutil.rmtree(out.parent, ignore_errors=True)


def pages(out: Path):
    return [p for p in sorted(out.rglob("*.html")) if p.name != "ledger-app.html"]


def test_every_page_has_the_search_box_under_the_header(site):
    out, _ = site
    for p in pages(out):
        t = p.read_text(encoding="utf-8")
        assert 'id="sitesearch-q"' in t and 'placeholder="Search the guide"' in t, f"{p.relative_to(out)} has no search box. Check page() in scripts/docs-site/build.py."
        assert t.index("</header>") > t.index('id="sitesearch-q"') > t.index('<nav aria-label="Site">'), f"{p.relative_to(out)}: the box must sit in the header, under the menu."
        assert "assets/search.js" in t, f"{p.relative_to(out)} does not load search.js."


def test_search_works_without_a_network(site):
    out, _ = site
    index = (out / "assets" / "search-index.js").read_text(encoding="utf-8")
    assert index.startswith("window.SEARCH_INDEX=["), "the search index must be a plain script file on the site"
    assert (out / "assets" / "search.js").is_file()
    for p in pages(out):
        t = p.read_text(encoding="utf-8")
        assert not re.search(r'(src|href|data-index)="https?://[^"]*search', t), f"{p.relative_to(out)} points search at another site"


def test_header_icon_favicon_and_social_image(site):
    out, build = site
    css = (out / "assets" / "site.css").read_text(encoding="utf-8")
    assert "maipai-bot-icon-light.png" in css and "maipai-bot-icon-dark.png" in css, "the header icon needs a light and a dark file"
    assert 'data-theme="dark"] .mark' in css and "prefers-color-scheme:dark" in css, "the header icon must follow the theme button and the system theme"
    for name in build.BRAND_FILES:
        assert (out / "assets" / "brand" / name).read_bytes() == (ROOT / "docs-site" / "assets" / "brand" / name).read_bytes(), f"{name} in the site is not the unedited copy"
    for p in pages(out):
        t = p.read_text(encoding="utf-8")
        assert 'rel="icon"' in t and "maipai-bot-icon" in t, f"{p.relative_to(out)} has no favicon"
        assert 'property="og:image"' in t and "maipai-bot-logo-light.png" in t, f"{p.relative_to(out)} has no og:image"
        assert 'name="twitter:card" content="summary_large_image"' in t, f"{p.relative_to(out)} has no twitter:card"
        assert "MaiPai for StackChan" in t[t.index('class="brand"'):t.index("</a>", t.index('class="brand"'))], f"{p.relative_to(out)}: the header must say MaiPai for StackChan"


def test_social_image_is_absolute_only_with_a_base_url(site):
    out, build = site
    other = out.parent / "with-base"
    build.build(other, "https://docs.example.org/guide/")
    t = (other / "docs" / "getting-started.html").read_text(encoding="utf-8")
    assert 'content="https://docs.example.org/guide/assets/brand/maipai-bot-logo-light.png"' in t
    build.build(other)
    t = (other / "docs" / "getting-started.html").read_text(encoding="utf-8")
    assert 'content="../assets/brand/maipai-bot-logo-light.png"' in t
    shutil.rmtree(other, ignore_errors=True)


def test_sponsor_line_everywhere_and_matches_funding(site):
    out, build = site
    funding = (ROOT / ".github" / "FUNDING.yml").read_text(encoding="utf-8")
    handle = re.search(r"^github:\s*\[([^\]]+)\]", funding, re.M).group(1).strip()
    assert build.SPONSOR_URL == f"https://github.com/sponsors/{handle}", "the sponsor address in build.py must be the account in .github/FUNDING.yml"
    line = "Support this project: [GitHub Sponsors](%s)." % build.SPONSOR_URL
    assert line in (ROOT / "README.md").read_text(encoding="utf-8"), "README.md lost its sponsor line in the footer"
    for p in pages(out):
        t = p.read_text(encoding="utf-8")
        assert 'Support this project: <a class="sponsor" href="%s">GitHub Sponsors</a>.' % build.SPONSOR_URL in t, f"{p.relative_to(out)} has no sponsor line in its footer"
        assert t.index('class="sponsor"') > t.index('<footer class="foot">'), f"{p.relative_to(out)}: the sponsor line belongs in the footer"
    home = (out / "index.html").read_text(encoding="utf-8")
    assert home.count("Support this project") == 1, "the home page shows the sponsor line twice: the README line must be left out of the home body"


def test_style_sheet_keeps_three_sizes_and_system_fonts(site):
    out, _ = site
    css = (out / "assets" / "site.css").read_text(encoding="utf-8")
    assert "system-ui,-apple-system" in css
    sizes = set(re.findall(r"--fs-[a-z]:([\d.]+rem)", css))
    assert len(sizes) == 3, f"the type scale must stay at three sizes, found {sorted(sizes)}"
    loose = [m for m in re.findall(r"font-size:([^;}]+)", css) if not m.startswith("var(--fs-") and m not in ("11pt", "100%")]
    assert loose == [], f"font sizes outside the three-size scale: {loose}. Use var(--fs-s), var(--fs-m) or var(--fs-l)."
