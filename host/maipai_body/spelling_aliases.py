"""The one place for the old British spellings the host still understands.

Owner rule (2026-11-16): American spelling everywhere. The names below are the only ones that keep
the old spelling, for two reasons:

* ``LEGACY_KEYS`` (old name to new name): a key an older saved file, an older settings page or an older
  caller may still send. The host reads the old key and writes the new one.
* ``UNIT_KEYS`` (new name to the name the flashed unit understands): the unit's firmware keys
  (``self.face.set_config``, ``self.prefs.set``) keep the old spelling until a unit update accepts both.
  The host sends the key the unit knows, built here and nowhere else.

The list and the reasons are in docs/design/spelling-aliases.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

LEGACY_KEYS: dict[str, str] = {
    "colour": "color",
    "listen_light_colour": "listen_light_color",
    "fx_colour_mode": "fx_color_mode",
}

UNIT_KEYS: dict[str, str] = {
    "color": "colour",
    "listen_light_color": "listen_light_colour",
    "fx_color_mode": "fx_colour_mode",
}


def upgrade_keys(values: Mapping[str, Any]) -> dict[str, Any]:
    """``values`` with every legacy key renamed to its current name (the current key wins when both are present)."""
    out: dict[str, Any] = {}
    for key, value in values.items():
        new = LEGACY_KEYS.get(key, key)
        if new != key and new in values:
            continue
        out[new] = value
    return out


def to_unit_keys(values: Mapping[str, Any]) -> dict[str, Any]:
    """``values`` with every key renamed to the spelling the flashed unit understands."""
    return {UNIT_KEYS.get(key, key): value for key, value in values.items()}


def from_unit_keys(values: Mapping[str, Any]) -> dict[str, Any]:
    """A unit's reply with its keys renamed to the host's names."""
    return upgrade_keys(values)
