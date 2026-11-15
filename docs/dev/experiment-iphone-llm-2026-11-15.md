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
