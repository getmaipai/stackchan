# Check this project yourself

Copy the prompt below into your own AI coding assistant, with this repository open. It asks the assistant to read the files that decide what the robot and the host can reach, and to report only what it can show.

```text
You are reviewing the open-source repository "MaiPai for StackChan" (firmware for a desk robot plus a host program). Claims to test: (1) nothing in the robot or the host contacts a server the owner did not choose; (2) updates are signed and a bad or older image is refused; (3) the settings page cannot be used by someone else on the network without a token.

Read these files and quote the lines that decide each answer. Say "not found" or "not sure" where that is true; do not guess.

Network and outbound calls:
- host/maipai_body/bodies/stackchan/xiaozhi/server.py (what listens, and on which address)
- host/maipai_body/app.py (search for "0.0.0.0", "lan", "SettingsServer")
- host/maipai_body/brain_setup/ (the only downloads: which addresses, how they are checked)
- host/maipai_body/bodies/stackchan/updater.py and host/maipai_body/bodies/stackchan/firmware_update.py (what an update check sends, what is verified before install)
- firmware/patches/ (search added lines for http:// and https:// addresses)
- host/maipai_body/bodies/stackchan/firmware/host-search.sh (proves vendor cloud addresses are gone from an image)

Update path:
- docs/plan/signed-update-header.md and docs/plan/signed-update-anti-rollback.md, then the code they name
- flasher/ (signature check in the browser, flasher/trusted-keys.json)

Host sign-in:
- host/maipai_body/settings_server.py and host/maipai_body/local_guard.py (who counts as local, the token, the Host check, the lockout)

Also run: bash scripts/security-scan.sh and compare its output with SECURITY.md.

Report: for each claim, "supported", "not supported" or "cannot tell", the file and line that decide it, and anything you found that the project does not state.
```
