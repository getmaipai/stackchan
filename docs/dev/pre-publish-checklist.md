# Before the repository goes public

Do these once, in order. Each is a switch or a check the owner or a release session confirms.

1. **Private vulnerability reporting.** The owner switches it on in the GitHub repository settings (Security, then "Private vulnerability reporting"). Until then SECURITY.md says it is off. When it is on, edit the "Report a problem privately" section of SECURITY.md to point at the Security tab.
2. **Security scan and exposure suite pass.** Run `bash scripts/security-scan.sh --write`; the results and date in SECURITY.md must come from the commit being published.
3. **Release gate.** `bash scripts/release.sh` runs the checks, the scan, the exposure suite and the tests first; a failure stops the release (decision 23).
4. **Robot network capture.** The bench capture in [the bench procedures](bench.md) has been done on a real unit, and its destination list replaces the placeholder in the egress table.
5. **Private wording.** `bash scripts/leak-sweep.sh --history` lists commit messages that need a look; the owner decides what to do with each.
6. **Signed release.** A real release key exists, and the web flasher and the update path were proven with a signed image on a unit.

## Community files

Done:

- [x] `CONTRIBUTING.md` in the root. It repeats the rules in [contributing](contributing.md) and says how to report a bug and propose a feature.
- [x] `CODE_OF_CONDUCT.md` in the root, in our own words.
- [x] `SUPPORT.md` in the root.
- [x] Issue forms in `.github/ISSUE_TEMPLATE/`: bug report, feature request, and `config.yml` with blank issues off.
- [x] `CHANGELOG.md` in the root, with an Unreleased section and no invented versions.
- [x] `LICENSE`, `NOTICE` and `THIRD-PARTY.md` exist; `SECURITY.md` and `VERIFY.md` exist.

Still to do:

- [ ] **Pull request rule.** [Contributing](contributing.md) does not say whether pull requests are accepted. The owner decides and writes it there. If they are accepted, add `.github/PULL_REQUEST_TEMPLATE.md` and change the "Pull requests" section of `CONTRIBUTING.md`. If not, say so in both places.
- [ ] **Private contact for conduct reports.** `CODE_OF_CONDUCT.md` asks people to open a bare issue because no private channel exists. Add one (the Security tab reporting from item 1 does not cover conduct), then edit "Report a problem" in that file.
- [ ] **Repository address.** `.github/ISSUE_TEMPLATE/config.yml` and the two forms link to `github.com/getmaipai/stackchan` on the `main` branch. Confirm both after the public repo exists.
- [ ] **Labels.** Create the `bug` and `enhancement` labels in the public repository, or the forms add none.
- [ ] **Link the new files from the README.** The "Help, contributing, license" section names only contributing and Troubleshooting. Add CONTRIBUTING, SUPPORT, CODE_OF_CONDUCT and CHANGELOG.
- [ ] **Changelog fragments.** [Contributing](contributing.md) says `changes/<slug>.<type>.md` is "planned". Build that, or remove the line, and decide how fragments join `CHANGELOG.md` at release.
- [ ] **First release entry.** Replace "Unreleased" with the real version and date when the first signed release is cut (item 6).
- [ ] **Draft notice.** [Writing style](../STYLE.md) rule 3 says the README carries a Draft notice until 1.0.0. Confirm the README is in the state the owner wants at publish.
- [ ] **Funding file.** `.github/FUNDING.yml` is staged. Publish the listing or remove the line before release, as the file says.
- [ ] **Repository settings.** Set the description and topics, switch on Issues, and decide on Discussions. SUPPORT.md says to open an issue, so leave Discussions off unless that page changes.
