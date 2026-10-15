"""Small text helpers shared by the offline providers."""

from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+(?:[-./][a-z0-9]+)*")

STOPWORDS = frozenset(
    """a an and are as at be been before by can do does for from has have how i if in into is it
    its my of on or our should so than that the their then there these this to up was we what when
    where which while who why will with you your me any all about after also not no please tell
    must may only more most other over same such very each per out off""".split()
)


def stem(token: str) -> str:
    # Deliberately light: enough to match "bearings"/"bearing" or "vibrating"/"vibration".
    for suffix in (
        "ations",
        "ation",
        "ating",
        "ated",
        "ates",
        "ate",
        "ings",
        "ing",
        "ies",
        "ed",
        "es",
        "s",
    ):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    tokens = []
    for raw in _TOKEN.findall(text.lower()):
        if raw in STOPWORDS:
            continue
        tokens.append(stem(raw) if raw.isalpha() else raw)
    return tokens
