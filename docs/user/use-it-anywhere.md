# Use the robot away from home

The robot can reach your host or hub from any Wi-Fi, such as a friend's house, a hotel or the office. It joins your private network (Tailscale) by itself when it cannot reach your host. At home it never starts.

## How it works

- The robot tries your host first. If it fails 3 times in a row, it joins your private network and tries again over that route.
- You give it a one-time key on the Wi-Fi setup page. The key is never stored in a firmware image.
- Your own devices talk to each other over the private network. Your conversations stay on your machines.

## Status: built, not yet proven on a unit

The code is in the release images and the host tests pass. No robot has joined a real private network with a real key yet, so treat this page as the plan. The first real run is on the maintainers' list.

## Set it up

1. Install Tailscale on the computer that runs the host, and sign in on that computer.
2. In the Tailscale admin page, create a one-time auth key for the robot. Mark it as ephemeral and give it the tag `tag:robot`.
3. Find the host computer's Tailscale address. It looks like `100.x.x.x` and is shown in the Tailscale app and the admin page next to that computer.
4. In the settings page, open **Home**, then **Away from home**. Type the host's `100.x.x.x` address under **Home address** and save it.
5. Give the robot the key. The settings page sends the key only when the link to the robot is encrypted. If it is not, the page says so and does not send it. Then type the key on the robot's own Wi-Fi setup page (see [Getting started](getting-started.md)), in the key field, with your Wi-Fi and the setup code.
6. Take the robot to another Wi-Fi. After 3 failed tries to reach your host, it joins your private network and the screen shows its link state. The key is erased from the robot after it joins.

An access rule keeps the robot's reach small. In your Tailscale policy, let `tag:robot` reach only the host's robot port, and nothing else. The host cannot read your policy, so check it in the admin page.

## What it contacts

Only when it joins, the robot contacts a public coordination service over an encrypted connection, so your devices can find each other. It sends no voice, snapshots or settings there. At home it contacts nothing outside your network.

## If it does not connect

Check that the host is on and signed in to Tailscale, and that the one-time key was not used before or expired. Make a new key and enter it on the setup page. Then run `stackchan check`.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
