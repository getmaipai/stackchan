# Host configuration

The host reads `~/.config/maipai/robot.toml`. On first run it copies the commented safe-default example there and prints the file location. Edit that file, then restart the host.

`brain` is `"llm"` by default. `"standalone"` is an accepted alias. The current own-LLM brain is a placeholder that returns a clear not-installed reply. `"home"` selects the Home adapter.

`[llm]` accepts `url`, `model`, `stt_url`, and `tts_url`. Leave the speech URLs absent to use the built-in local speech engines. `[home]` accepts `url`, `language`, `quiet_hours_from`, and `quiet_hours_to`; quiet-hour fields use the setting keys `household.quiet_hours.from` and `household.quiet_hours.to`. `[remote] enabled` defaults to `false`.

Unknown fields stop startup and name the key to correct or remove. `stackchan pair` prints a six-digit code for the unit setup page. The code expires after ten minutes, works once, and allows five attempts per source in ten minutes. On success the host creates the normal per-device token record. `stackchan status` shows the selected brain and paired device identifiers with last-seen time when available.
