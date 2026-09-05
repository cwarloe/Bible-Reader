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


def _extract_noise_sample(
    AudioSegment,
    clip_paths: list[Path],
    *,
    window_ms: int = 200,
    target_ms: int = 600,
    threshold_dbfs: float = -55.0,
):
    """Build a loopable noise-texture segment from the quietest windows in the batch.

    The ElevenLabs voice model produces a consistent background noise floor
    (measured at −64 dBFS across this library).  Padding with absolute digital
    silence (−∞ dBFS) creates a 64+ dB contrast that the ear hears as dead air.
    This function profiles that noise floor from the clips themselves — no
    external reference file needed — and returns a segment the assembler can
    tile and use as pad material instead of zeros.

    Algorithm
    ---------
    For each clip, the signal is down-mixed to mono and scanned with a sliding
    window (step = window_ms / 4) to find the single quietest interior region.
    Windows quieter than `threshold_dbfs` are accepted as pure noise; the
    corresponding slice is extracted from the original file (preserving its
    channel count and sample rate) and appended to the collection.  The
    collection is tiled to at least `target_ms` so callers always receive
    enough material to slice any pad length from.

    Returns None when no clip yields a window below the threshold, in which
    case the assembler falls back to zero-silence pads.
    """
    try:
        import numpy as np
    except ImportError:
        return None

    collected = []

    for path in clip_paths:
        try:
            mono = AudioSegment.from_file(path).set_channels(1)
        except Exception:
            continue

        if len(mono) < window_ms:
            continue

        samples = np.array(mono.get_array_of_samples(), dtype=np.float64)
        win_samp = int(mono.frame_rate * window_ms / 1000)
        if win_samp <= 0:
            continue

        full_scale = 2 ** (8 * mono.sample_width - 1)
        best_rms = float("inf")
        best_ms = 0
        step = max(win_samp // 4, 1)

        for i in range(0, len(samples) - win_samp, step):
            rms = float(np.sqrt(np.mean(samples[i : i + win_samp] ** 2)))
            if rms < best_rms:
                best_rms = rms
                best_ms = int(i * 1000 / mono.frame_rate)

        if best_rms == 0:
            continue
        if 20 * np.log10(best_rms / full_scale) > threshold_dbfs:
            continue

        # Extract the window from the original file so channel count and
        # sample rate match whatever the rest of the assembled track uses.
        try:
            orig = AudioSegment.from_file(path)
            end_ms = min(best_ms + window_ms, len(orig))
            collected.append(orig[best_ms:end_ms])
        except Exception:
            continue

    if not collected:
        return None

    # Concatenate all quiet windows, then tile until we reach target_ms.
    combined = collected[0]
    for seg in collected[1:]:
        combined = combined + seg
    while len(combined) < target_ms:
        combined = combined + combined
    return combined[:target_ms]


def _make_noise_pad(noise_sample, duration_ms: int, fade_ms: int, *, fade_at_end: bool):
    """Tile *noise_sample* to *duration_ms* and apply a linear amplitude fade.

    *fade_at_end=True*  — the pad fades to zero at its right edge (used on the
                          lead so the noise blends into the clip's fade-in).
    *fade_at_end=False* — the pad fades in from zero at its left edge (used on
                          the tail so the clip's fade-out blends into noise).

    Together with the clip's own fade_in / fade_out the two fades form a
    cross-fade: as the noise goes to zero the clip comes up, and vice versa.
    """
    pad = noise_sample
    while len(pad) < duration_ms:
        pad = pad + noise_sample
    pad = pad[:duration_ms]
    fade_ms = min(fade_ms, duration_ms)
    if fade_ms > 0:
        if fade_at_end:
            pad = pad.fade_out(fade_ms)
        else:
            pad = pad.fade_in(fade_ms)
    return pad


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

    # --- Noise-texture pad (built fresh from this batch's clips) -----------
    # ElevenLabs generates a consistent background noise floor (~-64 dBFS).
    # Using absolute zero-silence pads creates a 64+ dB contrast the ear hears
    # as dead air.  Instead we extract the quietest interior windows from the
    # batch's own raw clips and tile them into a noise-texture reference the
    # lead/tail pads are sliced from.  Falls back to zero-silence if no clip
    # yields a window below the threshold (e.g. on a first run with no cached
    # takes yet — though in that case assembly would fail anyway).
    raw_dir_for_program = config.raw_dir / program.slug
    existing_clips = (
        sorted(raw_dir_for_program.glob(f"*.{ext}"))
        if raw_dir_for_program.exists()
        else []
    )
    noise_sample = (
        _extract_noise_sample(AudioSegment, existing_clips)
        if existing_clips
        else None
    )

    for block_id, repeat, repeat_gap_ms, trailing_gap_ms in plan_layout(program, pacing):
        block = blocks_by_id[block_id]
        path = take_path(config.raw_dir, program, block, voice, ext)

        if not path.exists():
            missing.append(block_id)
            continue

        raw_clip = AudioSegment.from_file(path)

        # Apply a short linear amplitude ramp so the waveform reaches zero at
        # both clip edges.  A non-zero sample value at the cut point creates a
        # step discontinuity that the listener hears as a click; the fade
        # removes it without being audible as attack or release.
        if pacing.clip_fade_in_ms:
            raw_clip = raw_clip.fade_in(pacing.clip_fade_in_ms)
        if pacing.clip_fade_out_ms:
            raw_clip = raw_clip.fade_out(pacing.clip_fade_out_ms)

        # Build the lead/tail pads.  When a noise sample is available, each pad
        # holds the ambient noise floor of the recording and fades toward zero
        # at the edge that meets the clip — forming a cross-fade with the clip's
        # own fade_in / fade_out so there is no moment of absolute silence.
        if noise_sample is not None:
            lead = (
                _make_noise_pad(
                    noise_sample,
                    pacing.clip_lead_ms,
                    pacing.clip_fade_in_ms,
                    fade_at_end=True,
                )
                if pacing.clip_lead_ms
                else AudioSegment.empty()
            )
            tail = (
                _make_noise_pad(
                    noise_sample,
                    pacing.clip_tail_ms,
                    pacing.clip_fade_out_ms,
                    fade_at_end=False,
                )
                if pacing.clip_tail_ms
                else AudioSegment.empty()
            )
        else:
            # Fallback: zero-silence pads (original behaviour, no noise sample).
            lead = (
                AudioSegment.silent(duration=pacing.clip_lead_ms)
                if pacing.clip_lead_ms
                else AudioSegment.empty()
            )
            tail = (
                AudioSegment.silent(duration=pacing.clip_tail_ms)
                if pacing.clip_tail_ms
                else AudioSegment.empty()
            )

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
