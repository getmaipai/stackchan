"""The default firmware tree of the renderer tools is main's reference tree (scripts/ref-tree.py), never some other tree by luck; a missing or stale one fails with a plain message; the renderer goldens carry
a stamp of the ORDER they were made for (scripts/golden-stamp.py)."""
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_tree(tmp_path, commit=None):
    cfg = tmp_path / "firmware" / "build-bench" / "config"
    cfg.mkdir(parents=True)
    (cfg / "sdkconfig.h").write_text("")
    if commit is not None:
        (tmp_path / ".main-ref-commit").write_text(commit + "\n")
    return tmp_path


def test_the_environment_variable_wins(monkeypatch, tmp_path):
    rt = _load("ref-tree")
    monkeypatch.setenv("MAIPAI_FW_TREE_ROOT", str(tmp_path))
    assert rt.resolve() == (tmp_path, None)


def test_a_missing_reference_tree_says_what_to_run(monkeypatch, tmp_path):
    rt = _load("ref-tree")
    monkeypatch.delenv("MAIPAI_FW_TREE_ROOT", raising=False)
    monkeypatch.setenv("MAIPAI_FW_REF_TREE", str(tmp_path / "nothing-here"))
    tree, why = rt.resolve()
    assert tree is None and "missing" in why and "scripts/fw-ref-tree.sh" in why


def test_a_tree_without_its_commit_or_from_another_order_is_refused(monkeypatch, tmp_path):
    rt = _load("ref-tree")
    monkeypatch.delenv("MAIPAI_FW_TREE_ROOT", raising=False)
    monkeypatch.setenv("MAIPAI_FW_REF_TREE", str(_fake_tree(tmp_path / "a")))
    assert "no .main-ref-commit" in rt.resolve()[1]
    # a commit that is not in this checkout
    monkeypatch.setenv("MAIPAI_FW_REF_TREE", str(_fake_tree(tmp_path / "b", "0" * 40)))
    assert "does not have" in rt.resolve()[1]
    # the root commit of the repository has an ORDER that is not today's
    first = subprocess.run(["git", "-C", str(ROOT), "rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True).stdout.split()[0]
    monkeypatch.setenv("MAIPAI_FW_REF_TREE", str(_fake_tree(tmp_path / "c", first)))
    tree, why = rt.resolve()
    assert tree is None and ("older than" in why or "does not have" in why) and "fw-ref-tree.sh" in why


def test_a_tree_made_from_this_order_is_accepted(monkeypatch, tmp_path):
    rt = _load("ref-tree")
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    monkeypatch.delenv("MAIPAI_FW_TREE_ROOT", raising=False)
    monkeypatch.setenv("MAIPAI_FW_REF_TREE", str(_fake_tree(tmp_path, head)))
    assert rt.resolve() == (tmp_path, None)   # HEAD's own ORDER is the checkout's ORDER unless it is edited and uncommitted
    # (an uncommitted edit of ORDER makes the tree stale, which is the point)


def test_the_goldens_are_stamped_with_this_order():
    stamp = ROOT / "host" / "tests" / "golden" / "golden-order.sha1"
    assert stamp.exists(), "no host/tests/golden/golden-order.sha1: run scenarios.py (see scripts/golden-stamp.py)"
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "golden-stamp.py")], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout
    assert stamp.read_text().strip() == hashlib.sha1((ROOT / "firmware" / "patches" / "ORDER").read_bytes()).hexdigest()
