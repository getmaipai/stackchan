#!/usr/bin/env python3
# ruff: noqa: E501
# Intent: compile a game table description (JSON) into the binary pack the unit's game engine plays (firmware patch G01,
# format in firmware/main/hal/maipai_games_core.h), check a pack, and sign one with the update key.
# Usage:
#   python3 scripts/game-pack.py build firmware/games/memory.json -o out/memory.mpk [--sign KEY.pem]
#   python3 scripts/game-pack.py info out/memory.mpk
#   python3 scripts/game-pack.py verify out/memory.mpk --pub PUBKEY.pem
# The description names counters, regions, states, texts and tones; the compiler turns them into numbers and says what
# is wrong, in plain words, for anything it cannot place. The unit's own checker runs again on the pack.
from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

MAGIC = b"MPGK"
VERSION = 1
HEADER = 40
MAX_PACK = 16384
SIG_LEN = 64
LIMITS = {"states": 16, "regions": 12, "shapes": 64, "texts": 32, "trans": 96, "actions": 255}
COUNTERS = 8
TEXT_LEN = 48
EDGE = (20, 28, 300, 220)  # left, top, right, bottom: the unit keeps the edges for its swipes
TONES = ("popup", "vibration", "success", "low_battery", "exclamation")
# Patch UI12: the games' own funny sounds, made in code (maipai_games_sfx_core.h; a test keeps these names equal to the header).
# A tone id is 0 to 4 for a shipped sound, 5 + n for clip n, 0x80 + g for group g (one clip of the group at random).
CLIPS = (
    "bonk_squeak", "bonk_boop", "squeak", "boing", "wah", "raspberry", "boop", "haha", "whistle", "trombone",
    "good", "fanfare", "bad", "cue0", "cue1", "cue2", "cue3", "cue4", "cue5",
    "rattle", "thud", "mystic", "ting",
)  # fmt: skip
GROUPS = ("bonk", "miss", "escape")
TONE_IDS = {
    **{name: i for i, name in enumerate(TONES)},
    **{name: 5 + i for i, name in enumerate(CLIPS)},
    **{name: 0x80 + i for i, name in enumerate(GROUPS)},
}
BOARD_CTR0 = 16  # a shape condition "board3" reads board cell 3 (counter 16 + 3)
TIMER_FROM_CTR = 0xFFFF
STAY, END, ANY_REGION, ANY = 0xFE, 0xFF, 0xFE, 0xFF
EVENTS = {
    "enter": 0, "timer": 1, "tap": 2, "swipe_l": 3, "swipe_r": 4, "shake": 5, "pet": 6,
    "tilt_l": 7, "tilt_r": 8, "tilt_f": 9, "tilt_b": 10, "easy": 11,
}  # fmt: skip
SHAPES = {"fill": 0, "circle": 1, "box": 2, "ring": 3, "text": 4, "line": 5, "mole": 6, "die": 7, "coin": 8}
SIZES = {"small": 0, "medium": 1, "large": 2}
GUARDS = {
    "ctr_eq": 1,
    "ctr_ne": 2,
    "ctr_lt": 3,
    "ctr_ge": 4,
    "seq_hit": 5,
    "seq_miss": 6,
    "seq_more": 7,
    "seq_last": 8,
    "reg_eq_ctr": 9,
    "cell_free": 10,
}
CTR_GUARDS = {"ctr_eq", "ctr_ne", "ctr_lt", "ctr_ge", "reg_eq_ctr"}
OPS = {
    "set": 0,
    "add": 1,
    "add_ctr": 2,
    "copy": 3,
    "rand": 4,
    "elapsed": 5,
    "div": 6,
    "seq_reset": 7,
    "seq_add": 8,
    "seq_rewind": 9,
    "seq_next": 10,
    "seq_to_ctr": 11,
    "tone": 12,
    "tone_ctr": 13,
    "save": 14,
    "set_reg": 15,
    "sub_ctr": 16,
    "floor": 17,
    "board_clear": 18,
    "board_place": 19,
    "board_bot": 20,
    "board_result": 21,
    "sync": 22,
    "light": 23,
    "celebrate": 24,
}


