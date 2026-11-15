# Pick hardware and a model

How well the robot answers depends on the computer and the model behind it. The robot, the host program and MaiPai for StackChan do the same work either way. Your language model decides how fast and how well it answers.

## What depends on your model

| Depends on your model and its hardware | Does not depend on it |
|---|---|
| How soon the first word comes after you stop talking | The wake cue and the listening light |
| How good, correct and natural the answers are | "Stop", mute, volume and brightness |
| Whether it follows a request like "set a timer" the right way | Timers and alarms once set, and the clock |
| How steady it is over a long talk | Faces, reactions and the dance |
| Speech in Spanish, and how it handles other languages | The camera switch and the mute switch |

A small model on a modest computer answers fast and gets simple things right. A big model answers better but needs more memory and more time. The robot reacts at once either way, because those parts run on the robot.

## A rough guide

- **A 4B-class model** answers in under 400 ms to the first token once it is warm. It is a good start on a small host.
- **A 27B-class model** gives better answers, but on a weak computer the first word is slow. It needs a computer built for it.
- **Memory is the limit.** The model must fit in the computer's memory with room left for everything else. Bigger models need more.

These are the figures from our design notes. We will publish measured numbers for named computers and models before release.

## Choose where the model runs

1. **On the host.** One small computer runs the host and a small model. It is the simplest and works well for short answers.
2. **On a bigger computer on your network.** Point `llm_url` at it. The host stays small and the model runs where there is more memory.
3. **On MaiPai Home.** MaiPai Home keeps its models loaded on a machine set up for them. It lists what each memory size can run on its install page, and the same sizes are a good guide for your own model. See [Use MaiPai Home as the brain](with-maipai-home.md).

## If answers are slow or wrong

| What you see | What went wrong | What to do |
|---|---|---|
| A long wait before the first word | The model is too big for the computer, or it was not loaded yet | Pick a smaller model, or ask the first question again after it warms up |
| Wrong or odd answers | The model is too small for the job | Try a larger one |
| It ignores "set a timer" | The model does not call actions well | Use the voice commands, or try a model that supports tools |
| Answers cut off or repeat | The computer ran short of memory | Close other programs, or use a smaller model |

Run `stackchan check` after you change the model.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
