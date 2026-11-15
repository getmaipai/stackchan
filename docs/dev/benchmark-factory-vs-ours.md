# Benchmark: factory firmware against MaiPai for StackChan

Owner request, 2026-11-15. The README and the compare page say MaiPai for StackChan is faster and smoother than the factory firmware.
This plan produces the numbers that back that claim, or shows where it is wrong. Publish the results on the compare page with the hardware and model versions used.

## Why

The owner heard stuttering in the factory firmware's voice replies, consistently. That is one person's observation on one unit, so it stays out of the docs until it is measured.

## Setup

- One robot, one network, one room. Flash the factory image, run the whole script, then flash MaiPai for StackChan and run it again. Repeat in reverse order once, to catch drift.
- Same Wi-Fi access point and distance. Note the host computer, the language model and the speech models for our run.
- Record every run with a fixed microphone placed beside the robot, 48 kHz, so the audio is judged the same way for both firmwares.

## Script

Twenty turns per firmware, the same spoken prompts each time:

1. Ten short questions ("what time is it", "set a timer for one minute").
2. Five medium questions that need a two or three sentence answer.
3. Five interrupts: say "stop" or touch the robot while it speaks.

## Measurements

| Measure | How |
|---|---|
| Wake cue delay | End of the wake phrase to the first cue sound or screen change, from the recording and a screen capture |
| Stop delay | Start of "stop" or the touch to silence |
| Time to first audio | End of the question to the first spoken sound |
| Stutter count | Gaps in the reply audio longer than 80 ms, found by script, then checked by listening |
| Longest gap | The longest silence inside a reply |
| Face smoothness | Frame times from a 120 fps phone capture of the screen during a reply |

Report median and p95 for each, with all 20 turns in an appendix.

## Pass line

The claim "faster and smoother" stands only if ours is better on time to first audio, stutter count and longest gap, and no worse on wake cue and stop delay.
If any measure is worse, say so on the compare page and change the README wording.

## Needs

A robot that can be re-flashed with both images, a spare hour with the owner for the spoken script, and the build lane's timing tool (see `docs/design/performance-and-latency.md`).
