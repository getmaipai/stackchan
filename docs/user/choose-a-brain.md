# Choose a brain

The robot needs a brain to think and talk. The first time you start the host, no brain is set. Open the settings page on the host computer at `http://127.0.0.1:8777/brain` (the host writes the exact address in its log), and pick one of three ways. You can change it later on the same page. You do not need a terminal.

| | What it is | You need |
|---|---|---|
| **1. MaiPai Home** | A Home hub is the brain | A Home hub on your network |
| **2. Your own stack** | Your own language model, speech-to-text and text-to-speech servers | Three addresses |
| **3. A small stack on this computer** | The host downloads small models and runs them here | About 2 GB of disk and 2 GB of free memory, and a network connection for the download |

Not sure? Pick 3 to try the robot today. Pick 1 or 2 when you want better answers or a faster robot.

## 1. MaiPai Home

Type Home's address and press **Use MaiPai Home**. Restart the host, then pair the robot with Home. See [Use MaiPai Home as the brain](with-maipai-home.md).

## 2. Your own stack

See [Use your own stack](use-your-own-stack.md). Each address has a **Test** button that says in plain words what is wrong.

## 3. A small stack on this computer

See [Install the small stack](local-stack.md).

## Two routes: hosted or custom

The Brain page offers two equal routes, the same choice the stock firmware gives. Hosted sends your voice to M5Stack/Xiaozhi's servers, outside your home. Custom keeps it where you point it. <span class="planned-tag">Planned</span> The hosted route is shown but cannot be saved yet: it waits for a test build to prove that their server accepts this firmware. If it does not, the route is hidden and this page says why. When you leave hosted, the page tells you that anything their servers already kept stays on their side, and only they can delete it.

- **A: Hosted by M5Stack/Xiaozhi.** Their servers answer. **Your voice leaves your home** for those servers, under their terms.
- **B: Custom.** Your own key, a community server address, your own host or MaiPai Home, or a model on your computer. Your voice stays where you point it. The three ways above are all part of this route.

Either way, if the brain cannot be reached the robot falls back to what it can do alone.

## Everything stays yours

The host calls only the addresses you set. In way 3 the only network traffic is the one-time download, and the page lists the two sites before you press Install. After that nothing leaves your computer.
