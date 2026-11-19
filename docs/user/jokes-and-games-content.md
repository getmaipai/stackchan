# Jokes and games content (optional package)

Off by default. When you turn it on, your own model writes jokes, riddles, trivia and short stories, the host keeps the good ones, and the robot keeps a small shelf of them to tell. Nothing goes to the internet except the model address you already set.

## Turn it on

In `robot.toml` set `enabled = true` under `[packages.pantry]` and restart the host. You need a model: choose a brain on the [Brain page](choose-a-brain.md) first. Everything is for kids unless you set `adult_humor = true`.

## What it keeps

The host asks your model for batches of twenty and keeps only what passes its checks:

- **Shape.** The right fields, short enough to fit the robot's screen, in the right language.
- **Kids.** A word list, then a second question to the model: is this fine for a six year old. Anything that is not a clear yes is dropped, never edited.
- **Facts.** For trivia, the model must answer the question the same way. Questions about "the latest" or "current" things are dropped.
- **Riddles.** A riddle with a second good answer is dropped.
- **Copies.** The same line twice, or the same idea in other words, is kept once.

## See and change what it keeps

Open the settings page, **Games and fun**, and find **Jokes and games content**. Each row has **Delete** (it may come back later) and **Never again** (it never comes back, and the robot skips it at once). **Refill now** asks your model for more of the kind and language you picked. The card shows how many model calls were used today against your daily cap.

## Limits

The robot's own shelf and the telling screens need a firmware update that is not built yet, so today the host keeps the library and the page works, and the robot does not tell from it. Records stay on your computer. Delete the `pantry` folder beside the pairing file to remove all of it.
