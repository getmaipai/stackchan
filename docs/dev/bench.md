# StackChan bench

Start a local testing console with `stackchan bench`. It binds to `127.0.0.1:9790` and does not need a password. Use `stackchan bench --sim` to exercise the page without a connected unit. Use `--host` and `--port` to select another address; a non-loopback address requires `--token SECRET`, which the page sends as a bearer token for API writes.

With several units, pick one in the Unit list at the top (default: the only unit, or the first online). Every control and the log carry the unit; `GET /api/units` lists them and `?unit=` on `/api/status` and `/api/tools` picks one. A bad unit gets a plain error naming what to do.

The page shows unit status and the raw reported MCP tool list. Lights offers pixel, side and full-ring controls, brightness, off and animation controls. Meaning colors are reference only and are not applied remotely. Face offers the built-in face names, caption, look direction and night and clock controls. Head and body offers bounded pan and tilt, home, dance, nod and touch simulation. Sound offers earcons, volume and typed speech. Privacy controls change mute, camera and quiet cues; the page never opens the camera or microphone. The generic tool caller exposes the unit's reported schema and raw reply, with dangerous tools hidden until enabled and requiring the word `CONFIRM`. The log keeps the latest 200 calls and can be copied, saved as JSON, or replayed.

## Checks owed by the bench (not the owner)

- **Quiet now and the quiet schedule (decision 22, firmware SF52).** On a unit with SF52: set Quiet now on the settings page, then `self.audio.sound_info` must answer `quiet_now` true and `night` true, event sounds stay silent, an alarm you set still rings, and the shutter click still plays. Turn it off and sounds return. Then save a schedule for Monday to Friday 22:00 to 07:00: quiet at 23:00 on a Thursday and at 03:00 on a Saturday, not at 23:00 on a Saturday. Record the result in `docs/dev/bench-evidence/`.
