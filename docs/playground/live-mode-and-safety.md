# Live mode and safety

Planned. Today the playground only runs the simulation. This page says how Live mode will work and what keeps it safe, so you know the rules before it exists.

## Simulation and Live

- **Simulation** is a virtual robot on your computer. Nothing you do can reach a real one.
- **Live** connects the same window to one of your own registered robots, through your own host (the computer or hub at home). The window shows a clear **LIVE** banner the whole time.

You pick Simulation or Live at the top. You can have many robots registered, but the playground connects to one at a time, and a robot accepts one playground at a time. If another session already holds the robot, you are told who, in plain words, and nothing is changed.

## What keeps it safe

- **A separate key.** Live uses a token made on your host's settings page, shown in a list, and revocable. It can move, show and play. It cannot lock or unlock the robot, update it, pair it, change settings or Wi-Fi, or install packages.
- **The robot's own rules still apply.** Mute, privacy, the head limits and the lock all work as they always do. A playground command cannot get around them.
- **The robot tells you.** While a playground is connected, the robot shows its remote-control sign, and the host logs who connected, when and why it ended.
- **It lets go on its own.** The connection must renew every 15 seconds. If the window closes or the network drops, the robot is free again within seconds.
- **Everything stays at home.** Live talks to your host over your own network. Nothing goes to a cloud service.

## Before you use it

Plug nothing unusual into the robot, keep a hand near the power, and watch the head: the limits protect the neck, but they do not replace looking. If a robot behaves oddly, press its own button or unplug it. That always wins over the playground.

## What is not built yet

The host's routes are designed (they are in the plan) and the lease and the token are tested, but the playground window does not show the picker yet.

Back: [index](index.md).
