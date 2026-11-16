# Calling the unit's tools without touching its link, 2026-11-16

Placement: bench procedure for the firmware lane. It was run on the owned unit on 2026-11-16 (results in `train3-2026-11-16.md`).

## The problem

The live hub host (a root process of the installed release 0.2.104 on this Mac) holds the unit's one link and does not know the newer tools. Pointing the unit at a second host means changing its saved host address, which is not allowed here, and stopping the hub is not allowed either.

## Options looked at

| Option | Verdict | Reason |
|---|---|---|
| A second host the unit is pointed to for a short test | Not used | The unit has no temporary host override: the address is one saved value in its flash, and the host-address tools were removed on purpose (patch 155). The only way is to change the saved value. |
| Read-only serial log of tool replies | Not enough | A reply goes to the link, not the log, and the hub does not call the new tools, so the log never shows them. |
| Stop the live hub for a while | Not allowed | It holds the household's link. |
| A serial tool path in the firmware (patch V01) | Used | One flash of a bench build. Nothing saved about the host changes, the hub keeps its link, and the replies come back on the cable. |

## What V01 is

A bench-only option, `MAIPAI_SERIAL_TOOLS` (off by default, so a shipped image has no reader and no USB driver). With it on, a line typed on the USB cable runs one tool through the same table the host uses, and the answer comes back as one `@reply` line.

- `@list [cursor]` lists the tools one page at a time (the reply's `nextCursor` is the next page).
- `@tool <name> [<json arguments>]` calls one tool, for example `@tool self.timer.set {"seconds":30,"label":"tea","silent":true}`.
- The stack is 8 KB in external RAM, the receive buffer is 512 bytes, and the task is created once at boot. Nothing on the network can reach it.

## Steps (repeatable)

1. Back up the flash and check the hash against its `.sha256` file (done as for every flash).
2. Build the bench image: add `CONFIG_MAIPAI_SERIAL_TOOLS=y` to `firmware/sdkconfig`, build, flash.
3. Open the cable at 115200 baud (opening it resets the unit once), wait for the line `serial tools are on` and about 20 seconds more, then send commands. Read each `@reply` line.
4. Put saved settings back: any tool that saves something (face settings, sound policy, idle motion) is read first and set back to what it read.
5. Run the 10-minute gate on the same image, then take the option out, rebuild, check the plain image is byte-identical to the earlier plain build, flash it and read the flash back.

## Risks and rollback

- Calling a tool that saves a setting changes the unit's saved state until it is put back. A partial call of `self.audio.set_sound_policy` sets every field it leaves out to its default, not to its current value, so read it first and send every field.
- `self.privacy.set` (mute, vision off, quiet) is not called on a bench run: it turns the microphone on or off.
- `self.firmware.update` and the Wi-Fi tools are not called.
- Rollback for the image: flash the saved plain image again (hash checked) or the full backup `~/stackchan-backups/2026-11-15/unit-flash-16MB.bin`.
