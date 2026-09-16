"""Runtime estimation.

The whole point of the Helmstetter format is that a track runs about eight
minutes. Word count alone is a bad proxy, because a daytime track says every
line three times and spends a third of its runtime in deliberate silence. This
module models both, so a script can be checked against its target before a
single ElevenLabs credit is spent.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Pacing
from .model import Block, Program


@dataclass
class BlockEstimate:
    block_id: str
    repeat: int
    speech_ms: float
    silence_ms: float

    @property
    def total_ms(self) -> float:
        return self.speech_ms + self.silence_ms


@dataclass
class ProgramEstimate:
    slug: str
    blocks: list[BlockEstimate]

    @property
    def speech_ms(self) -> float:
        return sum(b.speech_ms for b in self.blocks)

    @property
    def silence_ms(self) -> float:
        return sum(b.silence_ms for b in self.blocks)

    @property
    def total_ms(self) -> float:
        return self.speech_ms + self.silence_ms

    @property
    def total_minutes(self) -> float:
        return self.total_ms / 60_000


def estimate_block(block: Block, pacing: Pacing, *, repeat: int | None = None) -> BlockEstimate:
    """Model one block as: N spoken passes, separated and followed by silence."""
    n = repeat if repeat is not None else (block.repeat or pacing.repeat)
    n = max(1, n)

    words_ms = (block.word_count / max(pacing.words_per_minute, 1)) * 60_000
    # In-line [pause] tags buy silence inside a single pass.
    inline_silence_ms = block.pause_tag_count * pacing.pause_tag_ms

    trailing_ms = block.pause_after_ms if block.pause_after_ms is not None else pacing.pause_block_ms
    between_repeats_ms = (n - 1) * pacing.pause_repeat_ms

    return BlockEstimate(
        block_id=block.id,
        repeat=n,
        speech_ms=n * words_ms,
        silence_ms=n * inline_silence_ms + between_repeats_ms + trailing_ms,
    )




def plan_layout(program: Program, pacing: Pacing) -> list[tuple[str, int, int, int]]:
    """The track's timeline as data: (block_id, repeat, gap between repeats, trailing gap).

    This is the single definition of what a finished track looks like. Both the
    estimator and the assembler read it, so a predicted runtime and a rendered
    one cannot drift apart.
    """
    layout: list[tuple[str, int, int, int]] = []

    for block in program.blocks:
        repeat = max(1, block.repeat or pacing.repeat)
        trailing = block.pause_after_ms if block.pause_after_ms is not None else pacing.pause_block_ms
        layout.append((block.id, repeat, pacing.pause_repeat_ms, trailing))

    if program.synthesis is not None:
        # The coda is introduced by the longer perspective-shift pause, modelled
        # as the trailing gap of whatever came before it. An explicit
        # pause_after_ms on that block is a deliberate choice and still wins.
        if layout and program.blocks[-1].pause_after_ms is None:
            block_id, repeat, gap, _ = layout[-1]
            layout[-1] = (block_id, repeat, gap, pacing.pause_transition_ms)
        # Nothing follows the coda, so it gets no trailing silence.
        layout.append((program.synthesis.id, 1, 0, 0))

    return layout


def estimate_program(program: Program, pacing: Pacing) -> ProgramEstimate:
    """Estimate the finished track by walking the same layout the assembler will."""
    blocks_by_id = {b.id: b for b in program.all_blocks()}
    estimates: list[BlockEstimate] = []

    for block_id, repeat, repeat_gap_ms, trailing_gap_ms in plan_layout(program, pacing):
        block = blocks_by_id[block_id]
        words_ms = (block.word_count / max(pacing.words_per_minute, 1)) * 60_000
        inline_silence_ms = block.pause_tag_count * pacing.pause_tag_ms

        estimates.append(
            BlockEstimate(
                block_id=block_id,
                repeat=repeat,
                speech_ms=repeat * words_ms,
                silence_ms=repeat * inline_silence_ms
                + (repeat - 1) * repeat_gap_ms
                + trailing_gap_ms,
            )
        )

    return ProgramEstimate(slug=program.slug, blocks=estimates)


def format_duration(ms: float) -> str:
    total_seconds = int(round(ms / 1000))
    return f"{total_seconds // 60}m {total_seconds % 60:02d}s"


def words_needed_for(target_minutes: float, pacing: Pacing, silence_ms: float = 0.0) -> int:
    """How many spoken words a track needs to hit its target, given its silence.

    Useful when a draft comes back short: it answers "how much more do I write?"
    rather than leaving you to guess.
    """
    speech_ms = max(target_minutes * 60_000 - silence_ms, 0)
    return int(round((speech_ms / 60_000) * pacing.words_per_minute))
