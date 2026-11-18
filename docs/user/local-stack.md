# Install the small stack

Use this to try the robot with nothing else to set up. The host downloads a small language model, a speech-to-text model and a text-to-speech voice, and runs them on this computer.

## Before you press Install

The page shows, before it starts:

- How much it downloads, how much disk it needs, how much memory it needs, and how much is free.
- The two sites it downloads from. Nothing else is contacted.
- Which model size it suggests. The small model starts answering sooner. The better model gives better answers and needs 8 GB of memory or more.

Models used: Qwen2.5 (Apache-2.0), Moonshine (MIT) and the Piper voice (MIT). The language model runs in llama.cpp (MIT). Each file is checked against a fixed checksum, and a file that does not match is thrown away.

## Install

1. Open the settings page on the host at `/brain`.
2. In the third card, pick the size and press **Install**.
3. Watch the progress bar. It names the file it is on. You can press **Stop** at any time. The partly downloaded files are removed.
4. When it finishes, the page says how long this computer took to answer in a test, measured here. If that is slow, it says so and suggests the small model or another way.

## Remove it

Press **Remove it**. The downloaded files and the settings lines go. Your other settings stay.

## If it fails

The page says which file failed and why, in plain words. Check your connection and press **Install** again. A checksum failure means the download was damaged: it is thrown away, and nothing is half installed.

It works on a Mac and on Linux, including a Raspberry Pi 5. A Raspberry Pi is slower: expect a few seconds before the robot answers.
