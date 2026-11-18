# Names, marks and affiliation

Owner's policy, 2026-11-18. It applies to the firmware, the host program, the documentation and the web tools.

## The two statements

The wording lives in one place, `docs/legal/affiliation.json`, and every surface copies it from there. A test fails if a copy drifts.

Full statement, for the README and the documentation's About and legal page:

> MaiPai for StackChan is an independent project providing custom firmware and tools for the M5Stack StackChan robot. It is not affiliated with, endorsed by, or sponsored by M5Stack or the original StackChan creators. Product names and trademarks belong to their respective owners.

Short notice, for the viewers and each robot's local configuration page, linking to the full statement:

> Independent project. Not affiliated with or endorsed by M5Stack or the original StackChan creators.

Keep the notice small and in the same place on every page. It does not go on each control.

## Why

The project is named MaiPai for StackChan because it is firmware and tools for that robot. Saying which hardware it supports, and showing what that hardware looks like, is a different thing from presenting MaiPai as the maker's product.

An earlier pass removed the maker's name and marks from the 3D model. That was a precaution, not something a license or a published trademark policy required. The MIT license of the structure files does not require stripping names or logos. It also does not grant trademark rights or permission for every piece of artwork. So the project states its independence clearly, keeps the required attribution, and looks into specific assets where there is a real question. It does not erase accurate identifying details by default.

## Rules

1. **The model shows the real robot.** The 3D model carries the unit's own name, the maker's two-character mark and the label details. The local viewer and the public viewer use the same model; nothing strips marks for a public build.
2. **Marks on the robot are not our branding.** MaiPai's own name and icon go on page headers, application icons and the firmware's identity. The maker's and the robot's names are used where they are needed to say which hardware is supported and to credit its creators.
3. **Compliance marks are details of the hardware's label.** A drawn CE or FCC mark shows what the original label carries. It does not say that MaiPai's firmware, viewer or other software is certified, and the hardware's original compliance status does not necessarily cover modifications.
4. **Licenses and provenance stay.** Every required copyright, license and attribution notice stays with the redistributed source assets and builds (`LICENSE`, `NOTICE`, `THIRD-PARTY.md`, the model's `SOURCE.md`). Accurate credits, source names, URLs and provenance records may appear wherever they are useful.
5. **An affiliation statement is not a permission.** It does not replace a license obligation, grant trademark or artwork rights, or settle a specific restriction. Those are checked one by one.
6. **Before removing a mark**, name the exact asset, its source, the license or published policy that applies, and what is uncertain. A precaution is never presented as a legal requirement.

## What was checked (2026-11-18, model session)

| Asset | Source | What applies | Open question |
|---|---|---|---|
| The head, holder and base geometry | the maker's structure files (MIT), pinned in `scripts/virtual-unit/model/SOURCE.md` | MIT: the notice is kept in `NOTICE` and `THIRD-PARTY.md` | none found |
| The two-character mark, the robot's name on the side labels, the label artwork | drawn for this model in simple strokes from the owner's photos of his own unit; no artwork file of the maker's is copied | they depict the product; the names are the maker's | no brand or logo policy was found on the maker's site in one web search. A trademark listing site shows an application for the maker's name as pending; that site is a third party and was not verified against the official register. Whether the maker has terms for showing its logo in a third-party model is **not established** |
| CE and FCC marks on the drawn labels | drawn in simple strokes as part of the label | regulators' marks with their own rules on use on products and in marketing | shown only as details of the depicted label, never as a claim about this project. The regulators' rules were not read for this check |
| The owner's photos | the owner's own unit | not in the repository | none |

Nothing here is legal clearance. It records what the sources establish and what they do not.

## Where the statements go

| Surface | Statement | State on 2026-11-18 |
|---|---|---|
| `README.md` | full | in the Disclaimer section |
| Virtual unit viewer (`scripts/virtual-unit/view.html`) | short, linking to `/about` | done |
| Documentation's About and legal page (Pages) | full | to do: docs track |
| Each robot's local configuration page | short | to do: app and firmware tracks |
| Firmware About screen or its documentation | project identity, with the full statement in the documentation | to do: firmware track |

## Game names

Games use generic names only: Four in a Row, Mine Finder, Paddle, Fleet, Word Grid, Memory, Dots, Reversi-style names that are plain words. No trademarked game names: not Connect 4, Minesweeper, Pong, Battleship, Boggle, Scrabble, Simon or Tetris-like games. A new game is named from what it is, and a name that someone could have registered is checked before it ships.

## Open item: translating the short notice

The short notice on the unit's version page is English only (one wording, `docs/legal/affiliation.json`). It is not machine-translated: a translation needs a native and legal review first. Until then the page shows the English notice in every language.
