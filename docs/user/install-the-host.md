# Install, update and remove the host

The host is the program that runs on your computer, between the robot and your model. It runs on a Mac, a Linux machine or a Raspberry Pi 5.

## Install

1. Install `pipx` if you do not have it. Your system's package manager has it.
2. Run `pipx install git+https://github.com/getmaipai/stackchan`.
3. You'll know it worked when `stackchan --help` lists its commands.

No Docker is needed.

## Start it when the computer starts

Run `stackchan install-service`. It is off until you run it, and nothing runs as a silent service before then.
To stop it starting at boot, run `stackchan install-service --remove`.

Windows service support is not in this release.

## Update

Run `pipx upgrade stackchan`, then restart the host. The robot's firmware updates separately: see [Update the robot](updates.md).
If the host and the robot disagree about versions, the robot says so and names the side to update first.

## Remove

1. Run `stackchan forget` to unpair the robot.
2. Run `stackchan install-service --remove` if you set it to start at boot.
3. Run `pipx uninstall stackchan`.
4. Delete the host's folder of settings and snapshots if you want them gone.

You'll know it worked when `stackchan --help` no longer runs. To put the factory firmware back on the robot, see [Switch from the factory firmware, or go back](switch-from-the-factory-firmware.md).

## Firewall

The robot connects to the host, so the host must accept that connection. The host prints its port when it starts.
If you run a firewall, allow only what the host needs:

| Direction | Who | To | Why |
|---|---|---|---|
| In | The robot | The host, on the port it prints | Voice, events and snapshots |
| Out | The host | Your model and speech addresses | Answers and speech |
| Out | The host | Your update source, if checking is on | The weekly version check |

Nothing else needs to reach the internet. See [What stays private](privacy.md) for the full list.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
