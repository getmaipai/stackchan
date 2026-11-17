"""The American-spelling lint (scripts/spelling-check.py) and its hook in scripts/hygiene-check.sh."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("spelling_check", ROOT / "scripts" / "spelling-check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sc = _load()


def _scan(text: str, rules=()):
    return sc.scan_text("docs/x.md", text, list(rules))


def test_british_words_are_found_with_their_line_number():
    found = _scan("fine line\nThe colour of the behaviour\n")
    assert [(n, w) for n, w, _ in found] == [(2, "colour")]


def test_identifiers_plurals_and_ing_forms_are_found():
    for text in ("CENTRE_PITCH_DEG = 5", "fx_colour_mode", "colours", "it was cancelled", "cancelling now", "labelled", "the licence", "grey area", "analyse it", "normalised", "a metre", "centimetres"):
        assert _scan(text), text


def test_american_spelling_and_lookalikes_pass():
    for text in ("color center gray license canceled labeled analyzes", "greyhound", "the center of the room", "a parameter", "analysis and analyses of data"):
        assert not _scan(text), text


def test_the_allow_list_skips_matching_lines_and_whole_files():
    line = 'the old key "colour" is still read'
    assert _scan(line)
    assert not _scan(line, [("docs/*", "colour")])
    assert not _scan(line, [("docs/*", "*")])
    assert _scan(line, [("other/*", "*")])  # a rule for another path does not apply
    assert _scan('plain colour and "music_clip_cancelled"', [("docs/*", "music_clip_cancelled")]) == []


def test_allow_file_parsing_ignores_comments_and_blanks(tmp_path):
    allow = tmp_path / "allow.txt"
    allow.write_text("# why\n\nvendor/* :: *\nsrc/a.py :: legacy_colour\n")
    assert sc.load_allow(allow) == [("vendor/*", "*"), ("src/a.py", "legacy_colour")]


def test_the_command_line_fails_on_a_bad_file_and_passes_a_good_one(tmp_path):
    bad, good = tmp_path / "bad.md", tmp_path / "good.md"
    bad.write_text("Pick a colour.\n")
    good.write_text("Pick a color.\n")
    script = str(ROOT / "scripts" / "spelling-check.py")
    run = lambda *a: subprocess.run(["python3", script, "--root", str(tmp_path), "--allow", str(tmp_path / "none"), *a], capture_output=True, text=True)  # noqa: E731
    failed = run(str(bad))
    assert failed.returncode == 1 and "bad.md:1" in failed.stdout
    assert run(str(good)).returncode == 0


def test_the_repo_itself_is_clean():
    """Every tracked text file is American or allow-listed with a reason."""
    result = subprocess.run(["python3", str(ROOT / "scripts" / "spelling-check.py")], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout[-2000:]


def test_the_hygiene_hook_runs_the_lint_and_checks_the_commit_message(tmp_path):
    hook = ROOT / "scripts" / "hygiene-check.sh"
    words = tmp_path / "words.txt"
    words.write_text("zzzunlikelyzzz\n")
    bad = tmp_path / "bad.md"
    bad.write_text("The behaviour is odd.\n")
    env = {"NO_MENTION_WORDS": str(words), "PATH": "/usr/bin:/bin:/opt/homebrew/bin"}
    result = subprocess.run(["bash", str(hook), str(bad)], capture_output=True, text=True, env=env, cwd=ROOT)
    assert result.returncode == 1 and "British spelling" in result.stdout
    msg = tmp_path / "msg.txt"
    msg.write_text("Fix the colour\n")
    result = subprocess.run(["bash", str(hook), "--msg", str(msg)], capture_output=True, text=True, env=env, cwd=ROOT)
    assert result.returncode == 1 and "commit message" in result.stdout
