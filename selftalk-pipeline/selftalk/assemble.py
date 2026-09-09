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


def _tile_noise(noise_sample, duration_ms: int):
    """Tile *noise_sample* to exactly *duration_ms* by repeating as needed."""
    pad = noise_sample
    while len(pad) < duration_ms:
        pad = pad + noise_sample
    return pad[:duration_ms]


def _make_noise_pad(
    noise_sample,
    duration_ms: int,
    *,
    fade_in_ms: int = 0,
    fade_out_ms: int = 0,
):
    """Tile *noise_sample* to *duration_ms* and apply linear amplitude fades at either edge.

    When gaps are filled with continuous noise (the normal path), only one of
    the two fades is ever non-zero:
      lead pad  — fade_out_ms cross-fades with the clip's own fade_in
      tail pad  — fade_in_ms  cross-fades with the clip's own fade_out

    The gap-facing edge no longer needs a fade because the gap itself is
    textured noise at the same level — there is no silence to ramp into.

    Both fades are applied independently and each is clamped to duration_ms
    so they never overlap in a way that causes pydub to raise.
    """
    pad = _tile_noise(noise_sample, duration_ms)
    if fade_in_ms > 0:
        pad = pad.fade_in(min(fade_in_ms, duration_ms))
    if fade_out_ms > 0:
        pad = pad.fade_out(min(fade_out_ms, duration_ms))
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

    # --- Noise-texture reference (built fresh from this batch's clips) ------
    # ElevenLabs clips carry a consistent background noise floor (~-64 dBFS).
    # The strategy here is continuous noise: rather than inserting absolute
    # silence between clips/repeats and trying to fade in/out of it, ALL gaps
    # are filled with the same tiled noise at a reduced level (noise_pad_gain_db,
    # default 0 = full clip level, daytime uses -10 dBFS for subtlety).  The
    # listener hears one consistent room tone from start to finish; voices
    # appear and disappear on top of it, eliminating any on/off toggling.
    # Falls back to zero-silence everywhere if no clip yields a noise window.
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
    # Apply the per-track gain to the reference once; all subsequent tiling
    # inherits this level automatically — pads, inter-repeat gaps, and inter-
    # block gaps all share the same noise floor so there is nothing to fade
    # across at the gap edge.
    if noise_sample is not None and pacing.noise_pad_gain_db != 0.0:
        noise_sample = noise_sample.apply_gain(pacing.noise_pad_gain_db)

    for block_id, repeat, repeat_gap_ms, trailing_gap_ms in plan_layout(program, pacing):
        block = blocks_by_id[block_id]
        path = take_path(config.raw_dir, program, block, voice, ext)

        if not path.exists():
            missing.append(block_id)
            continue

        raw_clip = AudioSegment.from_file(path)

        # Short linear amplitude ramp at both clip edges eliminates click
        # discontinuities without being audible as attack/release.
        if pacing.clip_fade_in_ms:
            raw_clip = raw_clip.fade_in(pacing.clip_fade_in_ms)
        if pacing.clip_fade_out_ms:
            raw_clip = raw_clip.fade_out(pacing.clip_fade_out_ms)

        # Build lead/tail pads.  With continuous-noise gaps the pad only needs
        # to cross-fade with the clip's own edge fade — there is no silence to
        # ramp in/out of, so gap_fade_ms is not used here.  The silence fallback
        # path keeps the gap_fade_ms behaviour for environments with no clips.
        if noise_sample is not None:
            lead = (
                _make_noise_pad(
                    noise_sample,
                    pacing.clip_lead_ms,
                    # Gap-facing edge matches the continuous gap noise — no fade.
                    # Clip-facing edge cross-fades with the clip's own fade-in.
                    fade_out_ms=pacing.clip_fade_in_ms,
                )
                if pacing.clip_lead_ms
                else AudioSegment.empty()
            )
            tail = (
                _make_noise_pad(
                    noise_sample,
                    pacing.clip_tail_ms,
                    # Clip-facing edge cross-fades with the clip's own fade-out.
                    # Gap-facing edge matches the continuous gap noise — no fade.
                    fade_in_ms=pacing.clip_fade_out_ms,
                )
                if pacing.clip_tail_ms
                else AudioSegment.empty()
            )
            # Inter-repeat and trailing gaps: noisy, not silent.
            def _noise_gap(ms: int):
                return _tile_noise(noise_sample, ms) if ms else AudioSegment.empty()
        else:
            # Fallback: zero-silence pads with gap fades (original behaviour).
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
            def _noise_gap(ms: int):
                return AudioSegment.silent(duration=ms) if ms else AudioSegment.empty()

        clip = lead + raw_clip + tail

        for index in range(repeat):
            master += clip
            if index < repeat - 1:
                master += _noise_gap(repeat_gap_ms)

        if trailing_gap_ms:
            master += _noise_gap(trailing_gap_ms)
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
