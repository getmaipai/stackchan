# Before the repository goes public

Do these once, in order. Each is a switch or a check the owner or a release session confirms.

1. **Private vulnerability reporting.** The owner switches it on in the GitHub repository settings (Security, then "Private vulnerability reporting"). Until then SECURITY.md says it is off. When it is on, edit the "Report a problem privately" section of SECURITY.md to point at the Security tab.
2. **Security scan and exposure suite pass.** Run `bash scripts/security-scan.sh --write`; the results and date in SECURITY.md must come from the commit being published.
3. **Release gate.** `bash scripts/release.sh` runs the checks, the scan, the exposure suite and the tests first; a failure stops the release (decision 23).
4. **Robot network capture.** The bench capture in [the bench procedures](bench.md) has been done on a real unit, and its destination list replaces the placeholder in the egress table.
5. **Private wording.** `bash scripts/leak-sweep.sh --history` lists commit messages that need a look; the owner decides what to do with each.
6. **Signed release.** A real release key exists, and the web flasher and the update path were proven with a signed image on a unit.
