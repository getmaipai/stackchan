#!/usr/bin/env python3
# Intent: every image in README.md, docs/user, docs/playground and docs/dev has a visible caption: a standalone image is followed by an italic line, and an image inside a table row or an <img> tag carries a non-empty alt text (the row names it). Owner rule 2026-11-18.
import re
import subprocess
import sys

files = [f for f in subprocess.run(["git", "ls-files", "README.md", "docs/user", "docs/playground", "docs/dev"], capture_output=True, text=True, check=True).stdout.split() if f.endswith(".md")]
bad = []
for f in files:
    lines = open(f).read().split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$", line):
            following = next((x for x in lines[i + 1:] if x.strip()), "")
            if not re.match(r"^\s*\*[^*].*\*$", following):
                bad.append(f"{f}:{i + 1}: image with no caption (add an italic line under it saying what it shows)")
        for alt in re.findall(r"!\[([^\]]*)\]\(", line) if line.lstrip().startswith("|") else []:
            if not alt.strip():
                bad.append(f"{f}:{i + 1}: table image with empty alt text (name what it shows)")
        for tag in re.findall(r"<img\s[^>]*>", line):
            if not re.search(r'alt="[^"]+"', tag):
                bad.append(f"{f}:{i + 1}: <img> with no alt text")
if bad:
    print("captions: FAIL\n" + "\n".join(bad[:30]))
    sys.exit(1)
print("captions: ok")
