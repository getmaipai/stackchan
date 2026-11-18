"""scripts/funding-check.py fails on a funding link that .github/FUNDING.yml does not list."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "funding-check.py"


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)], capture_output=True, text=True, timeout=60
    )


def _tree(tmp_path: Path, funding: str, readme: str, doc: str = "") -> Path:
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "FUNDING.yml").write_text(funding, encoding="utf-8")
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "page.md").write_text(doc, encoding="utf-8")
    return tmp_path


def test_listed_link_passes(tmp_path):
    root = _tree(tmp_path, "github: [example-owner]\n", "[Sponsor](https://github.com/sponsors/example-owner)\n")
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "funding: ok" in result.stdout


def test_unlisted_link_in_readme_fails_with_next_step(tmp_path):
    root = _tree(tmp_path, "github: [example-owner]\n", "Tip us at https://ko-fi.com/someone\n")
    result = _run(root)
    assert result.returncode == 1
    assert "README.md:1" in result.stderr
    assert "ko-fi.com/someone" in result.stderr
    assert "Add the account to FUNDING.yml or remove the link" in result.stderr


def test_unlisted_link_in_docs_fails(tmp_path):
    root = _tree(tmp_path, "# nothing live\n", "No links.\n", "See opencollective.com/example-collective\n")
    result = _run(root)
    assert result.returncode == 1
    assert "docs/page.md:1" in result.stderr


def test_commented_out_placeholder_does_not_count_as_listed(tmp_path):
    root = _tree(tmp_path, "# ko_fi: someone\n", "https://ko-fi.com/someone\n")
    assert _run(root).returncode == 1


def test_placeholder_handle_in_prose_is_not_a_link(tmp_path):
    root = _tree(tmp_path, "# nothing live\n", "Pattern: github.com/sponsors/<handle> and ko-fi.com/<handle>\n")
    assert _run(root).returncode == 0


def test_custom_and_scheme_and_case_differences_match(tmp_path):
    root = _tree(
        tmp_path,
        'ko_fi: Someone\ncustom: ["https://example.com/support"]\n',
        "http://www.KO-FI.com/someone/\n",
    )
    assert _run(root).returncode == 0


def test_repo_passes():
    result = _run(REPO)
    assert result.returncode == 0, result.stderr
