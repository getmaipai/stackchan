# Memory notes (optional package)

Off by default. When you turn it on, the robot keeps short notes for each adult you list, as plain text files on the host computer. Nothing goes to the internet.

![What the robot says, and the notes file it keeps.](../images/shot-memory-notes.png)

## Turn it on
In `robot.toml` add the block under `[packages.memory_notes]`: `enabled = true`, the names of the adults in `people`, and `default_person`. Restart the host.

## What you say
- "Remember that I like oat milk." Stores the note for the person speaking.
- "Remember for everyone that the guest Wi-Fi is called cabin." Every listed adult hears it.
- "What do you remember?" Reads back the last five notes.
- "Forget oat milk." Removes the notes that contain those words. "Forget everything about me." Removes all of that person's notes.

## What it will not keep
Passwords, codes and keys (including short forms like pw, cloud key ids and signed tokens), card and account numbers, government and passport id numbers, and anything over 300 characters. It says why, and nothing is stored.

## Who can read what
A person's private notes go only into that person's own turns. The robot does not recognize voices on its own, so it opens private notes in this order:
1. The person a recognizer named, when MaiPai Home or another source supplies one.
2. The person who said their **notes passphrase**: "This is Sam, my passphrase is blue river lamp." It holds for 30 minutes. Five wrong tries lock it for 10 minutes.
3. When nobody is identified, the `default_person` you named in `robot.toml`. That is your choice as the owner: anyone in the room who talks to the robot gets that person's notes, so name one only in a home where that is fine.

Saying "this is Sam" with no passphrase is only a claim. It lets the robot use the **household** notes ("Remember for everyone that...") and nothing private. A child who says "this is Sam" cannot hear Sam's notes.

Set your passphrase while the robot knows it is you: "Set my notes passphrase to blue river lamp." Use two or more words, at least eight letters. The robot keeps only a scrambled copy, never the words. "Who is speaking?" tells you whose notes it is using. A child or teen is never a notes person; a child's robot needs MaiPai Home.

## Where the files are
One file per person in the `notes` folder beside the pairing file (`~/.local/share/maipai-bot/notes/alex.md`). One note per line. You can read, edit or delete them by hand.
