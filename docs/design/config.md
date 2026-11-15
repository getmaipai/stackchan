# Host configuration

The host reads `~/.config/maipai/robot.toml`. On first run it copies the commented safe-default example there and prints the file location. Edit that file, then restart the host.

`brain` is `"llm"` by default. `"standalone"` is an accepted alias. The current own-LLM brain is a placeholder that returns a clear not-installed reply. `"home"` selects the Home adapter.

`[llm]` accepts `url`, `model`, `stt_url`, and `tts_url`. Leave the speech URLs absent to use the built-in local speech engines. `[home]` accepts `url`, `language`, `quiet_hours_from`, and `quiet_hours_to`; quiet-hour fields use the setting keys `household.quiet_hours.from` and `household.quiet_hours.to`. `[remote] enabled` defaults to `false`.

Unknown fields stop startup and name the key to correct or remove. `stackchan pair` prints a six-digit code for the unit setup page. The code expires after ten minutes, works once, and allows five attempts per source in ten minutes. On success the host creates the normal per-device token record. `stackchan status` shows the selected brain and paired device identifiers with last-seen time when available.

## Several robots (design, owner question 2026-11-15; not built)

Today pairing already issues one token per unit, but the config has one `[llm]`, one persona and one set of settings for every unit. Several robots need per-unit settings:
- Each paired unit gets a name (`stackchan name <id> kitchen`) and an optional `[units.kitchen]` table in `robot.toml`. Any key from the top-level tables can be overridden there: `[units.kitchen.llm]` (its own model, URL, persona, key variable), language, voice, speech speed, quiet hours, face and colour, night mode, volume cap, default alarms.
- Anything not overridden inherits the top-level value. Unknown unit names are an error that names the key; a unit with no table behaves exactly as today.
- Alarms and timers run on each unit (they ring with the host off), so they are per unit by nature. Recurring alarms are defined per unit in `[[units.kitchen.alarm]]` (time, days, label, sound) and pushed to that unit when it connects.
- The host keeps conversation history and the local settings page per unit; the status command and the bench page show and pick a unit.
- With Home, the same per-unit settings live in Home's robot settings and the host reads them; the brain choice can differ per unit (one on Home, one on its own LLM).
- Limits: one host serves a handful of units at once (memory and model speed decide); announcements and intercom between units are Home features.
Build: a small phase after phase 5 (config model, per-unit brain selection, per-unit history, alarm push, settings page unit picker, tests with two fake units).
