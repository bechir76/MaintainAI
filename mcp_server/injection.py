"""Detection and neutralisation of instruction-like text in retrieved documents.

Retrieved chunks are data, but a document can carry text aimed at the model
("ignore previous instructions", "call create_maintenance_ticket ..."), often
hidden from human readers (white or tiny text, zero-width characters). Before a
chunk leaves the MCP server, every sentence is checked against a set of
patterns; matching sentences are replaced with a marker and the chunk is
flagged. This is one layer: role checks on the server and the agent's system
prompt still apply if something slips through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REDACTION = "[removed: instruction-like text]"

# Zero-width, bidi-override and Unicode tag characters used to hide text.
_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿\U000e0000-\U000e007f]")

_PATTERNS: dict[str, re.Pattern[str]] = {
    name: re.compile(pattern, re.IGNORECASE)
    for name, pattern in {
        "override_instructions": (
            r"\b(ignore|disregard|forget|override|bypass)\b[^.]{0,40}"
            r"\b(previous|prior|above|earlier|all|any|your|the|system|safety)\b[^.]{0,20}"
            r"\b(instructions?|rules?|prompts?|guidelines|directives)\b"
        ),
        "role_hijack": (
            r"\byou are now\b|\bact as (an? )?(admin|administrator|system|developer|root)\b"
            r"|\b(developer|god|jailbreak|\w+ override) mode\b"
        ),
        "fake_system_message": (
            r"\b(system|developer|admin)\s+(prompt|message|notice|instruction|override)s?\b"
            r"|<\|?(im_start|im_end|system|assistant|user)\|?>"
            r"|^\s*(system|assistant)\s*:"
            r"|\bnew instructions?\b|\bto the (assistant|ai|model|llm)\b"
        ),
        "tool_invocation": (
            r"\b(create_maintenance_ticket|get_sensor_readings|search_manuals|list_machines)\b"
            r"|\b(call|invoke|execute|run|use) (the |a )?(tool|function)\b"
        ),
        "safety_bypass": (
            r"\b(lockout|tagout|loto|isolation|ppe|permit)\b[^.]{0,60}"
            r"\b(is not|isn't|are not|not) (required|needed|necessary)\b"
            r"|\b(can|may) be (changed|replaced|removed|opened|serviced)\b[^.]{0,40}"
            r"\bwhile\b[^.]{0,30}\brunning\b"
        ),
        "concealment": r"\b(do not|don't|never) (tell|inform|mention|reveal)\b[^.]{0,40}\buser\b",
    }.items()
}

_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|(?=\n)|$)|[.!?]+|\n")


@dataclass
class Sanitized:
    text: str
    findings: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return bool(self.findings)


def scan(text: str) -> list[str]:
    """Names of the patterns found in `text` (empty when clean)."""
    return [name for name, pattern in _PATTERNS.items() if pattern.search(text)]


def sanitize(text: str) -> Sanitized:
    findings: list[str] = []
    if _INVISIBLE.search(text):
        findings.append("invisible_characters")
        text = _INVISIBLE.sub("", text)

    parts = _SENTENCE.findall(text)
    hits = [scan(p) if p != "\n" else [] for p in parts]
    flagged = [bool(h) for h in hits]
    # Text sandwiched between two flagged sentences on the same line belongs to the injection.
    for i in range(1, len(parts) - 1):
        if not flagged[i] and parts[i] != "\n" and flagged[i - 1] and flagged[i + 1]:
            flagged[i] = True

    out: list[str] = []
    for part, is_flagged, names in zip(parts, flagged, hits, strict=True):
        if not is_flagged:
            out.append(part)
            continue
        findings.extend(n for n in names if n not in findings)
        if not out or not out[-1].endswith(REDACTION):
            out.append(f" {REDACTION}")
    cleaned = re.sub(r"[ \t]+", " ", "".join(out)).strip()
    return Sanitized(text=cleaned, findings=findings)
