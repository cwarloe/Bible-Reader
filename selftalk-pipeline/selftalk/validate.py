"""Pre-flight checks, run before anything is generated.

Every rule here exists because it is a mistake that costs either credits or a
re-record: SSML that v3 silently reads aloud, a block that exceeds the
single-generation window, a script that is two minutes short of its target.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .config import TRACK_TYPES, Pacing
from .estimate import estimate_program, format_duration
from .model import PERSPECTIVES, Program

Severity = Literal["error", "warning"]

# ElevenLabs single-request text limit. Past this the request is rejected;
# well before it, delivery starts to drift across a long take.
MAX_CHARS_PER_GENERATION = 5000
CHARS_WARN_THRESHOLD = 3000

# v3 does not support SSML. A <break time="1.0s" /> is either ignored or, worse,
# read out as literal text in the middle of a finished take.
SSML_RE = re.compile(r"<\s*(break|prosody|speak|emphasis|say-as|phoneme)\b", re.IGNORECASE)

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# How far a script may land from its stated target before it is worth flagging.
TARGET_TOLERANCE = 0.15


@dataclass
class Finding:
    severity: Severity
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.where}: {self.message}"


def validate_program(program: Program, pacing: Pacing) -> list[Finding]:
    findings: list[Finding] = []

    def add(severity: Severity, where: str, message: str) -> None:
        findings.append(Finding(severity, where, message))

    if program.track_type not in TRACK_TYPES:
        add("error", program.slug, f"unknown track_type {program.track_type!r}; expected one of {', '.join(TRACK_TYPES)}")
    if program.perspective not in PERSPECTIVES:
        add("error", program.slug, f"unknown perspective {program.perspective!r}; expected one of {', '.join(PERSPECTIVES)}")

    # The daytime format is defined by first-person drilling; a second-person
    # daytime track is more likely a mislabel than a deliberate choice.
    if program.track_type == "daytime" and program.perspective != "first_person":
        add("warning", program.slug, "daytime tracks are first-person in the source format; this one is second-person")
    if program.track_type == "daytime" and program.synthesis is None:
        add("warning", program.slug, "daytime tracks close with a second-person synthesis coda; none is defined")

    seen: dict[str, int] = {}
    for block in program.all_blocks():
        where = f"{program.slug}/{block.id}"

        seen[block.id] = seen.get(block.id, 0) + 1
        if seen[block.id] == 2:
            add("error", where, "duplicate block id; ids must be unique within a program")

        if not ID_RE.match(block.id):
            add("error", where, "block id must be lowercase alphanumeric with - or _ (it becomes a filename)")

        if not block.spoken_text:
            add("error", where, "block has audio tags but no spoken text")

        if SSML_RE.search(block.text):
            add("error", where, "contains SSML; v3 does not support it and may read the tag aloud — use [pause] instead")

        if block.char_count > MAX_CHARS_PER_GENERATION:
            add("error", where, f"{block.char_count} chars exceeds the {MAX_CHARS_PER_GENERATION}-char single-generation limit; split the block")
        elif block.char_count > CHARS_WARN_THRESHOLD:
            add("warning", where, f"{block.char_count} chars is a long single take; delivery may drift")

        if block.text.count("[") != block.text.count("]"):
            add("warning", where, "unbalanced square brackets; an audio tag may be malformed and get spoken")

    if program.target_minutes:
        estimate = estimate_program(program, pacing)
        low = program.target_minutes * (1 - TARGET_TOLERANCE)
        high = program.target_minutes * (1 + TARGET_TOLERANCE)
        if not low <= estimate.total_minutes <= high:
            direction = "short of" if estimate.total_minutes < low else "over"
            add(
                "warning",
                program.slug,
                f"estimated {format_duration(estimate.total_ms)} is {direction} the {program.target_minutes:g}-minute target",
            )

    return findings


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity == "error" for f in findings)
