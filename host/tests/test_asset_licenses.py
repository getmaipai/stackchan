"""schema/licenses.json is the one definition of the asset store's license ids: unique, never 0 (the unit refuses 0), id 1 is the owner's own content."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_license_table_is_sound():
    t = json.loads((ROOT / "schema" / "licenses.json").read_text())
    ids = [row["id"] for row in t["licenses"]]
    assert len(ids) == len(set(ids)) and 0 not in ids and all(0 < i < 65536 for i in ids)
    assert t["owner_content_ids"] == [1] and ids[0] == 1 and t["licenses"][0]["spdx"].startswith("LicenseRef-")
    assert all(row["spdx"] for row in t["licenses"])


def test_the_unit_refuses_license_zero_and_the_owner_kinds_use_id_one():
    patch = (ROOT / "firmware" / "patches" / "SF89-asset-store-core.patch").read_text()
    assert "if (out->license == 0) return MAS_E_LICENSE;" in patch
    assert "h.license = 1;   /* the unit's own */" in patch
