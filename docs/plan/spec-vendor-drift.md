# Vendored spec drift check, owner: playground track, 2026-11-17

- `scripts/spec-drift-check.sh` runs in `scripts/check.sh`. It compares `host/spec-vendor/spec` with `host/spec-vendor/MANIFEST.sha256`, and with the source tag named in `STAMP.md` when that tag is on the Mac.
- The playground track added only the script and the manifest. It does not edit `host/spec-vendor/spec`.
- App track rule: after a deliberate re-vendor, update `STAMP.md`, run `bash scripts/spec-drift-check.sh --update`, and commit the manifest in the same commit. A hand edit of a vendored file fails the check by design.
- Today: 388 files, identical to `spec-v0.1.208` (the snapshot is a trimmed subset; files the tag has and the snapshot lacks are allowed).
