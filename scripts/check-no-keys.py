#!/usr/bin/env python3
# Intent: refuse any firmware image, release folder or source tree that contains a key (safety fix).
# Usage: check-no-keys.py PATH...   (a file is scanned as bytes; a folder is scanned recursively)
# Exit 0: clean. Exit 1: a key-shaped value was found. The value is never printed: only the file, the kind and the byte offset.
# Used by: the firmware build (post-build step, patch 156, through MAIPAI_KEY_CHECK set in scripts/fw-env.sh),
#          the release tools, and by hand. The matching source-level rules live in .gitleaks.toml.
import os
import re
import sys

KINDS = [
    ("private-network auth key", re.compile(rb"tskey-[A-Za-z0-9]+-[A-Za-z0-9]{8,}")),
    ("private key block (header plus encoded body; the bare header text that crypto libraries carry is not a key)", re.compile(rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----\s*(?:[A-Za-z0-9+/=]{20,}\s*){2,}")),
    ("code host token", re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")),
    ("cloud access key id", re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("chat or model api key", re.compile(rb"\b(?:sk-[A-Za-z0-9_-]{24,}|xox[abprs]-[A-Za-z0-9-]{10,})")),
]
SKIP_DIRS = {".git", "build", "node_modules", "managed_components", "__pycache__", ".runs"}
MAX_BYTES = 256 * 1024 * 1024


def scan_file(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return [(path, "file too large to scan", 0)]
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        return [(path, f"unreadable ({exc.strerror})", 0)]
    hits = []
    for label, rx in KINDS:
        # Test fixtures use the marker FAKETESTKEY; every other match is refused.
        for m in rx.finditer(data):
            if b"FAKETESTKEY" in m.group(0):
                continue
            hits.append((path, label, m.start()))
            break
    return hits


def walk(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield os.path.join(base, name)


def main(argv):
    if not argv:
        print("usage: check-no-keys.py PATH...", file=sys.stderr)
        return 2
    hits = []
    count = 0
    for arg in argv:
        paths = walk(arg) if os.path.isdir(arg) else [arg]
        for p in paths:
            count += 1
            hits += scan_file(p)
    if hits:
        for path, label, off in hits:
            print(f"REFUSED: {path}: {label} at byte {off}. Remove it, rebuild, and keep keys in a file outside the repo. Nothing was released.", file=sys.stderr)
        return 1
    print(f"no keys found in {count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
