# Jokes and games content (optional package)

Off by default. When you turn it on, your own model writes jokes, riddles, trivia and short stories, the host keeps the good ones, and the robot keeps a small shelf of them to tell. Nothing goes to the internet except the model address you already set.

## Turn it on

In `robot.toml` set `enabled = true` under `[packages.pantry]` and restart the host. The first time, the host adds a built-in set of jokes, riddles and trivia questions (100 of each in English, 40 of each in Spanish, French, German, Portuguese and Italian) for the languages you chose. It needs no model, and the card shows **Built-in set**. A record you delete does not come back. To get more, choose a brain on the [Brain page](choose-a-brain.md) so your model can write new ones. Everything is for kids unless you set `adult_humor = true`.

## What it keeps

The host asks your model for batches of twenty and keeps only what passes its checks:

- **Shape.** The right fields, short enough to fit the robot's screen, in the right language.
- **Kids.** A word list, then a second question to the model: is this fine for a six year old. Anything that is not a clear yes is dropped, never edited.
- **Facts.** For trivia, the model must answer the question the same way. Questions about "the latest" or "current" things are dropped.
- **Riddles.** A riddle with a second good answer is dropped.
- **Copies.** The same line twice, or the same idea in other words, is kept once.

The checks above apply to what the host stores to tell later. They are not a filter on your chats: what your model says in a conversation is between you and your model.

## When it refills

During your quiet hours if you set them, otherwise between 2:00 and 5:00 at night, and at once when a shelf runs low. It never refills while the robot is busy.

## See and change what it keeps

Open the settings page, **Games and fun**, and find **Jokes and games content**. Each row has **Delete** (it may come back later) and **Never again** (it never comes back, and the robot skips it at once). **Refill now** asks your model for more of the kind and language you picked. The card shows how many model calls were used today against your daily cap.

## Games without a model

Say "play jokes", "tell me a riddle" or "let's play trivia". If your model stops answering in the middle of one of these games, the robot keeps playing from the library: it asks the next riddle or trivia question, checks your answer, keeps the score and never tells the same one twice. When the library runs out it says so and the game ends. Twenty questions also keeps playing from a built-in list of animals and things. Word chain, would you rather and bedtime stories need a model, so they stop with the usual "I cannot think right now" line.

## Offline lines

Pick the kind **line** on the same card to see the short lines the robot says by itself when it has no host, with the count for each situation (a greeting in the morning, a touch on the head, a low battery, and so on). Each line has **Delete** and **Never again**, like any other record. The model does not write lines; they come with the built-in set.

## Limits

The robot has its own shelf and telling screens. The host sends the shelf to the robot, and the robot reports which records it has told. The host keeps the full library. Delete the `pantry` folder beside the pairing file to remove it.
