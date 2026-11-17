#!/usr/bin/env python3
"""Fail when a task whose stack is in PSRAM can reach flash or saved settings (patches TC02 and FM05).

Intent: a flash call (NVS, the flash driver, the partition API) or a read of saved settings on a task with a PSRAM stack asserts
in esp_task_stack_is_sane_cache_disabled and reboots the unit. It happened twice in two days (the listening ring task, the music
worker). This script finds every task created with an external-memory stack in the patched firmware tree, follows the calls its
function makes by name (a grep-level call graph over every function defined in the tree), and reports each path that ends at a
flash or settings call. A function in GUARDED is a reviewed boundary that is safe from a PSRAM stack by construction: the walk stops there.
Placement: host tooling for the developer (reads source; nothing runs on the robot).
Upstream: none (ours).

Usage:
  python3 scripts/psram-stack-lint.py --tree ~/esp/stackchan-rebase/merge/firmware
Exit 0: no unreviewed path. Exit 1: at least one path, printed as task -> function -> function ... : call.

Limits: calls are followed by name, and only when the name is defined in the caller's own file or has exactly one definition in the tree (a name several files define, such as update or run, is skipped, so the walk can miss a path through one); a call
through a function pointer, a std::function or a vtable is not followed. A new finding is reviewed by reading the path, then either
fixed (read the value once on the main task, as TC02 does) or added to GUARDED or ALLOWED with the reason.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".h", ".hpp"}
SKIP_DIRS = {"build", "build-bench", "managed_components", ".git", "components", "tests"}

# A creation with an external-memory stack: the IDF's WithCaps call, or a static task whose stack buffer is allocated in PSRAM.
CREATE_CAPS = re.compile(r"\bxTaskCreate(?:PinnedToCore)?WithCaps\s*\(\s*([A-Za-z_]\w*)")
CREATE_STATIC = re.compile(r"\bxTaskCreateStatic(?:PinnedToCore)?\s*\(")

# What a PSRAM-stack task must never reach.
DANGEROUS = re.compile(
    r"\b(nvs_[a-z_0-9]+|esp_flash_[a-z_0-9]+|spi_flash_[a-z_0-9]+|esp_partition_(?:read|write|erase_range|mmap)[a-z_0-9]*|"
    r"esp_ota_[a-z_0-9]+|Settings)\b"
)
# "Settings st(" / "Settings(" / "Settings::" as a use; a bare mention in a comment is stripped before this runs.
SETTINGS_USE = re.compile(r"\bSettings\b\s*(?:\w+\s*)?\(|\bSettings\s*::")

CONTROL = {"if", "for", "while", "switch", "catch", "return", "sizeof", "defined", "else", "do", "static_cast", "reinterpret_cast", "const_cast", "dynamic_cast", "new", "delete", "throw", "alignof", "decltype", "operator", "auto"}

# Reviewed boundaries: safe from a PSRAM stack by construction. The walk does not go inside them. Each is (reason, text its
# definition must contain, or "" when the safety is in how it is called); a guard whose text is gone is reported.
GUARDED = {
    "maipai_tb_prefs": ("TC02: from a task whose stack is not internal it returns the cache and asks the timer task to refresh", "stack_may_read_flash"),
    "maipai_tb_nvs_key": ("pure string helper", ""),
    "load_once": ("FM05: the saved privacy state is read once, on the main task at boot; a PSRAM-stack caller gets the closed answer", "maipai_flash_stack_ok"),
    "snapshot": ("FM05: the sound policy is read once, on the main task at boot (TC02 pre-read); a PSRAM-stack caller gets the default", "maipai_flash_stack_ok"),
    "find_restore_volume": ("FM05: restores the saved volume only on an internal stack", "maipai_stack_is_internal"),
    "find_begin": ("FM05: only reached with find=1, which only the self.audio.play_sound tool sets (the MCP task); maipai_sounds_play passes 0", ""),
}
# Reviewed paths that are fine, keyed "task:dangerous token" with the reason.
ALLOWED: dict[str, str] = {}


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def match_brace(text: str, open_at: int) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


class Tree:
    def __init__(self, root: Path) -> None:
        self.files: dict[Path, str] = {}
        for base in (root / "main", root / "xiaozhi-esp32" / "main"):
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if path.suffix in SOURCE_SUFFIXES and not (set(path.relative_to(root).parts) & SKIP_DIRS):
                    self.files[path] = strip_comments(path.read_text(errors="replace"))
        self.defs: dict[str, list[tuple[Path, str]]] = {}
        definition = re.compile(r"\b([A-Za-z_]\w*)\s*\([^;{}()]*(?:\([^()]*\)[^;{}()]*)*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?\{")
        for path, text in self.files.items():
            for match in definition.finditer(text):
                name = match.group(1)
                if name in CONTROL:
                    continue
                body = text[match.end() - 1 : match_brace(text, match.end() - 1) + 1]
                self.defs.setdefault(name, []).append((path, body))

    def tasks(self) -> list[tuple[str, Path, str]]:
        """(task name, file, body text) for every task with a PSRAM stack."""
        found: list[tuple[str, Path, str]] = []
        for path, text in self.files.items():
            for match in CREATE_CAPS.finditer(text):
                name = match.group(1)
                for where, body in self.defs.get(name, []):
                    found.append((name, where, body))
                if name not in self.defs:
                    found.append((name, path, ""))
            for match in CREATE_STATIC.finditer(text):
                call = text[match.end() : match.end() + 900]
                if not re.search(r"MALLOC_CAP_SPIRAM|heap_caps_malloc|stack", text[max(0, match.start() - 600) : match.end() + 900]):
                    continue
                if "MALLOC_CAP_SPIRAM" not in text[max(0, match.start() - 1500) : match.end() + 900] and "psram" not in call.lower():
                    continue
                lambda_start = call.find("{")
                if call.lstrip().startswith("[") and lambda_start >= 0:
                    end = match_brace(call, lambda_start)
                    found.append(("<lambda in %s>" % path.name, path, call[lambda_start : end + 1]))
                else:
                    ident = re.match(r"\s*([A-Za-z_]\w*)", call)
                    if ident and ident.group(1) in self.defs:
                        for where, body in self.defs[ident.group(1)]:
                            found.append((ident.group(1), where, body))
        return found

    def findings(self) -> list[tuple[str, list[str], str]]:
        """(task, call path, dangerous token) for every unreviewed path."""
        out: list[tuple[str, list[str], str]] = []
        for task, where, body in self.tasks():
            seen: set[str] = set()

            def walk(text: str, path: list[str], here: Path) -> None:
                for token in DANGEROUS.finditer(text):
                    word = token.group(1)
                    if word == "Settings" and not SETTINGS_USE.search(text[max(0, token.start() - 1) : token.end() + 40]):
                        continue
                    key = f"{task}:{word}"
                    if key not in ALLOWED:
                        out.append((task, path, word))
                for call in re.finditer(r"(?<![.>\w])([A-Za-z_][\w]*(?:::[A-Za-z_]\w*)*)\s*\(", text):
                    name = call.group(1).split("::")[-1]  # a member call (x.load(), p->run()) is not followed: its class is unknown
                    if name in GUARDED:
                        required = GUARDED[name][1]
                        if required and not any(required in inner for _w, inner in self.defs.get(name, [])):
                            out.append((task, [*path, name], f"guard for {name} lost (its body no longer contains {required})"))
                        continue
                    if name in CONTROL or name in seen or name not in self.defs:
                        continue
                    # A name defined in the caller's own file, else a name with one definition in the whole tree. A name that several
                    # files define (update, run, start) is skipped: following it would join unrelated classes.
                    same = [(w, b) for w, b in self.defs[name] if w == here]
                    candidates = same or (self.defs[name] if len(self.defs[name]) == 1 else [])
                    if not candidates:
                        continue
                    seen.add(name)
                    for where2, inner in candidates:
                        walk(inner, [*path, name], where2)

            walk(body, [task], where)
        unique: dict[tuple[str, str, str], tuple[str, list[str], str]] = {}
        for task, path, word in out:
            unique.setdefault((task, " ".join(path), word), (task, path, word))
        return list(unique.values())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tree", type=Path, required=True, help="the patched firmware directory (the one holding main/ and xiaozhi-esp32/)")
    args = ap.parse_args(argv)
    tree = Tree(args.tree.expanduser())
    tasks = tree.tasks()
    if not tasks:
        print(f"psram-stack-lint: no task with a PSRAM stack found under {args.tree}; check the --tree path.", file=sys.stderr)
        return 2
    found = tree.findings()
    for task, path, word in found:
        print(f"{' -> '.join(path)} : {word}")
    names = sorted({t for t, _, _ in tasks})
    print(f"psram-stack-lint: {len(names)} PSRAM-stack tasks ({', '.join(names)}); {len(found)} unreviewed path(s).")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
