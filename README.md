# MaiPai for StackChan

![The robot talking, dancing, showing rain and opening its games page.](docs/images/hero-robot.gif)

*The robot's screen as drawn by the virtual robot's own screen renderer: it talks, dances, shows rain and opens its games page, with no cloud involved. This is not a recording of a real unit.*

Custom firmware for the [StackChan](https://github.com/m5stack/StackChan) desk robot, plus a small host program. Private and local: your robot talks to a model you choose, and nothing leaves your home unless you point it there.

- **Works on its own.** Faces, touch, timers, alarms, games and dances run on the robot with no host and no cloud.
- **Your brain, your choice.** Use your own model, a small one the host installs for you, or MaiPai Home.
- **Safe by design.** A lock, mute and camera-off switches, and cues that cannot be hidden when the robot listens or watches.
- **Take it anywhere.** On any Wi-Fi (hotel, office, a friend's home) the robot joins your own private Tailscale network by itself and reaches your host; at home it never starts. See [use it away from home](docs/user/use-it-anywhere.md).
- **Six languages**, switched at run time, no reflash.

Try it with no hardware in the virtual playground:

![The virtual robot playground.](docs/images/hero-playground.gif)

*The virtual robot playground: a 3D model, the robot's screen and a tool panel, so you can try everything before you own a robot.*

## Install and use

1. Flash a robot with the [web flasher](docs/user/web-flasher.md) (not published yet; [build from source](docs/dev/build-from-source.md) works today).
2. [Install the host](docs/user/install-the-host.md).
3. Follow [Getting started](docs/user/getting-started.md).

Optional: try the [virtual robot](docs/user/try-the-virtual-robot.md) or the [playground](docs/playground/index.md) first, no hardware needed.

Docs: [For users](docs/user/index.md) · [Playground](docs/playground/index.md) · [For developers](docs/dev/index.md)

## Security

Each release is scanned for leaked secrets, vulnerable dependencies and unexpected network calls, and the host is checked to contact nothing beyond your own computer by default. Results and dates are in [SECURITY.md](SECURITY.md); the gaps are listed there too. Check it yourself: point your own AI at this repo with the prompt in [VERIFY.md](VERIFY.md).

## AI disclosure

This project is built with AI coding assistants (Claude and Codex), directed and reviewed by the owner. All code goes through the repository's checks (`bash scripts/check.sh`) and hardware tests. What is proven only on a computer and what is proven on a real robot is listed on [the readiness page](docs/plan/release-readiness.md). Status: pre-1.0.

## Independence

MaiPai for StackChan is an independent project providing custom firmware and tools for the M5Stack StackChan robot. It is not affiliated with, endorsed by, or sponsored by M5Stack or the original StackChan creators. Product names and trademarks belong to their respective owners.

## Help, contributing, license

Run `stackchan check` and read [Troubleshooting](docs/user/troubleshooting.md); report bugs on the Issues tab. To change code, read [contributing](docs/dev/contributing.md). AGPL-3.0: see `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.
