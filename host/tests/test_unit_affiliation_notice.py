"""The unit's version page carries the project name and the short affiliation notice (owner policy 2026-11-18). The strings live in the firmware patch SF69
(maipai_version_core.h) and must equal docs/legal/affiliation.json ("project" and "short")."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JSON = json.loads((ROOT / "docs" / "legal" / "affiliation.json").read_text())


def _define(name: str) -> str:
    text = (ROOT / "firmware" / "patches" / "SF69-project-name-and-affiliation-notice.patch").read_text()
    m = re.search(rf'^\+#define {name} "(.*)"$', text, re.M)
    assert m, f"{name} is not defined by patch SF69"
    return m.group(1)


def test_the_unit_project_name_matches_the_json():
    assert _define("MV_PROJECT") == JSON["project"]


def test_the_unit_notice_matches_the_json():
    assert _define("MV_NOTICE") == JSON["short"]


def test_the_notice_names_no_one_it_should_not():
    notice = _define("MV_NOTICE").lower()
    assert "not affiliated with or endorsed by" in notice and "independent" in notice
