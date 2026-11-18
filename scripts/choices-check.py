#!/usr/bin/env python3
"""Every key of robot.toml needs a row in docs/dev/settings-justification.md (owner decision 20, docs/dev/choices-rule.md)."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))


def keys() -> list[str]:
    from pydantic import BaseModel

    from maipai_body.config import RobotConfig

    out: list[str] = []

    def walk(model, prefix=""):
        for name, field in model.model_fields.items():
            ann = field.annotation
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                walk(ann, prefix + name + ".")
            else:
                out.append(prefix + name)

    walk(RobotConfig)
    return out


def main() -> int:
    table = (ROOT / "docs" / "dev" / "settings-justification.md").read_text()
    documented = set(re.findall(r"^\|\s*`([^`]+)`\s*\|", table, re.M))
    missing = [k for k in keys() if k not in documented]
    if missing:
        print("choices: these robot.toml keys have no row in docs/dev/settings-justification.md: " + ", ".join(missing))
        print("Add one row each: who needs it, what it costs, why the default is not enough, and its disposition (docs/dev/choices-rule.md).")
        return 1
    print(f"choices: ok ({len(documented)} keys justified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
