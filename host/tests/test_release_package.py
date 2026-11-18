"""The StackChan release package carries no Reachy body, and no recorded-moves package."""

import os
import subprocess
import sys
from pathlib import Path

HOST = Path(__file__).resolve().parents[1]


def test_the_hosted_stackchan_host_imports_without_the_reachy_body_or_the_moves_package():
    code = (
        "import sys, importlib.abc\n"
        "class Block(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.startswith(('maipai_body.bodies.reachy_mini', 'maipai_body.moves', 'reachy_mini')):\n"
        "            raise ImportError('blocked in a StackChan release: ' + name)\n"
        "sys.meta_path.insert(0, Block())\n"
        "import maipai_body.app, maipai_body.cli, maipai_body.settings_page, maipai_body.brain_setup.controller\n"
        "from maipai_body.app import _stackchan_selected\n"
        "print('ok')\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=HOST, env={**os.environ, "MAIPAI_HUB_HOST": "1"}, timeout=120)
    assert done.stdout.strip() == "ok", done.stderr[-600:]


def test_the_wheel_recipe_excludes_the_legacy_robot_code_and_the_sdk_is_only_an_extra():
    text = (HOST / "pyproject.toml").read_text()
    recipe = text.split("[tool.hatch.build.targets.wheel]", 1)[1].split("\n[", 1)[0]
    assert '"maipai_body/bodies/reachy_mini"' in recipe and '"maipai_body/moves"' in recipe
    base = "\n".join(l for l in text.split("dependencies = [", 1)[1].split("\n]", 1)[0].splitlines() if not l.strip().startswith("#"))
    assert "reachy" not in base.lower() and "gstreamer" not in base.lower()
    assert "reachy-mini==" in text.split("[project.optional-dependencies]")[1]
