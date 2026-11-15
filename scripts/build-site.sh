#!/usr/bin/env bash
# Intent: build a local static docs site (site/index.html and one page per doc) from README.md and docs/**/*.md.
# Usage: bash scripts/build-site.sh   then open site/index.html. Needs bun (uses the marked package through bunx).
set -eu
cd "$(dirname "$0")/.."
rm -rf site && mkdir -p site/images && cp docs/images/* site/images/ 2>/dev/null || true
css='img{max-width:100%;height:auto;border-radius:8px}body{font:16px/1.6 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}
nav{font-size:.9rem;margin-bottom:2rem}nav a{margin-right:1rem}pre,code{background:#f4f4f4;border-radius:4px}pre{padding:.8rem;overflow:auto}code{padding:.1rem .3rem}
table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.3rem .6rem}@media(prefers-color-scheme:dark){body{background:#161616;color:#ddd}pre,code{background:#262626}td,th{border-color:#444}a{color:#8ab4ff}}'
files=$(ls README.md docs/user/*.md docs/dev/*.md docs/design/*.md docs/STYLE.md | grep -v INDEX.md)
nav='<nav><a href="index.html"><b>Home</b></a>'
out_of() { case "$1" in README.md) echo index.html;; *) echo "$(echo "${1%.md}" | tr / -).html";; esac; }
dev=""; design=""
for f in $files; do n=$(out_of "$f"); l="<a href=\"$n\">$(basename "${f%.md}")</a>"
  case "$f" in docs/user/*) nav+="$l";; docs/dev/*) dev+="$l";; *) design+="$l";; esac; done
nav+="<details><summary>Developers</summary>$dev</details><details><summary>Design record and style</summary>$design</details></nav>"
for f in $files; do
  n=$(out_of "$f"); body=$(bunx --bun marked@18.1.0 -i "$f"); body=${body//..\/images\//images/}; body=${body//docs\/images\//images/}
  body=$(printf '%s' "$body" | perl -pe 's#href="\.\./(user|dev|design)/([A-Za-z0-9-]+)\.md#href="docs-$1-$2.html#g')
  case "$f" in
    README.md) body=$(printf '%s' "$body" | perl -pe 's#href="docs/(user|dev|design)/([A-Za-z0-9-]+)\.md#href="docs-$1-$2.html#g; s#href="docs/STYLE\.md#href="docs-STYLE.html#g');;
    docs/user/*) body=$(printf '%s' "$body" | perl -pe 's#href="([A-Za-z0-9-]+)\.md#href="docs-user-$1.html#g');;
    docs/dev/*) body=$(printf '%s' "$body" | perl -pe 's#href="([A-Za-z0-9-]+)\.md#href="docs-dev-$1.html#g');;
  esac
  printf '<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>%s</title><style>%s</style>%s<main>%s</main>' "$f" "$css" "$nav" "$body" > "site/$n"
done
echo "site: $(ls site/*.html | wc -l) pages in site/"
