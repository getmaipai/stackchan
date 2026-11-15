# Getting started

Status: planned. Today only a repo skeleton exists. This page says how setup will work.

## What you need

- A StackChan robot and a USB cable.
- A small always-on computer for the host program: a Mac, a Linux machine or a Raspberry Pi 5.
- Wi-Fi that the robot and the host share.
- A language model you run yourself, reached by a web address. Speech tools are optional, because the host has built-in ones.

## Steps

1. Install the host with `pipx install git+https://github.com/getmaipai/stackchan`.
2. Put the firmware on the robot with the web flasher over USB. You can enter your Wi-Fi in the same dialog.
3. Run `stackchan pair` on the host. A two minute window opens. The robot shows a 6 digit code. Type it on the host.
4. Open `robot.toml` and set `llm_url` to your model address, for example `http://192.0.2.10:8080`.
5. Run `stackchan check`. It tests each address and says in plain words what is wrong.
6. Say the wake word and talk.

If the robot cannot join Wi-Fi, it opens a setup page. Connect to its network, pick your Wi-Fi, enter the password and the host address.

## Optional

- `stackchan install-service` starts the host when the computer starts. It is off until you run it.
- To use MaiPai Home as the brain, set `brain = "home"` in `robot.toml` with the hub address. You do not need it.

## Content safety

In standalone mode the robot adds no content filter. The model you connect decides what is said. Pick a model and persona that suit your home.
