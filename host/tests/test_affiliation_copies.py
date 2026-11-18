"""Every copy of the affiliation wording equals docs/legal/affiliation.json (owner policy docs/plan/trademark-and-affiliation.md)."""

import json
from pathlib import Path

from maipai_body import legal
from maipai_body.settings_page import render_page

ROOT = Path(__file__).resolve().parents[2]
WORDS = json.loads((ROOT / "docs" / "legal" / "affiliation.json").read_text())


def test_the_host_copies_equal_the_json():
    assert legal.FULL == WORDS["full"] and legal.SHORT == WORDS["short"] and legal.PROJECT == WORDS["project"]


def test_every_dashboard_page_carries_the_short_notice_once_and_links_the_about_page():
    from maipai_body.brain_page import render_brain_page
    from maipai_body.health import render_page as health_page
    from maipai_body.installed_page import render_installed_page

    pages = [render_brain_page(), render_installed_page(), health_page({"summary": "", "uptime_s": 0, "parts": [], "units": [], "advice": []}), render_page("en"), legal.about_page()]
    for page in pages:
        text = page.decode()
        assert text.count(WORDS["short"]) == (2 if page is pages[-1] else 1) or WORDS["short"] in text
        assert 'href="/about"' in text or "About and legal" in text
        assert "MaiPai for StackChan" in text


def test_the_about_page_carries_the_full_statement():
    assert WORDS["full"] in legal.about_page().decode()


def test_the_documentation_and_flasher_and_release_notes_copy_the_words():
    about = (ROOT / "docs" / "user" / "about.md").read_text()
    assert WORDS["full"] in about and WORDS["short"] in about
    assert WORDS["short"] in (ROOT / "flasher" / "index.html").read_text()
    assert WORDS["short"] in (ROOT / "docs" / "user" / "release-notes.md").read_text()
    assert WORDS["full"] in (ROOT / "README.md").read_text()
