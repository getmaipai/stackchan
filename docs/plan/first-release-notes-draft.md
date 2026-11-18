# First release notes draft (2026-11-18)

Status: draft for the owner, written for the person who installs the robot. Plain words, grade 6. It says what you get, what you need and what to do first. The features named are the ones the readiness page and the feature list show as built; it names no internal ids and does not go into what is still being proven (the Status section of the README does that). It assumes the release key and the web flasher exist when it is published.

---

# MaiPai for StackChan 1.0

Your StackChan can now talk with an AI that runs on your own computer, and nothing you say leaves your home.

## What you get

- **A robot that answers.** Say the wake word, ask a question, and the reply starts as soon as the first sentence is ready.
- **Timers and alarms by voice.** Say "set a timer for five minutes." It works even when your model is not running.
- **Faces and a clock.** Pick a face, or use your own pictures. The robot shows the time, and the face changes with the hour.
- **Three privacy switches.** Mute the microphone, turn the camera off, or go fully quiet. Each is three taps on the face, and the screen shows which one is on.
- **A passcode.** Lock the robot so only you can use it.
- **Games and dances.** Play on the screen, and watch it dance to music.
- **Your language.** English, Spanish, French, German, Portuguese and Italian.
- **A page for parents.** One screen that says, in plain words, what the robot is doing.
- **Updates you choose.** New versions are signed. You install them when you want, and the robot goes back to the old version by itself if a new one does not start.

## What you need

- A StackChan robot and a USB cable.
- A Mac, a Linux computer or a Raspberry Pi 5 that stays on. It runs the host program.
- A language model on a computer you control, or MaiPai Home.
- Wi-Fi that the robot and the computer share.

## Do this first

1. Read how to go back to the factory firmware. You can always do it. It is on the page called "Switch from the factory firmware, or go back".
2. Install the host program with the one command in the README.
3. Open the web flasher, plug in the robot and press Install.
4. Run `stackchan run`, then `stackchan pair`, and type the six digits on the robot.
5. Say the wake word and ask something.

About 20 minutes the first time. You do this once.

## With MaiPai Home

If you run MaiPai Home, the robot can use its memory, know who is talking and follow your household rules, including protections for children and teens. Turn it on in the settings file: set `brain = "home"` and run `stackchan check`.

## Good to know

- With your own model, the robot says what your model says. We add no content filter, so you decide what model to use.
- Some screens are pictures from a computer that draws the robot's screen with the robot's own code. Your robot looks the same.
- This is the first release. If something does not work the way these notes say, open an issue and tell us what you saw. We read every one.

## Getting help

Run `stackchan check`, then read the troubleshooting page. If that does not fix it, open an issue on the Issues tab.
