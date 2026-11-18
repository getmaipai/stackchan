# Install, update and remove the host

The host is the program that runs on your computer, between the robot and your model. It runs on a Mac, a Linux machine or a Raspberry Pi 5.

## Install

1. Install `pipx` if you do not have it. Your system's package manager has it.
2. Run `pipx install "git+https://github.com/getmaipai/stackchan#subdirectory=host"`.
3. You'll know it worked when `stackchan --help` lists its commands.
4. Run `stackchan run` to start the host. It stays in the terminal and prints what it does. The first run writes `~/.config/maipai/robot.toml` for you to edit.

![The robot's screen while it waits to be approved: crossed-out signal bars and a key, and the words "Waiting for Home to approve me".](../images/vu-pairing.png)

*The robot's screen while it waits to be approved: crossed-out signal bars and a key, and the words "Waiting for Home to approve me".*

No Docker is needed.

## Start it when the computer starts

Run `stackchan service install`. The host then starts at login and restarts itself if it stops. `stackchan service status` shows whether it runs. More: [Keep the host running](run-as-a-service.md).

## Update

Run `pipx upgrade maipai-bot`, then restart the host. The robot's firmware updates separately: see [Update the robot](updates.md).
If the host and the robot disagree about versions, the robot says so and names the side to update first.

## Remove

1. Run `stackchan service uninstall` to stop the host and remove its start-at-login entry.
2. Run `pipx uninstall maipai-bot`.
3. Delete the pairing file `~/.local/share/maipai-bot/stackchan-pairing.json` to unpair the robot, and delete the host's folder of settings and snapshots if you want them gone.

You'll know it worked when `stackchan --help` no longer runs. To put the factory firmware back on the robot, see [Switch from the factory firmware, or go back](switch-from-the-factory-firmware.md).

## Firewall

The robot connects to the host, so the host must accept that connection. The host listens on the voice port set by `MAIPAI_XIAOZHI_PORT` (the default is in the host log at start).
If you run a firewall, allow only what the host needs:

| Direction | Who | To | Why |
|---|---|---|---|
| In | The robot | The host, on the port it prints | Voice, events and snapshots |
| Out | The host | Your model and speech addresses | Answers and speech |

Nothing else needs to reach the internet. See [What stays private](privacy.md) for the full list.

## Still need help?

Run `stackchan status`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
