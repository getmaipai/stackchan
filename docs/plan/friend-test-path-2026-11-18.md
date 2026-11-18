# The friend-test path: what exists and what is missing (2026-11-18)

A friend with a StackChan and a Mac, Linux machine or Raspberry Pi, no Home and no help. Checked against the tree.

## Web flasher
- **Exists:** `flash_manifest.py` builds and signs a manifest (`stackchan flash` verifies one). `docs/images/flasher.svg` is a drawing.
- **Missing:** the page. Plan: a static page in `site/` using ESP Web Tools (pinned version, served from our own pages, no third-party scripts at run time), reading `flash-manifest.json` from the release. One Install button; Wi-Fi fields are optional (the robot's own setup page takes them).
- **Needs the owner:** the release key (open decision 10) before a signed manifest can ship. Build and test the page against an unsigned test manifest first.
- **Check:** open the page in a browser with the real unit on USB and flash it once; judge the screenshot.

## Pairing without a terminal
- **Exists:** `stackchan run` plus `stackchan pair` (code on the host, typed on the robot's setup page). The settings page can mint a code with a POST from the host computer.
- **Missing:** a button on the settings page (host computer) that shows the code large, so no second terminal is needed; a QR code on the robot's screen that joins the setup hotspot and opens the setup page (firmware, LVGL QR widget, in `handoff-roaming-tailnet-2026-11-17.md` item 5).
- **Order:** the settings-page code button (host only, small) first; the QR waits for the firmware track.

## Two units on one host
- **Done in the host:** calls that name no unit go to the longest-connected unit; per-unit model, persona, history, alarms and volume cap are tested (`test_stackchan_multi_unit.py`); firmware push and notify audio require a unit name.
- **Done since:** a call made during a unit's turn (voice commands, volume, alarms set by voice) goes to the unit that is talking (`ACTIVE_UNIT`, tested).
- **Done since (services):** household settings the background services push (sound policy, music features, idle motion) reach every connected unit when no unit is named; reads still come from the longest-connected unit (`_FAN_OUT_TOOLS`, tested with the playground's two fake units). Reads per unit (battery, privacy read-back) and per-unit light and alarm services are not split yet.
- **Missing:** a test with two real fake units connected to one `XiaozhiServer`, one tool call each, and a disconnect of the first while the second stays up; and per-unit background loops (idle motion, privacy read-back, self-heal): the services share one client bound to the longest-connected unit, and giving each unit its own stack of services is a larger change that needs the second unit on the bench. Run on the virtual unit when the playground track has two instances.
