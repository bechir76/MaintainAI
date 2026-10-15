"""Page-aware chunking with overlap.

Chunks never cross a page boundary, so every chunk has exactly one page to
cite. Inside a page, lines are packed greedily up to `size` characters, a new
chunk is preferred at a section heading, and the tail of the previous chunk
(up to `overlap` characters) is repeated at the start of the next one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ingestion.pdf import Page

_HEADING = re.compile(r"^\d+(\.\d+)*\.? [A-Z]")
_SENTENCE_END = re.compile(r"(?<=[.;:!?])\s+")


@dataclass(frozen=True)
class Chunk:
    page: int
    index: int
    text: str


def _split_long_line(line: str, size: int) -> list[str]:
    if len(line) <= size:
        return [line]
    parts: list[str] = []
    current = ""
    for piece in _SENTENCE_END.split(line):
        while len(piece) > size:  # no sentence boundary: cut on a word boundary
            cut = piece.rfind(" ", 0, size)
            cut = cut if cut > 0 else size
            parts.append(piece[:cut].strip())
            piece = piece[cut:].strip()
        if current and len(current) + len(piece) + 1 > size:
            parts.append(current)
            current = piece
        else:
            current = f"{current} {piece}".strip()
    if current:
        parts.append(current)
    return parts


def _tail(lines: list[str], overlap: int) -> list[str]:
    tail: list[str] = []
    total = 0
    for line in reversed(lines):
        if total + len(line) > overlap:
            break
        tail.insert(0, line)
        total += len(line) + 1
    return tail


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    lines = [part for line in text.splitlines() for part in _split_long_line(line, size)]
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    fresh = 0  # lines added since the overlap was carried over

    def emit() -> None:
        nonlocal current, length, fresh
        chunks.append("\n".join(current))
        current = _tail(current, overlap)
        length = sum(len(x) + 1 for x in current)
        fresh = 0

    for line in lines:
        at_heading = bool(_HEADING.match(line)) and length > size // 2
        if fresh and (length + len(line) + 1 > size or at_heading):
            emit()
            if at_heading:
                # Start a new section cleanly rather than with the previous section's tail.
                current, length = [], 0
        current.append(line)
        length += len(line) + 1
        fresh += 1
    if fresh:
        chunks.append("\n".join(current))
    return chunks


def chunk_pages(pages: list[Page], size: int = 900, overlap: int = 150) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for text in chunk_text(page.text, size, overlap):
            chunks.append(Chunk(page=page.number, index=len(chunks), text=text))
    return chunks
