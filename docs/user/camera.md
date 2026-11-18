# Use the camera

> **This is a convenience, not a safety device.** Do not rely on it to watch a baby or a person who needs care. Use a purpose-made monitor for that.

<span class="planned-tag">Planned</span> Taking a photo from the settings page is built and flashed, and it works without MaiPai Home. It is off until you turn it on, shows its cue every time, and the picture stays on your own host. Snapshots by voice, live view and the rest of this page are planned for your own host too. Naming people, recognizing faces and "what is this" need <span class="home-tag">Needs MaiPai Home</span>. Not yet checked on a robot.


The camera is off until you turn it on. Frames go to your own host or to your MaiPai Home hub and never to an outside service.
The robot's camera has a low resolution, so these pages call the pictures **snapshots**.

## Turn it on

Switch the camera on in MaiPai Home, and choose how long Home keeps snapshots. A photo taken from the Remote section of your own settings page needs no Home.
A camera-on cue shows whenever the camera streams. You cannot turn that cue off.

When it takes a picture, the light bars flash pink twice and stay pink <img src="../images/light-pink.svg" alt="pink light bars" height="22">, and you hear a double click <img src="../images/tone-shutter.svg" alt="double click" height="18">. The pink never dims, even at night. [All lights and sounds](lights-and-sounds.md).

![The robot screen with the camera-on icon.](../images/camera-cue.svg)

*The robot screen with the camera-on icon. A placeholder drawing, not a real screenshot.*

## You can always tell

The robot always shows when it is listening, looking or taking a picture, and no setting can hide it.

| The robot is | The light bars | The screen | A sound |
|---|---|---|---|
| Listening to you | Green, steady | A microphone icon | A short rising pop when it starts |
| Taking a picture | Pink, two flashes then steady | A camera icon | A double click |
| Showing live view | Pink, steady, the whole time | A camera icon with a LIVE dot | A double click when it starts |

If the camera is off or the robot is muted, none of these show, and none of the things they describe are happening.

## Live view



Open the web app and watch what the robot sees, live, at low resolution. The camera is small, so the picture is a smooth low-resolution view, not high definition.
Live view only runs while the web page is open. The robot sends 5 pictures a second and stops by itself after 10 minutes. When it starts, the robot plays a double click and the pink lights and the LIVE dot appear, and they stay on until it stops.
You cannot turn those cues off, and live view never starts by itself. Frames go to your MaiPai Home hub, not to an outside service.

## What is this

<span class="home-tag">Needs MaiPai Home</span>

Hold something up and say "what is this". The robot sends one snapshot to your MaiPai Home hub, which describes it out loud.
Without MaiPai Home, this feature is hidden. See [Use MaiPai Home as the brain](with-maipai-home.md).

## What do you see

<span class="planned-tag">Planned</span> This is a design only.

Ask "what do you see" and the robot lists the people and objects in view, such as "a table and a person", straight away, while a fuller look runs in the background.

## Take my picture

<span class="planned-tag">Planned</span> Say "take my picture". The robot counts down, plays a shutter tone and saves the snapshot. Today you take a photo with the **Take a photo** button under Remote controls on the settings page. The picture shows on that page and the host does not keep it.

![The countdown screen showing 2.](../images/countdown.svg)

*The countdown screen showing 2. A placeholder drawing, not a real screenshot.*

## Face follow, wave and mirror

- **Turn toward faces.** Set it on the settings page to off, only after it is spoken to, or always (the default). In always, the robot looks at one camera frame a second, with the camera cue on, and turns at most four times a minute. It never turns when it is carried, locked or at night. A face detector on the robot is an experiment and is not flashed.
- **Wave.** Wave at the robot and it waves back.
- **Mirror.** Say "mirror me". The robot copies your head tilt.

## Names and alerts

Add people to a name list in MaiPai Home. The robot can then say who it sees, and Home can send an alert such as
"Atlas is at the door". The list lives in MaiPai Home.

![The name list page with two entries.](../images/name-list.svg)

*The name list page with two entries. A placeholder drawing, not a real screenshot.*

## Keep and delete

With your own model, the host keeps no photos. With MaiPai Home, Home keeps snapshots for the time you set there, and you can delete them all in Home.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
