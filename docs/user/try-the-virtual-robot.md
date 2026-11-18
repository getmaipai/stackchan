# Try the virtual robot

You can use a StackChan on your Mac, with no robot. It shows the same screens the real robot draws. This page is for people building or testing StackChan; the real robot does not need it.

## Open it

1. Start it. In the repository folder, run this command in a terminal:

```bash
python3 scripts/virtual-unit/view.py 8780
```

2. Open this address in your browser: http://127.0.0.1:8780/

The address only works on your own Mac. Nothing leaves it.

## What you can do

- Click the screen to tap it. Drag across it to swipe. Swipe up from the bottom edge to open the control sheet, swipe left for the next page, swipe right to come back to the face. The Gestures buttons do the same for you.
- Pick a face button to change the face.
- Use the side panel to call any of the robot's tools by name and see what comes back.
- Press Record, use the robot, press Stop, name it and press Save. The file lands in `scripts/virtual-unit/recordings/`. Pick `rec:NAME` in the scenario list to replay it with the same waits.
- Pick a scenario and press Play to watch a screen or a story run in real time.

## If it does not start

- The screens come from a program you build once: see `docs/dev/virtual-unit.md`. Without it the view shows only the face and says so.
- The 3D head needs an internet connection to load its drawing library. The flat screen still works without one.
