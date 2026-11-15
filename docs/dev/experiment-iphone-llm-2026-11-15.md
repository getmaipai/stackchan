# Experiment: run the language model on an iPhone

Owner idea, 2026-11-15. The robot joins a phone hotspot when it travels. Could the same iPhone also run the language model, so a trip needs no laptop for the model?

## Findings so far (a web search, not a test)

- Several iPhone apps run a model on the phone and expose an OpenAI-compatible address on the local network. Examples found: Local LLM Server (uses Apple Intelligence models, needs iOS 26), LLM Server, and MLXHub. Names and versions come from App Store listings and are not tested.
- One report says iOS blocks GPU use in the background, so the app must stay open and in front. Not confirmed for these apps.
- On a hotspot the phone has its own address that the robot can reach, so `llm_url` could point at it.

## What would have to be true

1. The model server keeps answering with the screen locked, or the phone stays awake and the app in front.
2. A 3B to 8B model answers in under a second to the first token, on the phone's memory, without throttling from heat.
3. The host program still runs somewhere: a laptop or a Raspberry Pi. The host does not run on an iPhone.
4. The hotspot and the model together do not drain the battery faster than one evening.

## Plan

1. Pick one app that exposes an OpenAI-compatible address and one small model.
2. Join the robot to the phone's hotspot, run the host on a laptop on the same hotspot, and set `llm_url` to the phone's address.
3. Ask ten short questions. Record time to first token, the answer quality, the battery drop and the phone's temperature, with the screen on and then locked.
4. Report whether it works, with the numbers. If it works, add a short "phone as a brain" page marked Planned.

## Risks

- iOS may suspend the server when the app leaves the front.
- A phone that is both hotspot and model server may overheat.
- App Store apps change. Do not pin a name in the user docs until it is tested.

Needs: an iPhone, the unit, a laptop, and the owner's time for a trip test.

## Bigger idea: the phone as the whole host (owner, 2026-11-15)

Owner: could the iPhone run a local model and the robot just point at it, so users need no computer?

Why a model app alone is not enough: the robot does not call a model. The unit has about 76 KB of free internal memory and speaks one protocol to the host. The host does speech to text, the model call and text to speech. A model-serving app gives only the model call, so a host must still exist.

Options:

| Option | Computer needed | Notes |
|---|---|---|
| Host on a Raspberry Pi 5, model on the phone | A small box | Works with today's design. The smallest setup |
| Host on a laptop, model on the phone | A laptop | The experiment above |
| A native iPhone app as the host and brain | None | A new client: the robot link and pairing, speech to text and text to speech with Apple's on-device speech, the model from an on-device model or a local model app. Not built |
| Host in the cloud | None | Breaks the privacy promise. Rejected |

Questions for the native app: can it keep the robot link and the model alive when the screen locks (iOS suspends background apps; audio or network background modes may help but need a test); battery and heat with a hotspot on; App Store review; model size and tool use limits; whether it is a separate client rather than an extension of the core app. By the scope rule it is a separate thing, not a feature of the core.

Next step: finish the laptop-host experiment first, then decide whether a native iPhone host is worth building.