class PackError(ValueError):
    """The description cannot become a pack. The message says what to fix."""


def rgb565(text: str) -> int:
    if not (isinstance(text, str) and len(text) == 7 and text[0] == "#"):
        raise PackError(f"color {text!r} must look like #rrggbb. Write it that way.")
    try:
        r, g, b = (int(text[i : i + 2], 16) for i in (1, 3, 5))
    except ValueError as error:
        raise PackError(f"color {text!r} must look like #rrggbb. Write it that way.") from error
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def text_bytes(value: str, where: str) -> bytes:
    if not value.isascii() or any(ord(c) < 0x20 or ord(c) > 0x7E for c in value):
        raise PackError(
            f"{where}: the text {value!r} has a letter the unit's screen cannot draw. Use plain ASCII."
        )
    raw = value.encode("ascii")
    i = 0
    while i < len(raw):
        if raw[i : i + 1] == b"%":
            nxt = raw[i + 1 : i + 2]
            if not (nxt == b"%" or (nxt.isdigit() and int(nxt) < COUNTERS)):
                raise PackError(
                    f"{where}: in {value!r} a percent sign must be %0 to %7 (a counter) or %%. Fix it."
                )
            i += 1
        i += 1
    if len(raw) > TEXT_LEN - 1:
        raise PackError(
            f"{where}: the text {value!r} is {len(raw)} letters; the limit is {TEXT_LEN - 1}. Shorten it."
        )
    return raw.ljust(TEXT_LEN, b"\0")


def _index(names: list[str], name: object, what: str, where: str) -> int:
    if isinstance(name, int) and not isinstance(name, bool) and 0 <= name < len(names):
        return name
    if name not in names:
        raise PackError(
            f"{where}: {what} {name!r} is not defined (known: {', '.join(names) or 'none'}). Add it or fix the name."
        )
    return names.index(name)


