"""The content schema: one YAML file per program, one program per audio track.

A program is a list of blocks. A block is one thing you say. How many times it
gets said, and how much silence follows it, comes from the track type — so the
same block list can be rendered as a morning directive or a daytime drill
without editing the content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

# ElevenLabs v3 audio tags: bracketed direction like [calm, steady] or [pause].
# They steer delivery but are never spoken, so they must not count toward the
# word budget when estimating runtime.
AUDIO_TAG_RE = re.compile(r"\[[^\]\n]{0,80}\]")

# The subset of tags that buy silence rather than shape tone.
PAUSE_TAGS = {"pause", "beat", "long pause", "short pause"}

PERSPECTIVES = ("first_person", "second_person")


@dataclass
class Block:
    """One spoken unit: a sentence, a tricolon, a descriptor list.

    `id` is the cache key and the raw-take filename, so it must be stable —
    renaming an id forces a regeneration, editing the text is what should.
    """

    id: str
    text: str
    repeat: int | None = None
    pause_after_ms: int | None = None
    note: str = ""

    @property
    def spoken_text(self) -> str:
        """The text with audio tags removed — what actually gets vocalized."""
        return normalize_whitespace(AUDIO_TAG_RE.sub(" ", self.text))

    @property
    def word_count(self) -> int:
        return len(self.spoken_text.split())

    @property
    def char_count(self) -> int:
        """Characters billed by ElevenLabs, tags included — they count."""
        return len(self.text)

    @property
    def pause_tag_count(self) -> int:
        return sum(
            1
            for tag in AUDIO_TAG_RE.findall(self.text)
            if tag.strip("[]").strip().lower() in PAUSE_TAGS
        )


@dataclass
class Program:
    """One YAML file: everything needed to render a single track."""

    slug: str
    title: str
    track_type: str
    perspective: str
    blocks: list[Block]
    suite: str = ""
    source: str = ""
    target_minutes: float | None = None
    synthesis: Block | None = None
    voice_overrides: dict[str, Any] = field(default_factory=dict)
    pacing_overrides: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None

    def all_blocks(self) -> Iterator[Block]:
        """Every block that needs a generated take, synthesis coda included."""
        yield from self.blocks
        if self.synthesis is not None:
            yield self.synthesis

    @property
    def word_count(self) -> int:
        """Unique words written, not words heard — repeats are not counted here."""
        return sum(b.word_count for b in self.all_blocks())


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


class ContentError(ValueError):
    """A program file that cannot be loaded at all (as opposed to one that
    loads but fails validation — see selftalk.validate)."""


def _block_from_raw(raw: Any, where: str) -> Block:
    if not isinstance(raw, dict):
        raise ContentError(f"{where}: expected a mapping with 'id' and 'text', got {type(raw).__name__}")
    missing = [k for k in ("id", "text") if not raw.get(k)]
    if missing:
        raise ContentError(f"{where}: missing required field(s): {', '.join(missing)}")
    return Block(
        id=str(raw["id"]),
        text=str(raw["text"]).strip(),
        repeat=raw.get("repeat"),
        pause_after_ms=raw.get("pause_after_ms"),
        note=str(raw.get("note", "")),
    )


def load_program(path: Path | str) -> Program:
    """Parse one program YAML file. Raises ContentError on anything unusable."""
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ContentError(f"{path}: not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ContentError(f"{path}: expected a top-level mapping")

    for required in ("title", "track_type"):
        if not raw.get(required):
            raise ContentError(f"{path}: missing required field '{required}'")

    blocks_raw = raw.get("blocks") or []
    if not blocks_raw:
        raise ContentError(f"{path}: has no blocks")

    blocks = [_block_from_raw(b, f"{path} block[{i}]") for i, b in enumerate(blocks_raw)]

    synthesis = None
    if raw.get("synthesis"):
        synthesis = _block_from_raw(raw["synthesis"], f"{path} synthesis")

    return Program(
        slug=str(raw.get("slug") or path.stem),
        title=str(raw["title"]),
        track_type=str(raw["track_type"]),
        perspective=str(raw.get("perspective", "second_person")),
        blocks=blocks,
        suite=str(raw.get("suite", "")),
        source=str(raw.get("source", "")),
        target_minutes=raw.get("target_minutes"),
        synthesis=synthesis,
        voice_overrides=raw.get("voice") or {},
        pacing_overrides=raw.get("pacing") or {},
        path=path,
    )


def discover_programs(root: Path | str = "content") -> list[Program]:
    """Load every program under `root`, sorted by path for stable ordering."""
    root = Path(root)
    paths = sorted(p for p in root.rglob("*.yaml") if not p.name.startswith("_"))
    return [load_program(p) for p in paths]
