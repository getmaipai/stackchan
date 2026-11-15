# Getting started with MaiPai for StackChan

About 20 minutes the first time. You do this once.

## What you need

- A StackChan robot and a USB cable. New to the robot? See the [official docs](https://docs.m5stack.com/en/StackChan), or [buy one from the store](https://shop.m5stack.com/products/stackchan-kawaii-co-created-open-source-ai-desktop-robot).
- A small always-on computer for the host program: a Mac, a Linux machine or a Raspberry Pi 5.
- Wi-Fi that the robot and the host share.
- A language model you run yourself, reached by a web address. Speech tools are optional, because the host has built-in ones.

## Steps

1. **Install the host.** Run `pipx install git+https://github.com/getmaipai/stackchan`. You'll know it worked when `stackchan --help` lists its commands.
2. **Flash the robot.** Open the web flasher, plug the robot in by USB and press Install. You can enter your Wi-Fi in the same dialog.

   ![The web flasher with the Install button and the Wi-Fi fields.](../images/flasher.svg)

3. **Pair.** Run `stackchan pair` on the host. A two minute window opens. The robot shows a 6 digit code. Type it on the host. You'll know it worked when the host says the robot is paired and the robot shows its face.

   ![The robot screen with the 6 digit code, and the host terminal asking for it.](../images/pairing-code.svg)

4. **Point at your model.** Open `robot.toml` and set `llm_url` to your model address, for example `http://192.0.2.10:8080`.
5. **Check.** Run `stackchan check`. It tests each address and says in plain words what is wrong. You'll know it worked when every line says ok.

   ![The terminal after `stackchan check`, every line marked ok.](../images/check-output.svg)

6. **Talk.** Say the wake word, then ask a question. The face shows dots while it thinks, then it answers. If nothing happens, see [Troubleshooting](troubleshooting.md).

   ![The robot face with thinking dots.](../images/first-turn.svg)

## If the robot cannot join Wi-Fi

It opens a setup page. Connect to its network, pick your Wi-Fi, enter the password and the host address.

![The setup page with a list of networks.](../images/wifi-setup.svg)

## Optional

- `stackchan install-service` starts the host when the computer starts. It is off until you run it.
- Take the robot anywhere: join your Tailscale network. See [Use it anywhere](use-it-anywhere.md).
- `stackchan forget` removes the pairing. Use it before you give the robot away.
- To use MaiPai Home as the brain, see [With MaiPai Home](with-maipai-home.md). You do not need it.

## Content safety

In standalone mode the robot adds no content filter. The model you connect decides what is said. Pick a model and persona that suit your home.

## Next

Take the tour in [Features](features.md), or change how the robot looks in [Settings](settings.md).

## Lights and sounds

| What you see | What you hear | When |
|---|---|---|
| ![Cyan light bars pulsing slowly](../images/light-cyan.svg)<br>Cyan light bars, a slow pulse every 2 seconds, and the setup screen | ![Two rising notes](../images/tone-needs-you.svg)<br>Two rising notes, then again each minute | The robot needs Wi-Fi. Connect to its network and enter your Wi-Fi details. This one tone plays even at night |
| ![Cyan light bars pulsing slowly](../images/light-cyan.svg)<br>Cyan light bars, a slow pulse every 2 seconds, and "Waiting to be paired" | ![Two rising notes](../images/tone-needs-you.svg)<br>Two rising notes, once | The robot is waiting for you to type the pairing code |
| Lights off, the face appears | ![A rising chime](../images/tone-back-online.svg)<br>A rising chime | The robot is paired and connected |

See [Lights and sounds](lights-and-sounds.md) for every light and tone.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
