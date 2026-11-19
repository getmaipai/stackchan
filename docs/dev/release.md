# Release dry run (2026-11-19)

One full run of `scripts/release.sh` with a throwaway key on current `main`, to see what the release gate and the packaging do and how long they take. Nothing was published and the output folder was a scratch folder (`/tmp/rel-dry`, marked `TEST-KEY-NOT-FOR-RELEASE.txt`). The command:

```
bash scripts/release.sh --build-dir <tree>/firmware/build-plain --version 0.0.0-dry --date 2026-11-19 --build-number 1 --test-key --with-gate --app-image maipai-stackchan.bin --output /tmp/rel-dry
```

`--with-gate` makes a test-key run do what a real release always does: the checks, the security scan, the exposure suite and the whole host test suite run first, and any failure stops the release before anything is built.

## Timings (Mac Studio, 4 test processes)

| Step | Time | Result on the first run |
|---|---|---|
| `check.sh` and the security scan | about 5.5 minutes together | pass |
| Exposure suite (`exposure-test.py`) | 50 seconds | **fail**, fixed (below) |
| Host test suite (`test-all.sh`) | about 7.5 minutes | **fail** (below) |
| Packaging: signed manifest, update header, image signature, `SHA256SUMS` and its minisign signature, SBOM, evidence bundle | 2 seconds | pass |

The whole gate takes about 14 minutes when everything passes.

## What the dry run found and what was done

1. **Exposure suite: one outside address in the firmware tree.** `firmware/configs/sdkconfig.cloudtest.defaults` names the vendor's activation address for the cloud brain test image (decision 34). That overlay is never the default and never in a release. The check now allows exactly that host in exactly that file; the same host anywhere else, or another host in that file, still fails (`CLOUDTEST_FILE`, `CLOUDTEST_HOST` in `scripts/exposure-test.py`).
2. **Test suite: the sanitizer fuzz did not build.** The fuzz harness still called the pairing core the way it was before patch SF105. It now passes the time argument (`scripts/fuzz/core_fuzz.c`).
3. **Test suite: the end to end tests failed under load.** They shared one virtual environment, a stale renderer could hang a scenario, and two checks assumed an instant answer. All fixed (commit 668dad9f); both now pass in the 4 process run.
4. **Test suite: the golden frames.** The virtual unit renderer must be built from a firmware tree that holds the same patches as `firmware/patches/ORDER`, and its stamp (`.runs/vu-build/inputs.sha`, written by the test conftest) must be current. On this day no replayed tree (b66, b76, b77, b79) drew all of `main`'s goldens: 63 scenario frames differed or had no golden yet. That is the playground track's to land (a golden for each new scenario, drawn from the reference tree). **The release gate cannot pass until it does.**
5. **Packaging works.** The folder holds the signed `flash-manifest.json`, the image, its detached signature, the signed update header (`.hdr`, `.hdr.sig`), the public keys, `SHA256SUMS` with a minisign signature, and `release-evidence.tar.gz` (the host SBOM; with the gate on, the gate outputs too). The script re-verifies all three signatures before it says ok.

## Before a real release

- Build the renderer from the reference tree and write `inputs.sha`, then run `bash scripts/test-all.sh` alone (one run at a time: two runs at once share ports).
- Run the gate with the owner's key file: `--signing-key PATH` (never a command-line value) and a build number above `dist/last-build-number.txt`.
- Read `evidence/` and the checklist in [pre-publish-checklist.md](pre-publish-checklist.md). Publishing needs the owner's word.
