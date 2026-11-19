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

## Use a hosted brain (optional)

<span class="planned-tag">Planned</span> Not built. It waits for a test build of the cloud brain to prove it, and it will be off until you turn it on.

A hosted brain runs on a computer that is not in your home. Using one means your words **leave your home**. The page will say so in plain words before you can save it, and nothing is sent until you do. Three routes are planned:

- **Your own key.** You sign in to a model service you already pay for and paste your own key. The host sends each turn there, and that service's rules apply.
- **A community server address.** Someone you trust runs a server and gives you its address. You type it in. Ask them what they keep.
- **The official cloud.** A cloud brain run for MaiPai for StackChan, with a stated policy.

All three leave your home, so none is a default and none is chosen for you. The three ways above stay the way to keep everything at home.

## Everything stays yours

The host calls only the addresses you set. In way 3 the only network traffic is the one-time download, and the page lists the two sites before you press Install. After that nothing leaves your computer.
