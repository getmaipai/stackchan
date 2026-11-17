# ruff: noqa: E501
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
from dataclasses import dataclass

from maipai_body import reply_tags

MAX_TAG_CHARS = 60
SOFT_LIMIT_CHARS = 240
_TAGLIKE = re.compile(rf"^\[[A-Za-z_:\-= ]{{0,{MAX_TAG_CHARS}}}$")
_BOUNDARY = re.compile(r"""([.!?…]+["')\]]*)(\s+)|(\n+)""")
_ABBREVIATIONS = frozenset({"mr", "mrs", "ms", "dr", "st", "vs", "prof", "sr", "jr"})


def _tidy(sentence: str) -> str:
    """One space between words and none before punctuation (a removed tag leaves gaps)."""
    return re.sub(r"\s+([.!?,;:])", r"\1", re.sub(r"[ \t]+", " ", sentence)).strip()


MARK = "\ue000"  # stands where a tag was, when ``marks`` is on (a private-use character, never spoken)


class TagStripper:
    """Drops ``[...]`` spans from a stream of chunks; ``on_tag`` hears each tag's inner text.

    With ``marks`` on, a private-use character is left where each tag was, so a later step can tell which
    sentence each tag belonged to (see :class:`ReplyTagger`). Off (the default) nothing is left behind."""

    def __init__(self, on_tag: Callable[[str], None] | None = None, *, marks: bool = False) -> None:
        self._held = ""
        self._on_tag = on_tag
        self._marks = marks
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
                    if self._marks:
                        out.append(MARK)
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


# ---- tags with meaning: the mood and overlay cues a reply carries ----------------------------------


@dataclass(frozen=True)
class Cue:
    """One thing to do at a point in the reply: ``mood`` (name), ``overlay`` (name, intensity, seconds)
    or ``overlay_end`` (name)."""

    kind: str
    name: str
    intensity: str = reply_tags.DEFAULT_INTENSITY
    seconds: float = 0.0


@dataclass(frozen=True)
class Item:
    """One step of the reply in order: a sentence to speak (``text``), or cues to act on (``cues``)."""

    text: str = ""
    cues: tuple[Cue, ...] = ()


class ReplyTagger:
    """Streamed chunks in; speakable sentences and cues out, in order, with every tag removed.

    A mood tag becomes a ``mood`` cue ahead of its sentence. An overlay tag becomes an ``overlay`` cue ahead of
    the sentence where it opens and an ``overlay_end`` cue after the sentence where it closes; one left open
    ends with the sentence it started in. The robot is told what to show: a reply with no mood tag changes no
    face (there is no guessing from the words, owner decision 2026-11-17). ``moods`` and ``overlays`` switch each kind off:
    their tags are still removed, never spoken.
    """

    def __init__(self, *, moods: bool = True, overlays: bool = True) -> None:
        self._strip = TagStripper(marks=True)
        self._split = SentenceSplitter()
        self._moods, self._overlays = moods, overlays
        self._tagged = 0  # tags already matched to a mark
        self._open: dict[str, Cue] = {}  # overlays opened in an earlier sentence, still running
        self._sentences = 0
        self._mood_seen = False

    @property
    def tags(self) -> list[str]:
        return self._strip.tags

    def feed(self, chunk: str, *, whole: bool = False) -> list[Item]:
        text = self._strip.feed(chunk)
        if whole:
            text += "\n"
        return self._items(self._split.feed(text))

    def flush(self) -> list[Item]:
        tail = self._strip.flush()
        return self._items([*self._split.feed(tail), *self._split.flush()], closing=True)

    def _items(self, sentences: list[str], *, closing: bool = False) -> list[Item]:
        items: list[Item] = []
        for raw in sentences:
            items.extend(self._one(raw))
        if closing:
            # Tags at the very end ("... [/rain]") arrive as a mark with no text around them.
            for name in list(self._open):
                self._open.pop(name)
                items.append(Item(cues=(Cue("overlay_end", name),)))
        return items

    def _take_tags(self, raw: str) -> list[reply_tags.Tag]:
        found: list[reply_tags.Tag] = []
        for _ in range(raw.count(MARK)):
            if self._tagged < len(self._strip.tags):
                found.append(reply_tags.parse_tag(self._strip.tags[self._tagged]))
                self._tagged += 1
        return found

    def _one(self, raw: str) -> list[Item]:
        tags = self._take_tags(raw)
        pieces = raw.split(MARK)
        text = _tidy("".join(pieces))
        later = [reply_tags.parse_tag(x) for x in self._strip.tags[self._tagged :]]
        before: list[Cue] = []
        after: list[Cue] = []
        opened_here: set[str] = set()
        for index, tag in enumerate(tags):
            if tag.kind == "mood" and self._moods:
                before.append(Cue("mood", tag.name))
                self._mood_seen = True
            elif tag.kind == "overlay" and self._overlays:
                rest = tags[index + 1 :]
                spoken_after = _tidy("".join(pieces[index + 1 :]))
                before.append(Cue("overlay", tag.name, tag.intensity, reply_tags.span_seconds(spoken_after)))
                opened_here.add(tag.name)
                closed_here = any(t.kind == "overlay_end" and t.name == tag.name for t in rest)
                closes_later = any(t.kind == "overlay_end" and t.name == tag.name for t in later)
                if closed_here:
                    continue  # its own closing tag ends it
                if closes_later:
                    self._open[tag.name] = before[-1]  # a span over several sentences
                else:
                    after.append(Cue("overlay_end", tag.name))  # unclosed: to the end of this sentence
            elif tag.kind == "overlay_end" and self._overlays and (tag.name in self._open or tag.name in opened_here):
                self._open.pop(tag.name, None)
                after.append(Cue("overlay_end", tag.name))
        if text:
            self._sentences += 1
        items: list[Item] = []
        if before:
            items.append(Item(cues=tuple(before)))
        if text:
            items.append(Item(text=text))
        if after:
            items.append(Item(cues=tuple(after)))
        return items
