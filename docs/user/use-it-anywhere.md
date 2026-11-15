# Use it anywhere with Tailscale

The robot can join your Tailscale network. Then it reaches your host, or your MaiPai Home hub, from any Wi-Fi: your living room, a friend's house, a hotel.
The link is encrypted end to end by Tailscale, and nothing is opened on your router.

## Why use it

- **Bring the robot anywhere.** Plug it in on any Wi-Fi with internet. It finds your host through your tailnet, so you carry no travel router and no phone app.
- **An encrypted link.** On your home network the link between the robot and the host is plain. Over Tailscale it is encrypted.
- **Still private.** Tailscale connects your own devices to each other. Your voice, snapshots and models stay on your machines.

## Set it up

1. Install Tailscale on the computer that runs the host, and sign in.
2. In the Tailscale admin page, create a reusable auth key for the robot.
3. Open the web settings page, choose **Network**, and paste the key. The robot joins your tailnet and shows its address.

   ![The Network settings page with the Tailscale key field and a connected status.](../images/tailscale-settings.svg)

4. Run `stackchan check`. It tests the route from the robot to the host over Tailscale and says what is wrong if it fails.

The robot tries your home Wi-Fi first. Set `prefer_tailnet` to a number of minutes if you want it to try Tailscale first for that long.

## Saved Wi-Fi networks

The robot remembers several networks, such as home, a friend's house and a hotspot. At a new place it picks the strongest saved network.
Add one from the robot's setup page or the web settings page. Remove any time. Passwords stay on the robot.

![The saved Wi-Fi list with three networks and one marked connected.](../images/saved-wifi.svg)

## When something fails

| What you see | What went wrong | What to do |
|---|---|---|
| The status says "tailnet: offline" | The robot has no internet on this Wi-Fi, or the key expired. | Check the Wi-Fi, then paste a new key on the Network page. |
| The robot joins but cannot find the host | The host computer is asleep or signed out of Tailscale. | Wake the host and sign in to Tailscale. |
| Replies are slower away from home | The link goes through a relay, not straight to your host. | Wait a minute for a direct route. It usually improves on its own. |

## Using MaiPai Home

The same setup reaches a MaiPai Home hub on your tailnet. See [With MaiPai Home](with-maipai-home.md).
