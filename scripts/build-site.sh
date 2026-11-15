#!/usr/bin/env bash
# Intent: build a local static docs site (site/index.html and one page per doc) from README.md and docs/**/*.md.
# Usage: bash scripts/build-site.sh   then open site/index.html. Needs bun (uses the marked package through bunx).
set -eu
cd "$(dirname "$0")/.."
rm -rf site && mkdir -p site
css='body{font:16px/1.6 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}
nav{font-size:.9rem;margin-bottom:2rem}nav a{margin-right:1rem}pre,code{background:#f4f4f4;border-radius:4px}pre{padding:.8rem;overflow:auto}code{padding:.1rem .3rem}
table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.3rem .6rem}@media(prefers-color-scheme:dark){body{background:#161616;color:#ddd}pre,code{background:#262626}td,th{border-color:#444}a{color:#8ab4ff}}'
files=$(ls README.md docs/user/*.md docs/dev/*.md docs/design/*.md docs/STYLE.md | grep -v INDEX.md)
nav='<nav><a href="index.html">Home</a>'
out_of() { case "$1" in README.md) echo index.html;; *) echo "$(echo "${1%.md}" | tr / -).html";; esac; }
for f in $files; do n=$(out_of "$f"); nav+="<a href=\"$n\">$(basename "${f%.md}")</a>"; done; nav+="</nav>"
for f in $files; do
  n=$(out_of "$f"); body=$(bunx --bun marked@18.1.0 -i "$f")
  printf '<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>%s</title><style>%s</style>%s<main>%s</main>' "$f" "$css" "$nav" "$body" > "site/$n"
done
echo "site: $(ls site | wc -l) pages in site/"
