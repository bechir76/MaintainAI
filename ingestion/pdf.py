from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

# Third-party PDFs often use fonts pypdf only half supports; the text still extracts.
logging.getLogger("pypdf").setLevel(logging.ERROR)

_PAGE_NUMBER = re.compile(r"^page \d+( of \d+)?$", re.IGNORECASE)


@dataclass(frozen=True)
class Page:
    number: int  # 1-based, as printed and as cited
    text: str


_BULLET = re.compile("^[\x7f•●▪*-]$")
_LIST_NUMBER = re.compile(r"^\d{1,2}\.?$")
_CONTROL = re.compile("[\x00-\x08\x0b-\x1f�]")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    out: list[str] = []
    marker = ""
    for line in lines:
        # List markers are often extracted on a line of their own; fold them into the item.
        if _BULLET.match(line):
            marker = "- "
            continue
        if _LIST_NUMBER.match(line):
            marker = f"{line.rstrip('.')}. "
            continue
        line = _CONTROL.sub("", line.replace("\x7f", "")).strip()
        if line:
            out.append(marker + line)
            marker = ""
    return "\n".join(out)


def _boilerplate(pages: list[list[str]]) -> set[str]:
    """Lines repeated on most pages (running headers and footers)."""
    if len(pages) < 2:
        return set()
    counts = Counter(line for lines in pages for line in set(lines))
    return {line for line, n in counts.items() if n >= max(2, 0.6 * len(pages))}


def parse_pdf(path: Path) -> list[Page]:
    reader = PdfReader(path)
    raw = [clean_text(page.extract_text() or "").splitlines() for page in reader.pages]
    repeated = _boilerplate(raw)
    pages = []
    for number, lines in enumerate(raw, start=1):
        kept = [ln for ln in lines if ln not in repeated and not _PAGE_NUMBER.match(ln)]
        pages.append(Page(number=number, text="\n".join(kept)))
    return pages