def build(desc: dict, *, seed: int | None = None) -> bytes:
    """The pack (header, body and checksum; not signed) for a description."""
    name = desc.get("id", "")
    if not (
        isinstance(name, str)
        and 1 <= len(name) <= 11
        and all(c.islower() and c.isascii() or c.isdigit() or c == "_" for c in name)
    ):
        raise PackError(
            "id must be 1 to 11 lower case letters, numbers or underscores. Rename the game."
        )
    counters: list[str] = list(desc.get("counters", []))
    if not 1 <= len(counters) <= COUNTERS:
        raise PackError(f"counters must list 1 to {COUNTERS} names. Fix the list.")
    state_names = list(desc.get("states", {}))
    region_names = [r["name"] for r in desc.get("regions", [])]
    text_names = list(desc.get("texts", {}))
    if not 1 <= len(state_names) <= LIMITS["states"]:
        raise PackError(f"states must be 1 to {LIMITS['states']}. Fix the table.")
    if len(region_names) > LIMITS["regions"] or len(text_names) > LIMITS["texts"] or not text_names:
        raise PackError("regions must be at most 12 and texts 1 to 32. Fix the table.")
    all_mask = (1 << len(state_names)) - 1

    def state_mask(spec: object, where: str) -> int:
        if spec in (None, "all"):
            return all_mask
        names = [spec] if isinstance(spec, str) else list(spec)
        mask = 0
        for n in names:
            mask |= 1 << _index(state_names, n, "state", where)
        return mask

    def timer_of(st: dict) -> list[int]:
        spec = st.get("timer", [0, 0])
        if isinstance(spec, dict):  # {"ctr": name}: the time in a counter, in ms (a game that speeds up)
            return [TIMER_FROM_CTR, _index(counters, spec.get("ctr"), "counter", "state timer")]
        return list(spec) if isinstance(spec, list) else [spec] * 2

    states = b"".join(struct.pack("<HH", *timer_of(st)) for st in desc["states"].values())
    regions = b""
    for r in desc.get("regions", []):
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        if x < EDGE[0] or y < EDGE[1] or x + w > EDGE[2] or y + h > EDGE[3] or w <= 0 or h <= 0:
            raise PackError(
                f"region {r['name']}: it must lie inside x {EDGE[0]} to {EDGE[2]} and y {EDGE[1]} to {EDGE[3]}; the unit keeps the screen edges for swipes. Move it inward."
            )
        regions += struct.pack("<hhHH", x, y, w, h)
    shapes = b""
    for i, s in enumerate(desc.get("shapes", [])):
        where = f"shape {i}"
        kind = SHAPES.get(s.get("type"))
        if kind is None:
            raise PackError(f"{where}: type must be one of {', '.join(SHAPES)}. Fix it.")
        cond_ctr, cond_val = 0xFF, 0
        if s.get("when"):
            name_ = s["when"][0]
            if isinstance(name_, str) and name_.startswith("board") and name_[5:].isdigit() and int(name_[5:]) < 9:
                cond_ctr = BOARD_CTR0 + int(name_[5:])  # the Tic-Tac-Toe board cell (0 empty, 1 the person, 2 the unit)
            else:
                cond_ctr = _index(counters, name_, "counter", where)
            cond_val = int(s["when"][1])
            if not -128 <= cond_val <= 127:
                raise PackError(f"{where}: the 'when' value must be -128 to 127. Fix it.")
        aux = int(s.get("radius", s.get("thickness", 0)))
        text = 0
        if kind == SHAPES["text"]:
            text = _index(text_names, s.get("text"), "text", where)
            aux = SIZES[s.get("size", "medium")]
        sx, sy, sw, sh = s.get("x", 0), s.get("y", 0), s.get("w", s.get("r", 0)), s.get("h", 0)
        if kind == SHAPES["line"]:  # from (x, y) to (x2, y2): the end point rides in the width and height fields
            sw, sh = s.get("x2", 0), s.get("y2", 0)
        if kind == SHAPES["mole"]:  # the region counter picks the hole, the face counter the face; r is its size
            cond_ctr = _index(counters, s.get("region"), "counter", where)
            aux = _index(counters, s.get("face"), "counter", where)
            cond_val = 0
        if kind in (SHAPES["die"], SHAPES["coin"]):  # a value counter, and the mode in which it shows (counter, value)
            cond_ctr = _index(counters, s.get("value"), "counter", where)
            mode = s.get("mode")
            if mode:
                aux, cond_val = _index(counters, mode[0], "counter", where), int(mode[1])
            else:
                aux, cond_val = 0, -128
            sw = s.get("size", 60)
        shapes += struct.pack(
            "<BBbBhhhhHHBB",
            kind,
            cond_ctr,
            cond_val,
            aux,
            sx,
            sy,
            sw,
            sh,
            rgb565(s.get("color", s.get("colour", "#ffffff"))),  # "colour": an older pack file
            state_mask(s.get("states"), where),
            text,
            0,
        )
    texts = b""
    for key, tx in desc["texts"].items():
        if "en" not in tx:
            raise PackError(f"text {key}: it needs an English line. Add 'en'.")
        texts += text_bytes(tx["en"], f"text {key} (en)") + text_bytes(
            tx.get("es", ""), f"text {key} (es)"
        )
    trans = b""
    actions = b""
    n_trans = 0
    n_actions = 0
    for ri, rule in enumerate(desc["rules"]):
        where = f"rule {ri}"
        rule_states = rule["state"] if isinstance(rule["state"], list) else [rule["state"]]
        ev = EVENTS.get(rule["on"])
        if ev is None:
            raise PackError(f"{where}: 'on' must be enter, timer or tap. Fix it.")
        arg = 0
        if ev == 2:
            region = rule.get("region", "any")
            arg = (
                ANY
                if region == "any"
                else ANY_REGION
                if region == "any_region"
                else _index(region_names, region, "region", where)
            )
        g_kind, g_ctr, g_val = 0, 0, 0
        if rule.get("if"):
            g = rule["if"]
            if g[0] not in GUARDS:
                raise PackError(
                    f"{where}: guard {g[0]!r} is not one of {', '.join(GUARDS)}. Fix it."
                )
            g_kind = GUARDS[g[0]]
            if g[0] in CTR_GUARDS:
                g_ctr = _index(counters, g[1], "counter", where)
                g_val = int(g[2]) if len(g) > 2 else 0
        go = rule.get("go", "stay")
        nxt = (
            STAY
            if go == "stay"
            else END
            if go == "end"
            else _index(state_names, go, "state", where)
        )
        first = n_actions
        for act in rule.get("do", []):
            op = OPS.get(act[0])
            if op is None:
                raise PackError(
                    f"{where}: action {act[0]!r} is not one of {', '.join(OPS)}. Fix it."
                )
            a, v = 0, 0
            name_ = act[0]
            if name_ in ("set", "add", "rand", "div", "floor", "board_place"):
                a, v = _index(counters, act[1], "counter", where), int(act[2])
            elif name_ in ("add_ctr", "copy", "sub_ctr", "board_bot"):
                a, v = (
                    _index(counters, act[1], "counter", where),
                    _index(counters, act[2], "counter", where),
                )
            elif name_ in ("elapsed", "seq_to_ctr", "set_reg", "tone_ctr", "board_result", "sync"):
                a = _index(counters, act[1], "counter", where)
            elif name_ in ("light", "celebrate"):
                a, v = 0, int(act[1])
            elif name_ == "tone":
                if act[1] not in TONE_IDS:
                    raise PackError(
                        f"{where}: tone {act[1]!r} is not one of {', '.join(TONE_IDS)}. Fix the name."
                    )
                a = TONE_IDS[act[1]]
            actions += struct.pack("<BBh", op, a, v)
            n_actions += 1
        count = n_actions - first
        for st in rule_states:
            trans += struct.pack(
                "<BBBBBBhHBB",
                _index(state_names, st, "state", where),
                ev,
                arg,
                nxt,
                g_kind,
                g_ctr,
                g_val,
                first,
                count,
                0,
            )
            n_trans += 1
        # a rule on several states shares its action rows (the same first and count)
    if (
        n_trans > LIMITS["trans"]
        or n_actions > LIMITS["actions"]
        or len(desc.get("shapes", [])) > LIMITS["shapes"]
    ):
        raise PackError(
            "the game has too many rules, actions or shapes for the unit. Make it smaller."
        )
    score = _index(counters, desc.get("score", counters[0]), "counter", "score")
    title = _index(text_names, desc.get("title", text_names[0]), "text", "title")
    descr = (
        _index(text_names, desc["description"], "text", "description")
        if desc.get("description")
        else 0xFF
    )
    body = states + regions + shapes + texts + trans + actions
    payload_len = HEADER + len(body)
    header = struct.pack(
        "<4sBBBBBBHHBBIBBBBHH12s",
        MAGIC,
        VERSION,
        (1 if desc.get("lower_is_better") else 0) | (2 if desc.get("tap_on_release") else 0),
        len(state_names),
        len(region_names),
        len(desc.get("shapes", [])),
        len(text_names),
        n_trans,
        n_actions,
        score,
        int(desc.get("seq_range", 4)),
        int(desc.get("seed", 0) if seed is None else seed),
        int(desc.get("step_budget", 0)),
        _index(state_names, desc.get("start", state_names[0]), "state", "start"),
        title,
        descr,
        payload_len,
        0,
        name.encode("ascii").ljust(12, b"\0"),
    )
    assert len(header) == HEADER, len(header)
    payload = header + body
    blob = payload + struct.pack("<I", zlib.crc32(payload) & 0xFFFFFFFF)
    if len(blob) + SIG_LEN > MAX_PACK:
        raise PackError(
            f"the pack is {len(blob)} bytes; the unit's limit is {MAX_PACK} with a signature. Make the game smaller."
        )
    return blob


