# Brand art, sponsor line and the docs-site header

The brand art is copied from the org repo and never edited. The docs site shows the MaiPai bot icon in its header and every page has a search box.

## The art

The source is the `brand/` folder of getmaipai/.github (commit `65d9a1bda753e3832e5178d50d6e1176c3854047`). Five PNGs are copied byte for byte into two folders:

- `host/maipai_body/assets/brand/` ships inside the host package.
- `docs-site/assets/brand/` feeds the docs site. The build copies the three files the site uses (bot icon light and dark, bot logo light) into the site.

Each folder has a `PROVENANCE.md` with the source commit, the sha256 of every file and the rule: never edit or redraw, refresh by copying again. To refresh, copy the files from the source folder into both folders, then update the commit and the hashes in both `PROVENANCE.md` files.

`host/tests/test_brand_assets.py` fails when a copy and its hash line disagree, when the two copies differ, or (on a machine that has the source folder) when a copy differs from the source file.

There is no StackChan-specific logo. The site uses the bot icon; the open question is in [open questions](open-questions.md).

## The docs-site header

- The header shows the bot icon (light or dark to match the theme button and the system theme) and the words "MaiPai for StackChan". The icon is a CSS background, so the theme choice needs no script.
- The favicon is the bot icon, with a light and a dark link chosen by the browser.
- `og:image` and `twitter:card` use the bot logo. A social card needs an absolute address, so `python3 scripts/docs-site/build.py --base-url https://host/path/` writes one. Without the option the address is relative and a card preview will not find it.

## The search box

Every page has a wide search box under the header (`assets/search.js`). It reads `assets/search-index.js`, a file on the site, so it works with no network. The index loads the first time you click in the box. Keys: type, Down and Up, Enter opens the marked page, Escape closes, `/` jumps to the box. On the Search page the same box filters the full page list.

## The sponsor line

"Support this project: GitHub Sponsors." with a link to the account in `.github/FUNDING.yml` sits in the README footer and in the footer of every docs-site page. It is the only link from the site to another address, and `check-site.py` allows exactly that one. `scripts/funding-check.py` keeps the address and `FUNDING.yml` in step.
