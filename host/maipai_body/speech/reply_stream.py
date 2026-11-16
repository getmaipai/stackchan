"""Turn a streamed reply (text chunks) into whole, speakable sentences.

Two small pieces, both pure text with no I/O so they are easy to test:

* :class:`TagStripper` removes ``[tag]`` spans (mood and overlay tags) before anything is spoken.
  A tag may arrive split across chunks, so an open ``[`` is held back until its ``]`` shows up.
* :class:`SentenceSplitter` cuts the cleaned text into sentences as soon as each one is complete,
  so the first sentence can be spoken while the rest of the reply is still being written.
"""

from __future__ import annotations

import re
from collections.abc import Callable

MAX_TAG_CHARS = 60
SOFT_LIMIT_CHARS = 240
_TAGLIKE = re.compile(rf"^\[[A-Za-z_:\-= ]{{0,{MAX_TAG_CHARS}}}$")
_BOUNDARY = re.compile(r"""([.!?…]+["')\]]*)(\s+)|(\n+)""")
_ABBREVIATIONS = frozenset({"mr", "mrs", "ms", "dr", "st", "vs", "prof", "sr", "jr"})


def _tidy(sentence: str) -> str:
    """One space between words and none before punctuation (a removed tag leaves gaps)."""
    return re.sub(r"\s+([.!?,;:])", r"\1", re.sub(r"[ \t]+", " ", sentence)).strip()


class TagStripper:
    """Drops ``[...]`` spans from a stream of chunks; ``on_tag`` hears each tag's inner text."""

    def __init__(self, on_tag: Callable[[str], None] | None = None) -> None:
        self._held = ""
        self._on_tag = on_tag
        self.tags: list[str] = []

    def feed(self, chunk: str) -> str:
        out: list[str] = []
        for char in chunk:
            if self._held:
                self._held += char
                if char == "]":
                    inner = self._held[1:-1].strip()
                    self._held = ""
                    self.tags.append(inner)
                    if self._on_tag is not None:
                        self._on_tag(inner)
                elif char == "\n" or len(self._held) > MAX_TAG_CHARS:
                    out.append(self._held)  # not a tag after all: it is plain text
                    self._held = ""
            elif char == "[":
                self._held = "["
            else:
                out.append(char)
        return "".join(out)

    def flush(self) -> str:
        """The end of the stream: an unfinished tag is dropped, anything else is plain text."""
        held, self._held = self._held, ""
        return "" if _TAGLIKE.match(held) else held


class SentenceSplitter:
    """Collects text and returns each sentence once it is complete, in order."""

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, text: str) -> list[str]:
        self._buffer += text
        sentences: list[str] = []
        while True:
            cut = self._find_cut()
            if cut is None:
                break
            sentence, self._buffer = self._buffer[:cut], self._buffer[cut:]
            sentence = _tidy(sentence)
            if sentence:
                sentences.append(sentence)
        return sentences

    def flush(self) -> list[str]:
        """The end of the stream: whatever is left is spoken even without closing punctuation."""
        rest, self._buffer = _tidy(self._buffer), ""
        return [rest] if rest else []

    def _find_cut(self) -> int | None:
        for match in _BOUNDARY.finditer(self._buffer):
            if match.group(1) is not None:
                before = self._buffer[: match.start(1)]
                word = re.search(r"([A-Za-z]+)$", before)
                if (
                    match.group(1) == "."
                    and word is not None
                    and word.group(1).lower() in _ABBREVIATIONS
                ):
                    continue
            return match.end()
        if len(self._buffer) > SOFT_LIMIT_CHARS:
            window = self._buffer[:SOFT_LIMIT_CHARS]
            for mark in (", ", " "):
                index = window.rfind(mark)
                if index > 0:
                    return index + len(mark)
        return None
