"""The shelf: the bytes of one `pantry` asset item (docs/design/content-pantry.md, section 3): one kind in one language.

Layout: a 16 byte header (format version u8, language 2 bytes, rating ceiling u8, record count u16, index offset u32, 6 reserved), an index of 16 bytes per
record (id 8, kind 1, rating 1, flags 1, text offset 3, text length 2) and the packed texts. A record's text blob is text, answer and extra split by
a zero byte. The unit reads the index in place from flash; the host writes it, and reads it back to prove the round trip."""

from __future__ import annotations

import struct

from maipai_packages.pantry.record import KINDS, RATINGS, Record, RecordError, check

VERSION = 1
HEADER = struct.Struct("<B2sBHI6x")  # 16 bytes
INDEX = struct.Struct("<8sBBB3sH")  # 16 bytes
ITEM_CAP_BYTES = 40_960  # cap per item of the pantry kind (10 sectors)
SECTOR = 4096


def sectors(size: int) -> int:
    return -(-size // SECTOR)


def pack(records: list[Record], *, rating_ceiling: str = "kid") -> bytes:
    """One shelf from records of one kind and one language. Raises RecordError when they do not fit one item."""
    if not records:
        raise RecordError("A shelf needs at least one record.")
    kind, language = records[0].kind, records[0].language
    if any(r.kind != kind or r.language != language for r in records):
        raise RecordError("A shelf holds one kind in one language.")
    if rating_ceiling not in RATINGS:
        raise RecordError("The rating ceiling must be kid or adult.")
    blobs, index = [], []
    offset = HEADER.size + INDEX.size * len(records)
    for record in records:
        record = check(record)
        if record.rating == "adult" and rating_ceiling == "kid":
            raise RecordError("An adult record cannot go on a kid shelf.")
        blob = b"\0".join(part.encode("utf-8") for part in (record.text, record.answer, record.extra))
        index.append(INDEX.pack(record.id, KINDS.index(record.kind), RATINGS.index(record.rating), 0, offset.to_bytes(3, "little"), len(blob)))
        blobs.append(blob)
        offset += len(blob)
    body = HEADER.pack(VERSION, language.encode("ascii"), RATINGS.index(rating_ceiling), len(records), HEADER.size) + b"".join(index) + b"".join(blobs)
    if len(body) > ITEM_CAP_BYTES:
        raise RecordError(f"The shelf is {len(body)} bytes; one item holds {ITEM_CAP_BYTES}. Build it with fewer records.")
    return body


def unpack(body: bytes) -> list[Record]:
    """The records of a shelf body, checked. A body that is cut short or says one thing and holds another raises RecordError."""
    if len(body) < HEADER.size:
        raise RecordError("The shelf is shorter than its header.")
    version, language, ceiling, count, index_at = HEADER.unpack_from(body)
    if version != VERSION:
        raise RecordError(f"The shelf has format {version}; this host reads format {VERSION}.")
    if index_at + INDEX.size * count > len(body):
        raise RecordError("The shelf index runs past the end of the body.")
    out = []
    for n in range(count):
        rid, kind, rating, _flags, off3, length = INDEX.unpack_from(body, index_at + n * INDEX.size)
        start = int.from_bytes(off3, "little")
        if start + length > len(body):
            raise RecordError("A shelf record runs past the end of the body.")
        try:
            parts = body[start:start + length].decode("utf-8").split("\0")
        except UnicodeDecodeError as error:
            raise RecordError("A shelf record is not valid text.") from error
        parts += [""] * (3 - len(parts))
        record = Record(KINDS[kind], language.decode("ascii"), RATINGS[rating], parts[0], parts[1], parts[2])
        if record.id != rid:
            raise RecordError("A shelf record does not match its id.")
        out.append(record)
    return out


def capacity_for(kind: str, free_bytes: int, sample: list[Record]) -> int:
    """How many records of this kind fit the free bytes (and one item), judged by the average size of a sample."""
    if not sample:
        return 0
    per = sum(len("\0".join((r.text, r.answer, r.extra)).encode("utf-8")) + INDEX.size for r in sample) / len(sample)
    return max(0, int((min(free_bytes, ITEM_CAP_BYTES) - HEADER.size) // per))
