# Contributing

Read `docs/design/INDEX.md` and the one design note for your slice. Do not read the whole tree.

## Hard rules

- No dependency on any other MaiPai repo: no import, submodule or runtime call. Shared shapes are vendored, stamped snapshots with a drift check.
- Do not mention, compare to or credit other projects in code, docs, comments or commit text. Required notices go only in LICENSE, NOTICE, THIRD-PARTY.md and `# Upstream:` patch lines.
- An optional feature that is off costs no memory. Every firmware step passes the memory gate.
- Every feature has a body half and a brain half. A missing brain half hides the feature.
- Every error message says what went wrong and what to do.
- Follow `docs/STYLE.md`.

## Workflow

1. Run `bash scripts/install-hooks.sh` once per clone.
2. Make one logical change. Add a changelog fragment `changes/<slug>.<type>.md` for any user-visible change (planned).
3. Run `bash scripts/check.sh`. It must print "hygiene: ok".
4. Run long commands through `bash scripts/run-bg.sh NAME -- cmd...`, and read the log path, not the log.
5. Regenerate the index with `bash scripts/repo-map.sh` when files change.

## Licence

Contributions are under AGPL-3.0. Never commit keys, real addresses or names. Examples use 192.0.2.x and example.com.
