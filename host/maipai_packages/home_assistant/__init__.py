"""Home Assistant voice and camera snapshots, as an optional local package (off by default).

Voice: a spoken request that starts with the trigger phrase ("home assistant, turn off the kitchen
light") goes to Home Assistant's own conversation endpoint as plain text, and Home Assistant's
answer is spoken. The model never builds a service call and never sees the token. Camera: "what is
on the front door camera" fetches one snapshot from a camera listed in robot.toml and asks the
configured model about that one picture. Everything stays on the local network.
"""

from maipai_packages.home_assistant.client import HomeAssistant, HomeAssistantError

__all__ = ["HomeAssistant", "HomeAssistantError"]
