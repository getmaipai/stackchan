# Use the robot away from home

The robot can reach your host or hub from any Wi-Fi, such as a friend's house, a hotel or the office. It joins your private network (Tailscale) by itself when it cannot reach your host. At home it never starts.

## How it works

- The robot tries your host first. If it fails 3 times in a row, it joins your private network and tries again over that route.
- You give it a one-time key on the Wi-Fi setup page. The key is never stored in a firmware image.
- Your own devices talk to each other over the private network. Your conversations stay on your machines.

Not yet checked on a robot: a real join with a real key, a spoken turn over the private route, and the camera and updates over it.

## Set it up

1. Install Tailscale on the computer that runs the host, and sign in.
2. In the Tailscale admin page, create a one-time auth key for the robot.
3. Open the robot's Wi-Fi setup page (see [Getting started](getting-started.md)) and type the key in the key field, with your Wi-Fi and the setup code.
4. Take the robot to another Wi-Fi. After 3 failed tries to reach your host, it joins your private network and the screen shows its link state.

![The setup page with the one-time key field.](../images/tailscale-settings.svg)

## What it contacts

Only when it joins, the robot contacts a public coordination service over an encrypted connection, so your devices can find each other. It sends no voice, snapshots or settings there. At home it contacts nothing outside your network.

## If it does not connect

Check that the host is on and signed in to Tailscale, and that the one-time key was not used before or expired. Make a new key and enter it on the setup page. Then run `stackchan check`.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
