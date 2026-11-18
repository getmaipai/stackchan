# The utilization panel

The side panel has a **Utilization** section. It shows what the virtual robot is using: battery, power, the servo supply, memory and how hard the playground itself is working. Read the notes on each row before you trust a number.

## What each row means

| Row | What it tells you | Real or assumed |
|---|---|---|
| Battery | Percent left, and about how many hours at the current draw | The percent is the model's; the hours are assumed from the draw |
| Power from | The battery, the side USB socket, the back USB socket, or both | The rules are the real ones; the figures behind them are assumed |
| Draw | The current the robot takes now, in mA | Assumed until a bench measures it |
| Servo supply | The volts at rest and under load with both servos moving | Assumed (the panel says so) |
| Unit CPU | How busy the robot's processor is, in percent | A model |
| State updates | How many updates a second the page receives | Real, for this page |
| One picture drawn in | How long the robot's screen code takes to draw one frame, in ms | Real, measured on your computer, not on the robot |
| Memory | The bytes each loaded screen, picture or language pack costs, and a warning when the budget is broken | Costs come from the maker's table; a row marked "to measure" is a placeholder |
| Installed | What is installed in each slot (faces, languages, sounds, packs) | The same rules as the real robot |

## Speed up time

**Clock speed** runs the robot's clock faster than real time (up to 20 times). Use it to watch a battery drain or a long timer finish. The robot's own timing rules stay correct at any speed.

## When memory goes red

If a screen or feature would break the memory budget, the panel shows "over budget" and the reason. The same limit applies on the real robot, so the message tells you what to free: close a screen, or turn off an optional feature.

## What is not here yet

A model of how long the battery lasts for a whole day of use is planned. Until the bench measures the real robot, treat every number marked assumed as a guess that is right in order of size, not in the last digit.

Back: [index](index.md).
