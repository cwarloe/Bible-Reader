"""Session assembly: raw takes in, one finished track out.

The assembler is deliberately dumb about content. It reads the same block list
the generator did, looks up each take by content hash, and lays it out
according to the track's pacing. Changing a track from morning to daytime is a
one-line edit to the YAML, not a different code path.

pydub is imported lazily so that validate/stats/plan all work on a machine with
no ffmpeg installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config, Pacing, VoiceSettings
from .estimate import plan_layout
from .generate import take_path
from .model import Program


__all__ = ["AssemblyError", "AssemblyReport", "assemble_program", "plan_layout"]


class AssemblyError(RuntimeError):
    pass


def _audio_segment():
    try:
        from pydub import AudioSegment
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise AssemblyError(
            "pydub is required to assemble audio: pip install -r requirements.txt "
            "(and install ffmpeg)"
        ) from exc
    return AudioSegment


@dataclass
class AssemblyReport:
    output_path: Path
    duration_ms: float
    blocks_used: int
    missing: list[str]


def assemble_program(
    program: Program,
    config: Config,
    voice: VoiceSettings,
    pacing: Pacing,
    *,
    ext: str = "mp3",
    strict: bool = True,
) -> AssemblyReport:
    """Stitch the generated takes into the finished session track."""
    AudioSegment = _audio_segment()

    blocks_by_id = {b.id: b for b in program.all_blocks()}
    master = AudioSegment.empty()
    missing: list[str] = []
    used = 0

    for block_id, repeat, repeat_gap_ms, trailing_gap_ms in plan_layout(program, pacing):
        block = blocks_by_id[block_id]
        path = take_path(config.raw_dir, program, block, voice, ext)

        if not path.exists():
            missing.append(block_id)
            continue

        raw_clip = AudioSegment.from_file(path)

        # Pad each take with dead silence so generation-edge clicks land in
        # quiet rather than at an audible join point.
        lead = AudioSegment.silent(duration=pacing.clip_lead_ms) if pacing.clip_lead_ms else AudioSegment.empty()
        tail = AudioSegment.silent(duration=pacing.clip_tail_ms) if pacing.clip_tail_ms else AudioSegment.empty()
        clip = lead + raw_clip + tail

        repeat_gap = AudioSegment.silent(duration=repeat_gap_ms)

        for index in range(repeat):
            master += clip
            if index < repeat - 1:
                master += repeat_gap

        if trailing_gap_ms:
            master += AudioSegment.silent(duration=trailing_gap_ms)
        used += 1

    if missing and strict:
        raise AssemblyError(
            f"{len(missing)} take(s) not generated yet: {', '.join(missing)}. "
            "Run `selftalk generate` first."
        )

    config.master_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.master_dir / f"{program.slug}.{config.output_format}"
    master.export(output_path, format=config.output_format, bitrate=config.bitrate)

    return AssemblyReport(
        output_path=output_path,
        duration_ms=len(master),
        blocks_used=used,
        missing=missing,
    )