def openssl() -> str:
    for cand in (
        shutil.which("openssl"),
        "/opt/homebrew/bin/openssl",
        "/opt/homebrew/opt/openssl@3/bin/openssl",
    ):
        if cand and Path(cand).exists():
            probe = subprocess.run(
                [cand, "genpkey", "-algorithm", "Ed25519", "-out", "/dev/null"], capture_output=True
            )
            if probe.returncode == 0:
                return cand
    raise PackError(
        "OpenSSL with Ed25519 is needed to sign a pack. Install it with brew install openssl@3."
    )


def sign(blob: bytes, key_pem: Path) -> bytes:
    """The pack with its 64 byte Ed25519 signature appended (plain Ed25519 over the pack, as updates are signed)."""
    with tempfile.TemporaryDirectory() as tmp:
        msg = Path(tmp, "m")
        sig = Path(tmp, "s")
        msg.write_bytes(blob)
        run = subprocess.run(
            [
                openssl(),
                "pkeyutl",
                "-sign",
                "-rawin",
                "-inkey",
                str(key_pem),
                "-in",
                str(msg),
                "-out",
                str(sig),
            ],
            capture_output=True,
            text=True,
        )
        if run.returncode != 0:
            raise PackError(
                f"signing failed ({run.stderr.strip()}). Check the key file is an Ed25519 private key in PEM form."
            )
        out = sig.read_bytes()
    if len(out) != SIG_LEN:
        raise PackError("the signature is not 64 bytes. Use an Ed25519 key.")
    return blob + out


