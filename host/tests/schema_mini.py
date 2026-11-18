"""A small JSON Schema checker for the subset the spec proposals use: type, enum, required, properties, additionalProperties, items, min, max, maxLength."""

from __future__ import annotations

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(value, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def errors(schema: dict, value, path: str = "$") -> list[str]:
    out: list[str] = []
    kinds = schema.get("type")
    if kinds is not None and not any(_is(value, k) for k in ([kinds] if isinstance(kinds, str) else kinds)):
        return [f"{path}: wrong type"]
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: {value!r} is not allowed")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{path}: below the minimum")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{path}: above the maximum")
    if isinstance(value, str) and "maxLength" in schema and len(value) > schema["maxLength"]:
        out.append(f"{path}: too long")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{path}: missing {key}")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                out += errors(props[key], item, f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                out.append(f"{path}: unexpected {key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            out += errors(schema["items"], item, f"{path}[{index}]")
    return out
