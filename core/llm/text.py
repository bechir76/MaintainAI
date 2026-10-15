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
            token = token[: -len(suffix)]
            break
    # "regrease" and "regreased" should meet at the same stem.
    return token[:-1] if token.endswith("e") and len(token) > 4 else token


def tokenize(text: str) -> list[str]:
    tokens = []
    for raw in _TOKEN.findall(text.lower()):
        if raw in STOPWORDS:
            continue
        if raw.isalpha():
            tokens.append(stem(raw))
            continue
        tokens.append(raw)
        # Compound words such as "lockout/tagout" also match their parts.
        parts = re.split(r"[-./]", raw)
        if len(parts) > 1 and all(p.isalpha() and len(p) >= 3 for p in parts):
            tokens.extend(stem(p) for p in parts if p not in STOPWORDS)
    return tokens
