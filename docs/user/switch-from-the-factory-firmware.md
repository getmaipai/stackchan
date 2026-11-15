# Switch from the factory firmware, or go back

You can move to MaiPai for StackChan and back. The robot's hardware does not change, so nothing is lost for good.

## Before you start

- Plug the robot into power. Use the USB-C port on the base, so the motors do not move while you flash.
- Do not turn the head or the arms by hand unless you know the motors are off. If you feel resistance, the motors are on and forcing them can damage them.
- Your factory settings and the StackChan World app pairing do not carry over. If you want to keep using the app later, unbind the robot first: open **Setup** on the robot and choose the account unbinding option.

## Switch to MaiPai for StackChan

1. Follow [Getting started](getting-started.md). The web flasher puts the firmware on over USB.
2. Pair the robot with your host and set `llm_url`.
3. You'll know it worked when the robot answers a spoken question and `stackchan check` shows every line ok.

## Go back to the factory firmware

M5Stack's own flashing tool restores the factory firmware. The steps are on the [official docs](https://docs.m5stack.com/en/StackChan) under "Restore Factory Firmware".

1. On your computer, install M5Burner from the official page.
2. Open M5Burner, search for StackChan, tick **Only Official**, and download the latest firmware.
3. Connect the robot by USB-C, using the port on the base, and press the power button once.
4. In M5Burner, flash the firmware to the robot.
5. You'll know it worked when the robot shows the factory welcome page.

Run `stackchan forget` on your host first, so it no longer expects the robot.

## What you lose and what you keep

| | Switching to MaiPai for StackChan | Going back |
|---|---|---|
| Robot hardware | Unchanged | Unchanged |
| Factory settings and app pairing | Cleared. Unbind first to keep the account tidy | You pair again with the app |
| MaiPai settings and pairing | Created | Cleared |
| Your host files | Created on your host | Stay on your host, unused |

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
