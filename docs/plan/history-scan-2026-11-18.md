# Secret scan, 2026-11-18

**Current files (HEAD):** no real secret. `scripts/check-no-keys.py` over every tracked file and `gitleaks` with `.gitleaks.toml` both pass. Test values carry the marker `FAKETESTKEY`, which the scanner and the gitleaks allowlist accept. `scripts/check.sh` now runs both (finding T-4); a key-shaped value without the marker fails the check.

**History (714 commits, `gitleaks --log-opts=--all`):** 12 findings in 8 commits, all checked by hand:
- private-network test keys made of letters like abcdefghi or zzzz, or marked FAKETESTKEY (`host/tests/test_settings_ui.py`, `host/tests/firmware/tailnet_travel_test.c`);
- `private-secret-123` in a Wi-Fi list test;
- a file hash (`sha256`) in a fixture README that the generic-key rule matched.

No value was a live credential. Run the history scan on request: `bash scripts/check.sh --history` (it fails until the history is replaced, because of those test fakes).

**Plan for the history (open decision 11, default):** publish a fresh squashed history and keep the old one private. Steps when the owner releases it:
1. Re-run the history scan one last time and keep the report in the private review repository.
2. Create the public branch from the tree of `main` as one commit (author: the noreply address), then run `scripts/check.sh --history` on it: it must pass with no allowlist entry for old fakes.
3. Push the squashed history to the public repository only; the 714-commit history stays in the private mirror.
