# Owner decisions and corrections

All dated 2026-11-15 unless noted. Later entries override earlier ones. Each is final until the owner changes it.

## Repo and structure

1. StackChan lives in its own repo, `getmaipai/stackchan`, for visibility and a clean split from other robots.
2. The repo is standalone. A user never clones another MaiPai repo. A hub is one optional brain among others.
3. The host contract is a schema. This repo vendors a stamped snapshot with a CI drift check. No shared package (decision 10).
4. No Docker in our own install path. A community Compose file may exist, never required.
5. Install is explicit. No silent service. `stackchan install-service` is an opt-in autostart.
6. Names: package `maipai-stackchan`, command `stackchan`.
7. The first working origin is a local bare repository on the build machine. The GitHub repo is created when the first cloud lane starts.
8. Install from GitHub first (`pipx install git+https://github.com/getmaipai/stackchan`). A PyPI listing comes later.
9. Windows service support is not in v1.
10. Shared code is a vendored, stamped copy per robot repo with a drift check.

## Scope

11. Scope rule: the bot does as much as possible locally. A feature goes to a hub when it needs an outside service,
    household-wide records, other devices or rooms, or policy. The grey zone gets a simple local version here and a household version in the hub, on the same schema.
12. The host calls no address the owner did not configure.
13. Standalone adds no content filter of its own (2026-11-15, correction). Content safety is the connected model's job.
    Body safety stays: servo limits, volume cap, wear limits, camera-on cue, mute, pairing security.
    An optional family-friendly persona preset may ship, labelled as a prompt and not a guarantee.

## Firmware

14. Settings gesture: fix swipe up. Diagnose the touch path on a real unit first.
15. Keep one small on-device command set (stop, mute, quiet, don't move). Free RAM first, measure, then add.
16. Radio power save: yes, test on the owner's mesh Wi-Fi first. Keep it only if the unit stays connected and replies as fast.
17. Gateway fallback: remove it now, as its own revertable patch.
18. Rebase before v1 (2026-11-15, overrides "stay on the old base"). Two hops: the first upstream pin, then the newest upstream. Detail in firmware-base.md.
19. No Bluetooth. Presence comes from the network, a private-network client and the camera.
20. Sound direction is rejected. The hardware cannot do it.

## Look and feel

21. Phone app: a web app served by the host. No native app. HTTPS for push alerts via a private-network certificate or reverse proxy.
22. Face style and colour are configuration. Colour may be none. Defaults are neutral and uncoloured until setup.
    Captions are optional on every face and off by default (correction to an earlier "on everywhere").
23. Thinking cue: visual dots always, plus a quiet tone on by default (2026-11-15, overrides "tone off"). Spoken fillers are optional and off.
24. The head touch strip drives quick sliders when `strip_mode = control`. Default is `petting`.
25. Spanish is the first non-English language. Every build step runs a language check.

## Process

26. Build trains: as few firmware builds and unit loads as possible. A train passes every host-side check first.
27. One physical unit only. The simulator is central and built first.
28. One first release with everything in v1. No tags or releases before it. Detail in release-and-updates.md.
29. Public text never mentions, compares to or credits other projects. Only the build-included notices in LICENSE, NOTICE and THIRD-PARTY.
30. An optional feature that is off costs no memory, and the memory gate proves it.
31. Ideas and designs are re-implemented in our own words. Nothing is copied that is not included in a build.

## Open

- Trademark check on the product and game names.
- Windows service support after v1.
- Whether the owner wants a second and third unit later (costs money, owner's call).
