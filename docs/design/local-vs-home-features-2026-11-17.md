# Local mode and Home mode: what you get in each (2026-11-17)

Placement: design note and source for the user docs (the docs session turns it into `docs/user/` pages). Facts: [from code] means read in this repo or the stock tree at commit 28b9f0c8, [decided] means an owner or build-session decision, [unverified] means not checked on a real unit or hub.

## The separation

- One firmware for every setup. The firmware has no Home code; it talks only to the host. [from code]
- The host runs the brain. Local mode: any OpenAI-compatible model you run yourself, plus local speech (Moonshine, Piper). Home mode: the household hub supplies the model, memory, people and data. [from code]
- Local mode keeps everything in the home: no weather service, no vendor cloud, no accounts. Anything that needs the internet comes through Home, or the feature is off. [decided]
- The robot is complete without a hub: wake word, stop, mute, timers and alarms, faces, effects, games, pages, settings and the remote controls all work with no Home. [from code]

## Stock features that need the internet, and what replaces them

| Stock feature (stock tree, or the vendor service it talks to) | Local mode | Home mode |
|---|---|---|
| AI chat (stock sends your voice to the vendor's cloud model) | Your own model on your network | The hub's model, memory and persona |
| Questions about weather, news, sports, general facts (answered by the vendor's cloud agent; the stock firmware itself has no weather code) | The model answers from what it knows; no live data | The hub looks it up with its own tools and sends a card or words |
| Time and date (public network time) | The host sets the clock; time zones built in | Same |
| Firmware updates from the vendor | Signed update from your own host (key not yet created) [unverified] | Same, through the hub |
| Phone app control and Bluetooth | Not built; the settings page and remote controllers replace it | Same, plus the hub's app |
| Video call and camera upload to a web address | Removed on purpose (vendor cloud) | Camera and photos go to the hub only |
| App Center, cloud data, vendor accounts | Removed on purpose | The hub's package catalog |
| Reminders and timers | On the unit, no network | Same |

Stock offers no on-device weather feature [from code: no weather or forecast strings in the stock firmware tree]. The weather answers the stock robot gives come from its cloud agent. So parity on weather means: ask in Home mode and the hub answers with live data; ask in local mode and the model answers from its own knowledge, with no live data.

## What each mode gives you

Both modes: voice chat, wake word, stop word, faces and animations, overlay effects, pages and swipes, games, timers and alarms (set and cancel by voice, no model), photos on the unit, settings page, remote controls with their cues, private network option, update from your own host.

Local mode only: no live weather, news or web lookups; the model speaks from its own knowledge.

Home mode adds: live weather and other tool data as cards, memory and people, scenes and household tools, face recognition by the hub, the package catalog.

## Rules for new features

1. A feature that needs outside data is a Home tool. In local mode it is off or answers from the model's knowledge, and the page says so in plain words ("Connect Home for live weather").
2. The host never fetches from the internet on its own account. A feature that would need that is an exception the owner must approve and the egress proof must list.
3. Nothing is removed from what stock offers without a line in this table saying what replaces it or that it was removed on purpose and why.

## Open checks

- [unverified] Confirm with the stock app which other vendor-cloud features exist (for example music, stories, knowledge packs) and add each to the table. The stock firmware tree cannot answer this; the vendor service defines it.
- [unverified] Confirm the hub exposes a weather tool and a way to return a card; see `llm-display-control-2026-11-17.md`.
