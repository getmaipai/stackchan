# Handoff from the old bot firmware session: roaming, private network, updates (2026-11-17)

Placement: backlog note. Source: a message from the session that worked on the older `bot` firmware. Facts below are that session's findings, not yet re-checked here.

## Open items, in order

1. **Roaming (port, then test).** The old base has a fix (patch 154: scan for a better access point when signal stays below -70 dBm for 10 s; plus a recipe line). Our build does not have it. Cause of the earlier reboot: a self-heal restart at -77 dBm, because patch 044 pins the access point address so the unit never roams. Port the scan into this tree as a new patch, then test by carrying the unit between two access points of one network name and looking for a roam scan line in the unit log and no stall reboot.
2. **Private network (Tailscale).** The owner reports the old custom firmware had Tailscale fully working, the last open item being a suspected regional fix. Port that working client and its last fix from the old firmware (history only, never feature scope), do not redesign it. Handshakes started by the robot fail across different relay regions (robot far from the host's relay). They worked only when the host pinged first. A proper fix is not built. Our join is also untested with a real key.
3. **Wireless update (patch 133).** Unproven. The hub serves only releases installed on it; release builds must not carry the private-network client or any key. Never put an auth key in a release or a commit.
4. **Setup hotspot.** Keep the hotspot name `stackchan-XXXX` and the setup page staying open for several networks (both exist in the old base; check ours matches).

## Rules

- Test builds that contain an auth key live outside the repo and are never published.
- Do items 1 to 4 after the current UI batch (final6) lands; one flash window per batch.
