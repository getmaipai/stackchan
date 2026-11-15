# Home tools

Everything here runs on the host. All of it is off by default, and every one needs a token. None of it calls an outside service.

| Tool | What it is for | Turn on |
|---|---|---|
| Local API | Start a timer, show a face or speak, over REST and WebSocket. | `api = true` |
| Event stream | Get a message when the robot hears you, is picked up or finishes a timer. | `events = true` |
| MQTT | Send the same events to your own MQTT broker. | `mqtt_url = "..."` |
| Home-automation bridge | Show the robot as a device in your home-automation system. | `ha_bridge = true` |
| Metrics | A page with counts and timings for your own dashboard. | `metrics = true` |

Run `stackchan token` to create a token. Run `stackchan check` to test each address.

![The web page with the API, MQTT and metrics switches.](../images/api-settings.svg)

## Ideas

- A status light for your server: the ring turns red when a job fails.
- A busy light: the ring shows red while you are on a call.
- A dimmer: slide the head strip to dim a lamp through the bridge.

## Safety

Tokens can be revoked at any time. The link between the host and your other tools is as private as your network.
Use a network you trust until the encrypted link ships.
