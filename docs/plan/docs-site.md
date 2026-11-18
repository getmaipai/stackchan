# Documentation site

A static site built from the user docs, the README, the feature ledger, the 3D model and the golden frames. It is published at release; the repository is private until then, so it is built and tested on a computer and not deployed.

## Build and test

```bash
python3 scripts/docs-site/build.py
```

Writes `docs-site/out/` (git-ignored). Open it through any static server, for example `python3 -m http.server -d docs-site/out`; the 3D viewer needs a server because a browser will not fetch the model from a `file:` address. Every other page also works from a file.

```bash
python3 scripts/docs-site/test_docs_site.py
```

Runs offline. It builds the site and checks that every internal link, image and heading anchor resolves, that nothing loads from or points at an outside address, that every page carries the disclaimer, that the model is a valid binary glTF served by a plain static server (and, when a browser with WebGL is present, that the viewer loads it and moves the head), and prints a size report with a 12 MB ceiling.

## What is in it

| Page | Source |
|---|---|
| Home | `docs-site/home-intro.html` and `README.md` |
| One page per user doc, and a searchable page list | `docs/user/*.md` |
| 3D viewer, view only, no unit | `docs-site/viewer.html`, `docs-site/viewer-stub.js`, `scripts/virtual-unit/view3d.js` (copied, not edited), `scripts/virtual-unit/model/stackchan.glb` |
| Feature ledger | `docs/dev/feature-ledger.html`, copied byte for byte (it is self-contained) and shown inside a page that carries the footer |
| Screens gallery | `docs/dev/screens/sheet-*.png` with the captions of `docs/dev/screens-contact-sheets.md`, and the golden frames under `host/tests/golden/` |
| Decisions log | `docs/design/decisions.md` |

The converter is a small one in `build.py` that handles what these docs use (headings, lists, tables, code, quotes, images, links, two span tags). It has no dependency, so there is nothing to pin. A link that leaves the site, or points at a repository file that is not a page, is shown as plain words with a dotted underline and no address. Code samples may still show an address as text.

The viewer loads `view3d.js` as it is. `viewer-stub.js` stands in for the unit: it holds the state object (head angles, ports, power, twelve lights), answers the model request and the screen request from files on the site, and wires the sliders and buttons. The screen shows a still of the face.

The disclaimer sentence is in the footer of every page. The pinned 3D library release is recorded in `THIRD-PARTY.md`.

## Deploying at release

1. Add a GitHub Actions workflow that runs `python3 scripts/docs-site/test_docs_site.py`, then `python3 scripts/docs-site/build.py`, then uploads `docs-site/out/` with the Pages artifact action and deploys it with the Pages deploy action. Pin each action by commit.
2. In the repository settings, set Pages to deploy from GitHub Actions.
3. Every link in the output is relative, so the site works under the `/<repository>/` path of a project site and at a custom domain without a setting. `docs-site/out/.nojekyll` is written so Pages serves the files as they are.
4. Run the workflow only after the repository is public and the release is cut. Until then nothing is deployed.

## Not included yet

- The interactive virtual robot (the real screen code, touch and the voice link in the page) needs WebAssembly. Another worker is on that spike. When it lands, it becomes one more page and a Simulation-only playground (decision 21); the viewer page here stays as the light version.
- Pages for documents outside `docs/user/` (design notes, plans, bench results) are not published.
- Translations of the site chrome. The page text is English.
