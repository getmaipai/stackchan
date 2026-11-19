#!/usr/bin/env python3
"""Character file checker: validates character files against schema/character.json with a small stdlib validator,
then checks the size, the file name, the face style name, based_on and the plain-text rule.
Usage: python3 scripts/character-check.py [FILE ...]   (no files: every host/maipai_body/characters/*.json)
Every problem prints one line `FILE: what is wrong. what to do.`; the exit code is 1 if there is any, else 0.
Placement: host-side development tool. No firmware change. Upstream: none."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "character.json"
CHAR_DIR = ROOT / "host" / "maipai_body" / "characters"
STYLES_PATH = ROOT / "scripts" / "virtual-unit" / "face_styles.py"
EM_DASH = "\u2014"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_styles() -> list:
    spec = importlib.util.spec_from_file_location("face_styles", STYLES_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.STYLES)


def _type_ok(value, kind: str) -> bool:
    if kind == "object":
        return isinstance(value, dict)
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (isinstance(value, float) and value.is_integer())
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "array":
        return isinstance(value, list)
    return True


def _walk(value, schema: dict, path: str, out: list) -> None:
    """Check one value against one schema node; append plain-words problems to out."""
    where = path or "the file"
    if "const" in schema and value != schema["const"]:
        out.append(f"{where} must be {schema['const']!r} but is {value!r}. Set it to {schema['const']!r}.")
        return
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{where} is {value!r}, which is not allowed. Use one of: {', '.join(str(v) for v in schema['enum'])}.")
        return
    kind = schema.get("type")
    if kind and not _type_ok(value, kind):
        out.append(f"{where} must be a {kind}. Change its value to a {kind}.")
        return
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            out.append(f"{where} is shorter than {schema['minLength']} characters. Make it at least {schema['minLength']} long.")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{where} is {len(value)} characters, over the limit of {schema['maxLength']}. Shorten it to {schema['maxLength']} or fewer.")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{where} is {value!r}, which does not match {schema['pattern']}. Rewrite it to fit that pattern.")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{where} is {value}, below the minimum of {schema['minimum']}. Raise it to {schema['minimum']} or more.")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{where} is {value}, above the maximum of {schema['maximum']}. Lower it to {schema['maximum']} or less.")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{where} is missing the key {key!r}. Add {key!r}.")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    out.append(f"{where} has the unknown key {key!r}. Remove it.")
        for key, sub in props.items():
            if key in value:
                _walk(value[key], sub, f"{path}.{key}" if path else key, out)


def _strings(value, path: str = ""):
    """Yield (path, text) for every key and string value in the data."""
    if isinstance(value, str):
        yield path or "the file", value
    elif isinstance(value, dict):
        for key, sub in value.items():
            yield from _strings(key, f"{path}.{key}" if path else key)
            yield from _strings(sub, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for i, sub in enumerate(value):
            yield from _strings(sub, f"{path}[{i}]")


def validate(data: dict) -> list[str]:
    """Return the problems of one character as plain sentences (empty when it is fine). The file name is not known here; see check_file."""
    schema = _load_schema()
    out: list = []
    if not isinstance(data, dict):
        return ["the file is not a JSON object. Make the top level one object with the character's keys."]
    _walk(data, schema, "", out)
    limit = schema.get("x-max-bytes")
    if limit:
        size = len(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        if size > limit:
            out.append(f"the file is {size} bytes as compact UTF-8, over the limit of {limit}. Shorten the persona or the about line.")
    styles = _load_styles()
    if list(schema.get("properties", {}).get("face", {}).get("properties", {}).get("style", {}).get("enum", [])) != styles:
        out.append("the schema's face.style list differs from STYLES in scripts/virtual-unit/face_styles.py. Make both lists the same.")
    face = data.get("face")
    if isinstance(face, dict) and isinstance(face.get("style"), str) and face["style"] not in styles:
        out.append(f"face.style {face['style']!r} is not a known style. Use one of: {', '.join(styles)}.")
    if "based_on" in data and data["based_on"] == data.get("id"):
        out.append(f"based_on is the same as id ({data['id']!r}). Set based_on to the id of the original, or remove it.")
    for path, text in _strings(data):
        if EM_DASH in text:
            out.append(f"{path} has an em dash. Replace it with a comma, a colon or a new sentence.")
    return out


def check_file(path) -> list[str]:
    """Return the problems of one file, each as `NAME: what is wrong. what to do.`."""
    path = Path(path)
    name = path.name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"{name}: the file cannot be read ({exc.strerror or exc}). Check the path."]
    except ValueError as exc:
        return [f"{name}: the file is not valid JSON ({exc}). Fix the syntax."]
    problems = validate(data)
    if isinstance(data, dict) and isinstance(data.get("id"), str) and data["id"] != path.stem:
        problems.append(f"the file name {path.stem!r} does not match id {data['id']!r}. Rename the file to {data['id']}.json or change the id.")
    return [f"{name}: {p}" for p in problems]


def main(argv: list) -> int:
    files = [Path(a) for a in argv] or sorted(CHAR_DIR.glob("*.json"))
    if not files:
        print(f"characters: no files found in {CHAR_DIR}. Add character files or pass paths.")
        return 1
    problems = [line for f in files for line in check_file(f)]
    for line in problems:
        print(line)
    if problems:
        return 1
    print(f"characters: ok ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
