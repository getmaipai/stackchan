# Rebuild the firmware from the repo alone

Placement: unit firmware tooling. The build blocker "the image cannot be rebuilt from the repo" (2026-11-18) is closed by these files.

- `firmware/BASE` pins the outer upstream commit and the nested tree commit.
- `bash scripts/fw-rebuild.sh TREE` downloads both, applies every entry of `firmware/patches/ORDER` with `git apply`, and builds the plain image. `--compile-every N` builds after every Nth patch (1 = every patch; slow, each build is incremental after the first). `--from-local DIR` reuses a local copy instead of downloading. `--list-misplaced` prints `firmware/patches/MISPLACED`.
- `bash scripts/fw-build.sh TREE plain|bench|gate [JOBS]` builds one image. Overlays come from `firmware/configs/` (bench: serial tools, face bench, games bench, memory line; gate: memory line). It generates the language header and, for bench, the speech clips (needs macOS `say` and ffmpeg), and downloads the private-network client into `TREE/deps`, never the shared folder.
- `MISPLACED` lists the three patches stored with hunks in the wrong place (075, 106, 107); B01 repairs them, so builds between them are skipped by the compile step.

Measured 2026-11-18: fresh rebuild applied 238 of 238 patches; plain image built in 118 s with `-j4` (plus the download), bench image in 132 s.
