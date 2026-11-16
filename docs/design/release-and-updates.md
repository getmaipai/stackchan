# Release and updates

## Build from source, for anyone

- One command from a clone: `stackchan firmware build` (or `scripts/build.sh`).
- It installs the pinned toolchain into a user folder if missing, fetches the pinned sources by commit hash,
  applies our patches in order, builds, and writes an image plus a manifest. No Docker.
- It prints exact versions first, with a size and time estimate. The toolchain install is several GB.
- Options live in `firmware.toml`: board, language packs, face packs, features compiled in or out
  (private-network client, command model, captions, camera, LED ring), default Wi-Fi and host (empty by default), signing key.
- Reproducible: the same inputs give the same image hash. The build prints the patch list, the pinned commits and the licence list.
  `verify` compares a downloaded release image with a local build.
- The build writes a memory report. A release build below the memory gate floor fails.
- A public workflow lets anyone fork the repo and build their own image in the cloud, signed with their own key.
- Secret scan: after the build, scan the output and every image for key patterns. A key in an image makes it PRIVATE and blocks it from any release folder.
  Private builds read keys from a file outside the repo. Keys are single-use and short-lived.
- The flasher accepts the official image or a local file. `esptool` commands are documented too.

## Optional auto updater

Default: checking on, installing off. Nothing installs until the owner turns it on. Same keys in the toml, web settings and the unit.

- `update_channel`: stable, beta, or pinned.
- `update_source`: our release manifest (default), the owner's server or folder, or off.
- `update_check`: never, daily, weekly, manual. One small manifest request to the chosen source. The host checks, not the unit. Only the firmware version is sent.
- `update_install`: ask, auto, or auto within a window.
- `update_window`: allowed hours, idle only, no timer pending, on power or above a battery level, not in quiet hours. Needs a correct clock.
- `update_backup_first` (on by default): settings, packs, face, palette, wake and language choices, token hash, timers saved to a dated local folder. Last N kept, one-click restore. No Wi-Fi password unless the owner opts in, then encrypted.
- `update_verify`: Ed25519 signature check against trusted keys (ours, plus an optional owner key). Unsigned images are refused unless a developer override is set.
- `update_health_check`: after install the unit must reach the host and pass a self-test within 60 seconds, or it rolls back. A hang rolls back too, not only a crash.
- `update_notify`, `update_rollback` (two slots, one click), `update_pause`.
- Release notes in plain words before install. `contract_version` is checked so a unit never installs firmware the host cannot talk to.
- Host updates are suggested with the changelog and never installed silently.

Keep a documented USB recovery path. Keep the last known-good signed image on the host.

## One big first release

- No tags, releases or pre-releases before v1 is complete. Until then the repo is private and test builds carry a build id.
- v1.0.0 contains everything in v1 scope: firmware, host, web app, simulator, packs, docs.
- The repo goes public at that moment, after the hygiene scan of the whole history passes.
  A fresh repo whose first commit is the finished work is the simplest way to keep that clean.

## Release policy after v1

- Feature releases at most once every 6 to 8 weeks. Patch releases only for a security fix or a blocking bug.
- One release carries the firmware image, signed manifest, host package and changelog section. No per-component tags.
- Beta and dev builds are served on update channels from our manifest, not as releases.
- One product version (SemVer) for host and firmware, with build id and contract version on the About page.

## Changelog standard

- One `CHANGELOG.md`, newest first. Section `## v1.1.0 (date)` with Added, Changed, Fixed, Security, Removed.
- One plain sentence per item, about 20 words at most, written for the robot's owner. A docs link when there is one.
- No commit hashes, issue numbers or names of other projects. No em dashes or filler words.
- Each user-visible change adds a fragment file `changes/<slug>.<type>.md` in the same commit.
  The release script assembles the section, deletes the fragments and writes the release notes from the same text.
  No API calls, no commit scraping, no "Unreleased" section.
- A fast landing check warns when user-facing code has no fragment.
- Breaking changes are marked and name the contract version and what to update first.

## Less GitHub

- The working origin is a local bare repository. GitHub is a mirror pushed at releases and when a cloud lane needs a branch.
- No polling of GitHub, no `gh` calls for state git already knows, batched pushes, no pull requests, no hosted CI on private repos.
- When public: one push per release. The update check reads a static manifest, not the GitHub API.

## Wi-Fi portal

Today's page (inside the Wi-Fi setup component) is 63 KB at the old pin and 138 KB at the newest, sent uncompressed, English and 37 locales.
It is open and unauthenticated (see safety-and-privacy.md).

Replacement, one page (estimates, untested):

- About 4 to 5 KB (about 2 KB gzipped): system fonts, about 1 KB inline CSS, about 1.5 KB plain JS.
- Nearby networks sorted by signal, tap to fill, password, host address, save.
- One 15-string table in the chosen language. Light and dark by browser setting. Large targets. Same palette as the web settings.
- Keep `/`, `/scan`, `/submit` and the captive redirects. Drop the advanced and saved-network routes (24 handlers down to about 8).
- A protected window: 5 to 10 minute timeout, generic hex SSID.
- The server and DNS responder stop and free memory after setup.
- Saving: about 65 to 75 KB flash against the old pin, about 140 to 150 KB against the newest. Running RAM 3 to 6 KB.
- The web flasher sends Wi-Fi in the same dialog over USB. The portal is the fallback for later changes.

## Open

- Release signing key custody and what a fork signs with.
- Portal component override and the lock check: answered 2026-11-16, it works with no fork (portal-status-2026-11-16.md). Open: the portal on a real unit.
- Update windows depend on the clock fix: answered 2026-11-16, they use the host clock, so no unit clock fix is needed (ota-update-2026-11-16.md).
