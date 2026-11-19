# Open questions for the owner

Questions that need the owner's word. Answer one by editing its section and moving the decision to the decisions log.

## StackChan logo

Is there a StackChan-specific logo for MaiPai for StackChan? The org brand folder has no such file, so the docs site and the host use the MaiPai bot icon and bot logo. If there is no StackChan logo, the bot icon stays and this question closes.

Where it matters: the docs-site header and favicon, the social image, and the host's brand icon route. Details: [brand art](brand.md).

## Host update channel: where the signed host release lives and who signs it

`stackchan update` installs the newest default branch of the repository with no pin, hash or signature (review fix R2-10 only refuses odd sources and hides credentials). A real fix needs one decision: where does a host release live and who vouches for it.

Options:

1. **The signed GitHub release of the public repo (recommended).** Each release publishes a wheel, `SHA256SUMS` and its minisign signature (the release script already produces them). `robot.toml` pins the release key and the host update checks the signature and the hash before installing. One place, no new service, works offline from a downloaded file.
2. A package index entry (PyPI): simple to install, but a second place to publish and sign, and the signature story is weaker.
3. Keep installing from the branch: fastest, but anyone who can push to the branch changes every host. Not recommended.

Recommended default: option 1, with the minisign public key pinned in `robot.toml` (`[update] host_key`) and the update refusing to run when the key is empty. It needs the owner's release key (already an owner-only item in the finish line).

Where it matters: `host/maipai_body/host_update.py`, `docs/user/run-as-a-service.md`, `docs/dev/release.md`.
