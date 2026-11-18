# Keep the robot secure

Privacy keeps your data in your home. Security keeps other people out. This page lists what stops someone from controlling or reaching your robot, and the one gap to know about.

## What protects the robot

- **Pairing needs you in the room.** `stackchan pair` prints a 6 digit code on the host and you type it on the robot's setup page. The code works once and expires after ten minutes, and five wrong tries from one address stop further tries for ten minutes.
- **Revocable access.** Pairing creates a long random token, stored hashed on the host. Run `stackchan forget` and that token stops working.
- **Tokens on everything that is on.** The local API, event stream and metrics are off by default. When you turn one on, every read and write needs a token.
- **Signed updates.** <span class="planned-tag">Planned</span> The signature check and the rollback are built, but no release key exists yet and no signed image has been installed on a robot. Until a release is signed, do not rely on this.
- **Remote control is off by default.** When you turn it on, every remote action needs your token and shows a Remote icon on the robot. There is no remote listening in remote control, and no mode that streams the robot's microphone to a phone.
- **The camera cue cannot be switched off.** When the camera streams, the screen always shows it.

![The web security page listing paired devices, with a Forget button next to each.](../images/security-settings.svg)

*The web security page listing paired devices, with a Forget button next to each. A placeholder drawing, not a real screenshot.*

## Who can open the settings page

The settings page listens only on the host computer (127.0.0.1) until you turn on `lan = true`. Then it listens on your network, and every device other than the host computer must show the settings token, which `stackchan settings-token` prints. A wrong token is refused, and ten wrong tries in a minute lock the login for everyone. The host refuses a page that reaches it through a proxy or under another name. The host will not start the page on your network without a token.

## No stealth

The robot never monitors in secret. Every listening, looking or watching mode shows on its screen. See [The robot never monitors in secret](no-stealth.md).

## Watch mode

The robot can watch a room for motion and loud sounds. It always shows when it is watching, and it never records or sends sound unless an alert fires. See [Watch your room and get alerts](watch-and-alerts.md).

## Known gaps

We audited the design and found these. Each is on the fix list before release.

- **The link on your home network is plain.** Anyone already on your Wi-Fi could read it, and the robot does not yet check that it is talking to your host. Use a network you trust. The host side of an encrypted link (TLS with a key from pairing) is built. The robot side is not flashed yet, so today the link is still plain.
- **The Wi-Fi setup page is a short window.** It needs the six-digit code on the robot's screen, locks after five wrong tries and gets a new code every few minutes. Use it when you are present.
- **Someone with the robot in hand can read its memory over USB.** Reset the robot before you give it away.

We have not yet captured the robot's network traffic to prove nothing else leaves your home. We will publish that capture before release.

## Reset the robot

A reset clears the robot's saved Wi-Fi networks, its pairing and its settings. Your host keeps its own files.

1. On the robot, open **Settings**, then **Reset**.
2. Read what will be cleared and press **Reset**.
3. Confirm by holding the button for three seconds. The robot asks twice on purpose, so a stray touch cannot wipe it.

You'll know it worked when the robot restarts and shows the setup page.

If you cancel, nothing changes. If the reset stops partway, the robot says so and starts the setup page anyway. Run the reset again.

## If you lose the robot or sell it

1. Run `stackchan forget` on the host. The robot can no longer reach it.
2. If you have the robot, [reset it](#reset-the-robot).

You'll know it worked when `stackchan check` no longer lists the robot.

## Found a security problem?

Please don't post it publicly. Tell us privately and we will fix it before anyone else sees it. We will add the contact to this page before release.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab, without any private details.
