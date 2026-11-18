"""The asset store's kind table in the unit's core is the one in schema/asset-kinds.json (one definition, one place): same names, same order, same limits.

The unit knows the first MAS_KINDS kinds of the schema; a kind added to the schema later gets its row in the core with its own patch."""

from __future__ import annotations

import json
import re
from pathlib import Path

from firmware_order_cores import cores_dir

ROOT = Path(__file__).resolve().parents[2]


def test_the_core_kind_table_matches_the_schema(tmp_path_factory):
    schema = json.loads((ROOT / "schema" / "asset-kinds.json").read_text())["kinds"]
    text = (Path(cores_dir(tmp_path_factory)) / "maipai_assets_core.h").read_text()
    rows = re.findall(r'\{"(\w+)", (\d+), (\d+)u, (\d)\}', text)
    assert rows, "the kind table was not found in maipai_assets_core.h"
    assert int(re.search(r"#define MAS_KINDS (\d+)", text).group(1)) == len(rows)
    for (name, slots, max_bytes, owner), want in zip(rows, schema):
        assert name == want["kind"]
        assert int(slots) == want["max_slots"], name
        assert int(max_bytes) == want["max_item_bytes"], name
        assert int(owner) == {"signed": 0, "owner": 1, "unit": 2}[want["trust"]], name
    assert max(int(r[1]) for r in rows) <= int(re.search(r"#define MAS_MAX_SLOTS (\d+)", text).group(1))
