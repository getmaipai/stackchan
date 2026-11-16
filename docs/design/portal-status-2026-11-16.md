# Wi-Fi portal, status 2026-11-16

Placement: unit firmware. Nothing is flashed; no USB was touched. Work tree: `~/esp/stackchan-rebase/portal`, branch `portal` from the `ours` tip (16fd45c), commits P01 to P05 (tip f7237b5). Patches are in `firmware/patches/` and on ORDER. Replaying them onto the tip reproduces the branch files exactly.

## Finding first: the base had no portal at all

The base build sets hotspot setup off, and the StackChan board sends every no-Wi-Fi case to the phone app setup (Bluetooth plus apps the core build removes). The old portal page was not even linked (the linker dropped it). A core unit with no Wi-Fi could only be fixed over USB. P05 wires the portal in behind `CONFIG_MAIPAI_WIFI_PORTAL` (default y); off restores the old path.

## Built

| Patch | What |
|---|---|
| P01 portal-page | One page, 3.3 KB of HTML plus a 1 KB string table (3.9 KB English). System fonts, inline CSS and JS, light and dark by browser setting, 48 px targets, nearby networks sorted by signal with tap to fill, code, password, host address, save. Plain-C core: 15 strings in English and Spanish, code check, lock, hotspot name, network tidy, host address. |
| P02 portal-routes | Replacement access point source. 4 handlers (was 24): `/`, `/scan`, `/submit`, and a catch-all 302 that covers every phone and PC captive-check address. No saved-network or advanced routes; saved names are never listed. Stop frees server, DNS, timers, scan list. |
| P03 portal-protect | Six-digit setup code made per window, shown on the unit's screen, required by `/submit` (constant-time check, 5 wrong codes lock the window). 8 minute window, then a new window with a new code. Hotspot `MaiPai-StackChan-<last4 hex>`. Screen hint now shows with captions off (F02 had silenced it). |
| P04 portal-language | Page language from the unit's saved face language (en or es). |
| P05 portal-wire | Kconfig switch, board opens the hotspot, `startNetwork` waits in setup instead of restarting into app setup. |

The host half exists: `PairingStore.create_pair_code` (10 minute code, 5 tries) shows the pairing code after the unit joins. The page tells the person the unit is joining; no host file was edited. The host address field saves the voice URL as `ws://host:8765` (port 8765 when none is typed).

## Component override answer (the design's open question)

It works with no fork and the lock check is untouched. `firmware/portal/portal.cmake` (one include line in `firmware/CMakeLists.txt`) defers a swap until `project()` has made every target: in the `78__esp-wifi-connect` build target it drops `wifi_configuration_ap.cc` and the two html embeds and adds our file. `managed_components` stays pristine, so `CHECKSUMS.json` and `dependencies.lock` still match (the lock diff in the tree is the IDF 6.1.1 version line from an earlier build, not ours). Checked in the build map: our object is linked, no html objects. A new component directory under `firmware/components` was rejected because that directory is git-ignored. Risk: our file defines the whole class, so a component version bump (pin is `~3.3.1`) needs the header compared again.

## Sizes (same tree, same sdkconfig, ESP-IDF 6.1.1)

| Build | App bytes |
|---|---|
| Before this work (no portal linked) | 3,093,200 |
| Old component portal wired in (measured by switching the swap off) | 3,216,560 |
| New portal (P05 tip) | 3,133,568 |

Saving against the old portal: 82,992 bytes (about 81 KB); the design estimate was 65 to 75 KB at the old pin, 140 to 150 KB at the newest. Cost against today's image: +40,368 bytes, because a working portal brings the web server, DNS and access point code that were linked out. Smallest slot 0x4f0000 (5,177,344): free 2,043,776 (39 percent). Static DIRAM 160,971 (was 161,163; old portal 161,179). Running RAM while setup is open is not measured; estimate 15 to 20 KB (two 4 KB tasks, server buffers, scan list), freed on Stop. The old portal held up to 7 sockets and an unbounded scan list.

## Tests

`host/tests/test_portal_core.py` (11 tests: page size at most 5 KB in both languages, no outside address, string table complete, page served over HTTP, route list, probe URLs, protection, wiring, patch headers) and `host/tests/firmware/portal_core_test.c` (built with `-Wall -Wextra -Werror`). The page was also opened in a browser against a mock in light and dark, English and Spanish.

## Still needs a unit

1. The screen hint fits and is readable (hotspot name, address, code).
2. Phones (iOS, Android) open the page by themselves on the open hotspot.
3. Joining: the access point changes channel while joining, so the answer may not reach the phone; the page then says the link was lost and the unit still joins. Check the real flow.
4. The boot flow: `startNetwork` now waits during setup; confirm the face and boot steps behind it are acceptable.
5. Runtime heap while open and after close.
6. Limit: the hotspot is open and the page is plain HTTP, so a neighbour in range can watch the password go by. A WPA2 hotspot keyed by the code is the follow-up; it needs the page to stop asking for the code.
