# Keep the robot secure

Privacy keeps your data in your home. Security keeps other people out. This page lists what stops someone from controlling or reaching your robot, and the one gap to know about.

## What protects the robot

- **Pairing needs you in the room.** The robot shows a 6 digit code, and you type it on the host. The window closes after two minutes, and five wrong codes close it early.
- **Revocable access.** Pairing creates a long random token, stored hashed on the host. Run `stackchan forget` and that token stops working.
- **Tailscale encrypts the link.** Over your Tailscale network, traffic between the robot and your host is encrypted end to end. Only your own devices can join.
- **Tokens on everything that is on.** The local API, event stream and metrics are off by default. When you turn one on, every read and write needs a token.
- **Signed updates.** The robot installs only signed images. A bad signature is refused, and a failed update rolls back.
- **The camera cue cannot be switched off.** When the camera streams, the screen always shows it.
- **No open ports on your router.** You never forward a port. Over Tailscale, only your own devices can reach the robot and host.

![The web security page listing paired devices, with a Forget button next to each.](../images/security-settings.svg)

## The gap to know about

On your home network without Tailscale, the link between the robot and the host is plain, not encrypted. Anyone already on your Wi-Fi could read it.
Use a network you trust, or turn on [Tailscale](use-it-anywhere.md), which encrypts it.

## If you lose the robot or sell it

1. Run `stackchan forget` on the host. The robot can no longer reach it.
2. Reset the robot from its settings page to clear its saved Wi-Fi networks and Tailscale key.
3. In the Tailscale admin page, remove the robot and delete its auth key.

You'll know it worked when `stackchan check` no longer lists the robot.

## Found a security problem?

Please don't post it publicly. Tell us privately and we will fix it before anyone else sees it. We will add the contact to this page before release.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab, without any private details.
