"""Make your own wake word on this computer: record clips on the settings page, train a small model, check it, install it.

Off by default. Recordings, the dataset and the model stay in one folder on this computer (nothing is uploaded). The model is a small
local detector; the unit and the host do not use an installed model yet, so installing records it and keeps the C header for the
firmware track. Recording from the browser needs the settings page opened on this computer (or over https)."""

from maipai_packages.wake_word_maker.flow import WakeWordMaker
from maipai_packages.wake_word_maker.store import ClipError, WakeStore

__all__ = ["ClipError", "WakeStore", "WakeWordMaker"]
