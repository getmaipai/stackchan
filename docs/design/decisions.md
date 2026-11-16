# Owner decisions and corrections

All dated 2026-11-15 unless noted. Later entries override earlier ones. Each is final until the owner changes it.

## Repo and structure

1. StackChan lives in its own repo, `getmaipai/stackchan`, for visibility and its own release cadence. The `bot` repo stops being a shared framework and becomes the Reachy Mini repo when that work resumes, or is archived (2026-11-15).
2. The repo is standalone. A user never clones another MaiPai repo. The `bot` repo is not a framework (2026-11-15).
3. The host contract is a schema. This repo vendors a stamped snapshot with a CI drift check. No shared package (decision 10).
4. No Docker in our own install path. A community Compose file may exist, never required.
5. Install is explicit. No silent service. `stackchan install-service` is an opt-in autostart.
6. Names: package `maipai-stackchan`, command `stackchan`.
7. The first working origin is a local bare repository on the build machine. The GitHub repo is created when the first cloud lane starts.
8. Install from GitHub first (`pipx install git+https://github.com/getmaipai/stackchan`). A PyPI listing comes later.
9. Windows service support is not in v1.
10. The capability API and record shapes are owned by `commons/spec`. Robot repos and Home vendor stamped definitions and fixtures with a drift check; they never vendor host code. There is no shared robot code repo (2026-11-15).

## Scope

11. Scope rule: the robot does what needs its body or talk loop. A feature goes to Home when it is the same for every bot, needs household records, other devices or rooms, or policy. The grey zone is limited to basics the robot must do alone, such as a timer or alarm (2026-11-15).
12. The host calls no address the owner did not configure.
13. The own-LLM brain adds no content filter of its own (2026-11-15, correction). Content safety is the connected model's job.
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

## Name check (2026-11-15)

"StackChan" is the name of M5Stack's own commercial desktop robot, and a community project spells it "Stack-chan". A web search found no trademark records either way. Before a public release, search the USPTO, EUIPO and WIPO registers and decide whether the product needs its own name. Status: decided by the owner on 2026-11-15: the user-facing project name is "MaiPai for StackChan". Still run the trademark register search before the public release.

## Scope: core and Home (2026-11-15)

The core MaiPai for StackChan app is a private voice robot, simple and single purpose. Camera features, watch mode, baby and pet monitor, find my robot, remote control, live view, games, the coding companion and integrations move to MaiPai Home (tag [Home] in `features.md`). The unit keeps their body halves and the cue code path. Firmware ships as two presets from one source, `core` and `home`; feature logic for those is not kept in this public repo (it lives in Home against a capability API this repo exposes). Detail: `docs/design/features.md` ("Core and Home").

## Bluetooth for v1 (decided 2026-11-15)

v1 ships with Bluetooth OFF (patch 098, a Kconfig switch). After v1 lands and the memory gate passes, measure the compiled-in-but-off cost and the running cost; if flash and idle heap cost stay near the owner's 1 KB figure, add phone setup over Bluetooth (start only during setup) as a DEFER feature. Presence by Bluetooth stays dropped. The review item stays in `features.md`.

## Migration order (owner, 2026-11-15)

Finish StackChan first. Then plan the Reachy Mini migration the same way (history-preserving extraction, vendored spec copy, own repo or Home package decided at that time, memory and cue rules carried over), and retire the old `bot` repo as the last step: archive it, move anything still needed, retire `bot/AGENTS.md` and `BODY-STACKCHAN-01`, and point Home's pins at the new repos. The Reachy plan gets its own design note when StackChan ships.
