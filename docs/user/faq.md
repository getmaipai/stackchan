# Questions people ask

## Does it work without the internet?

Yes, once it is set up and your model runs on your own network. Voice, timers, faces, games and the camera do not need the internet.
Update checks, Tailscale and anything you point at an outside address do.

## Do I need MaiPai Home?

No. The robot is complete without it. MaiPai Home adds memory across days, people, calendars, announcements, naming songs, and "what is this". See [Compare](compare.md).

## Does it record me?

The robot stores no recordings. While you talk, your voice goes to your own host and your own speech tool, and the light bars glow green. What your own speech tool and model keep is up to them, so check their settings.

## Is the camera always watching?

No. The camera is off until you turn it on, and the screen shows a cue whenever it streams. Tap an eye to turn it off at any time. See [Mute, camera off and full quiet](mute-and-camera-off.md).

## Can I use a model in the cloud?

You can point `llm_url` at any OpenAI-compatible address, including one in the cloud. If you do, your words go to that service, so the privacy promise no longer holds for the words you speak. We recommend a model you run yourself.

## Can I use it with the factory phone app?

No. MaiPai for StackChan replaces the factory firmware, so the factory app does not control it. You can [switch back](switch-from-the-factory-firmware.md) at any time.

## What languages does it speak?

English and Spanish, switched at run time. Your model and speech tools must handle the language. See [Switch the language](languages.md).

## Is it safe for children?

In standalone mode we add no content filter. The model you connect decides what the robot says, so pick a model and persona that suit your home. With MaiPai Home, its household rules apply.

## How do I wipe it?

Run `stackchan forget` on your host, then reset the robot from its settings. See [Keep the robot secure](security.md).

## Does it cost anything?

The software is free and open source (AGPL-3.0). You pay for the robot and for the computer that runs your model. See [Pick hardware and a model](hardware-and-models.md).

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
