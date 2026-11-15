# Use the camera

The camera is off until you turn it on. Frames stay on the host and never go to an outside service.
The robot's camera has a low resolution, so these pages call the pictures **snapshots**.

## Turn it on

Set `camera = true` in `robot.toml`, or switch it on in the web page. Choose how long the host keeps snapshots with `camera_retention`.
A camera-on cue shows whenever the camera streams. You cannot turn that cue off.

When it takes a picture, the light bars flash pink twice and stay pink <img src="../images/light-pink.svg" alt="pink light bars" height="22">, and you hear a double click <img src="../images/tone-shutter.svg" alt="double click" height="18">. The pink never dims, even at night. [All lights and sounds](lights-and-sounds.md).

![The robot screen with the camera-on icon.](../images/camera-cue.svg)

## You can always tell

The robot always shows when it is listening, looking or taking a picture, and no setting can hide it.

| The robot is | The light bars | The screen | A sound |
|---|---|---|---|
| Listening to you | Green, steady | A microphone icon | A short rising pop when it starts |
| Taking a picture | Pink, two flashes then steady | A camera icon | A double click |
| Showing live view <span class="planned-tag">Planned</span> | Pink, steady, the whole time | A camera icon with a LIVE dot | A double click when it starts |

If the camera is off or the robot is muted, none of these show, and none of the things they describe are happening.

## Live view

<span class="planned-tag">Planned</span>

Open the web app and watch what the robot sees, live, at low resolution. The camera is small, so the picture is a smooth low-resolution view, not high definition.
Live view only runs while the web page is open. When it starts, the robot plays a double click and the pink lights and the LIVE dot appear, and they stay on until it stops.
You cannot turn those cues off, and live view never starts by itself. Frames go to your host, not to an outside service.

## What is this

<span class="home-tag">Needs MaiPai Home</span>

Hold something up and say "what is this". The robot sends one snapshot to your MaiPai Home hub, which describes it out loud.
Without MaiPai Home, this feature is hidden. See [Use MaiPai Home as the brain](with-maipai-home.md).

## What do you see

<span class="planned-tag">Planned</span>

Ask "what do you see" and the robot lists the people and objects in view, such as "a table and a person", straight away, while a fuller look runs in the background.

## Take my picture

Say "take my picture". The robot counts down, plays a shutter tone and saves the snapshot to a folder on the host.

![The countdown screen showing 2.](../images/countdown.svg)

## Face follow, wave and mirror

- **Face follow.** The head turns to keep you in view. It uses a small detector that runs on the host.
- **Wave.** Wave at the robot and it waves back.
- **Mirror.** Say "mirror me". The robot copies your head tilt.

## Names and alerts

Add people to a local name list from the web page. The robot can then say who it sees, and the host can send an alert such as
"Atlas is at the door". The list lives in a file on the host.

![The name list page with two entries.](../images/name-list.svg)

## Keep and delete

Snapshots are deleted after `camera_retention`. Press Delete all in the web page, or run `stackchan camera delete`, to clear them now.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