def verify(signed: bytes, pub_pem: Path) -> bool:
    body, sig = signed[:-SIG_LEN], signed[-SIG_LEN:]
    with tempfile.TemporaryDirectory() as tmp:
        msg, sg = Path(tmp, "m"), Path(tmp, "s")
        msg.write_bytes(body)
        sg.write_bytes(sig)
        run = subprocess.run(
            [
                openssl(),
                "pkeyutl",
                "-verify",
                "-rawin",
                "-pubin",
                "-inkey",
                str(pub_pem),
                "-in",
                str(msg),
                "-sigfile",
                str(sg),
            ],
            capture_output=True,
            text=True,
        )
    return run.returncode == 0


def info(blob: bytes) -> dict:
    if blob[:4] != MAGIC:
        raise PackError(
            "this is not a game pack (wrong first bytes). Use a file made by this tool."
        )
    vals = struct.unpack("<4sBBBBBBHHBBIBBBBHH12s", blob[:HEADER])
    payload = vals[16]
    crc_ok = (
        len(blob) >= payload + 4
        and zlib.crc32(blob[:payload]) & 0xFFFFFFFF
        == struct.unpack("<I", blob[payload : payload + 4])[0]
    )
    return {
        "id": vals[18].rstrip(b"\0").decode(),
        "version": vals[1],
        "lower_is_better": bool(vals[2] & 1),
        "tap_on_release": bool(vals[2] & 2),
        "states": vals[3],
        "regions": vals[4],
        "shapes": vals[5],
        "texts": vals[6],
        "transitions": vals[7],
        "actions": vals[8],
        "bytes": len(blob),
        "signed": len(blob) == payload + 4 + SIG_LEN,
        "crc_ok": crc_ok,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("description", type=Path)
    b.add_argument("-o", "--out", type=Path, required=True)
    b.add_argument("--sign", type=Path, help="Ed25519 private key (PEM): append the signature")
    i = sub.add_parser("info")
    i.add_argument("pack", type=Path)
    v = sub.add_parser("verify")
    v.add_argument("pack", type=Path)
    v.add_argument("--pub", type=Path, required=True, help="Ed25519 public key (PEM)")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "build":
            blob = build(json.loads(args.description.read_text()))
            if args.sign:
                blob = sign(blob, args.sign)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_bytes(blob)
            print(f"{args.out}: {len(blob)} bytes{' (signed)' if args.sign else ''}")
        elif args.cmd == "info":
            print(json.dumps(info(args.pack.read_bytes()), indent=2))
        else:
            ok = verify(args.pack.read_bytes(), args.pub)
            print("signature ok" if ok else "signature does NOT match")
            return 0 if ok else 1
    except (PackError, OSError, json.JSONDecodeError, KeyError) as error:
        print(f"game-pack: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
