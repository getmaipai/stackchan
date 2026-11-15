# Camera

The camera is off until you turn it on. Frames stay on the host and never go to an outside service.
The robot's camera has a low resolution, so these pages call the pictures **snapshots**.

## Turn it on

Set `camera = true` in `robot.toml`, or switch it on in the web page. Choose how long the host keeps snapshots with `camera_retention`.
A camera-on cue shows whenever the camera streams. You cannot turn that cue off.

> **Screenshot placeholder:** `camera-cue.png`. The robot screen with the camera-on icon.

## What is this

Hold something up and say "what is this". The host sends one snapshot to the vision model address you set in `vision_url`.
If you set no vision model, the feature hides.

## Take my picture

Say "take my picture". The robot counts down, plays a shutter tone and saves the snapshot to a folder on the host.

> **Screenshot placeholder:** `countdown.png`. The countdown screen showing 2.

## Face follow, wave and mirror

- **Face follow.** The head turns to keep you in view. It uses a small detector that runs on the host.
- **Wave.** Wave at the robot and it waves back.
- **Mirror.** Say "mirror me". The robot copies your head tilt.

## Names and alerts

Add people to a local name list from the web page. The robot can then say who it sees, and the host can send an alert such as
"Atlas is at the door". The list lives in a file on the host.

> **Screenshot placeholder:** `name-list.png`. The name list page with two entries.

## Keep and delete

Snapshots are deleted after `camera_retention`. Press Delete all in the web page, or run `stackchan camera delete`, to clear them now.
