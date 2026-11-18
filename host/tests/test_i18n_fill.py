"""Machine-drafted translations (host/maipai_body/i18n_fill): shape checks that do not need a native speaker."""
import json
import re
from pathlib import Path

from maipai_body import i18n

FILL = Path(i18n.__file__).parent / "i18n_fill"
FIELD = re.compile(r"\{[^{}]*\}")
TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def _files():
    return sorted(FILL.glob("*.json"))


def test_fill_files_have_a_known_language_and_known_keys():
    for path in _files():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["lang"] in ("fr", "de", "pt", "it"), path.name
        assert path.name.startswith(data["lang"] + "_"), path.name
        for key in data["strings"]:
            assert key in i18n.CATALOG["en"], f"{path.name}: {key} is not a catalog key: copy the key exactly"


def test_fill_keeps_placeholders_and_tags():
    for path in _files():
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, text in data["strings"].items():
            en = i18n.CATALOG["en"][key]
            assert text.strip(), f"{path.name}: {key} is empty"
            assert sorted(FIELD.findall(text)) == sorted(FIELD.findall(en)), f"{path.name}: {key} changed a {{placeholder}}: keep it exactly"
            assert sorted(TAG.findall(text)) == sorted(TAG.findall(en)), f"{path.name}: {key} changed a tag: keep it exactly"
            assert "\u2014" not in text, f"{path.name}: {key} has an em dash: use a comma or a period"


def test_fill_changes_the_catalog_and_formats():
    for lang in ("fr", "de", "pt", "it"):
        for key, text in i18n.CATALOG[lang].items():
            values = {name[1:-1]: "x" for name in FIELD.findall(text) if name[1:-1].isidentifier()}
            text.format(**values)  # a broken brace would raise here
