"""Configuration: global defaults, per-track-type presets, per-program overrides.

Resolution order, lowest precedence first:

    TRACK_PRESETS[track_type]  ->  config.yaml  ->  the program's own `voice:`/`pacing:` block

so a program only has to state what makes it different.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config.yaml")


@dataclass
class VoiceSettings:
    """Everything that affects what ElevenLabs returns for a line of text.

    Every field here feeds the cache key, so changing any of them correctly
    invalidates previously generated takes.
    """

    voice_id: str = ""
    model_id: str = "eleven_v3"
    stability: float = 0.75
    similarity_boost: float = 0.80
    style: float = 0.05
    speed: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "model_id": self.model_id,
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "speed": self.speed,
        }


@dataclass
class Pacing:
    """Silence budget, in milliseconds.

    `repeat` is the Helmstetter triplication count: how many times each block is
    spoken back to back before moving on.

    `clip_lead_ms` / `clip_tail_ms` pad each raw take with dead silence before
    and after the speech.  ElevenLabs occasionally introduces a faint click at
    the very start or end of a generation; a few milliseconds of cushion pushes
    that transient away from the audible join point.  Both default to 0 (no
    change) so existing assembled tracks are unaffected unless the config is
    updated.
    """

    repeat: int = 1
    pause_repeat_ms: int = 0
    pause_block_ms: int = 1200
    pause_transition_ms: int = 3500
    pause_tag_ms: int = 700
    words_per_minute: int = 105
    clip_lead_ms: int = 0
    clip_tail_ms: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "repeat": self.repeat,
            "pause_repeat_ms": self.pause_repeat_ms,
            "pause_block_ms": self.pause_block_ms,
            "pause_transition_ms": self.pause_transition_ms,
            "pause_tag_ms": self.pause_tag_ms,
            "words_per_minute": self.words_per_minute,
            "clip_lead_ms": self.clip_lead_ms,
            "clip_tail_ms": self.clip_tail_ms,
        }


# The three delivery formats, and what makes each one sound different.
#
#   morning  "The Directive"    second person, continuous prose, brisk breaks
#   daytime  "The Conditioning" first person, every line three times, long breaks
#   night    "The Integration"  second person, slow, generous silence for sleep
TRACK_PRESETS: dict[str, dict[str, Any]] = {
    "morning": {
        "repeat": 1,
        "pause_repeat_ms": 0,
        "pause_block_ms": 1200,
        "words_per_minute": 105,
    },
    "daytime": {
        "repeat": 3,
        "pause_repeat_ms": 1100,
        "pause_block_ms": 2200,
        "words_per_minute": 105,
    },
    "night": {
        "repeat": 1,
        "pause_repeat_ms": 0,
        "pause_block_ms": 2500,
        "words_per_minute": 95,
    },
}

TRACK_TYPES = tuple(TRACK_PRESETS)


@dataclass
class Config:
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    pacing_overrides: dict[str, Any] = field(default_factory=dict)
    output_format: str = "mp3"
    bitrate: str = "192k"
    raw_dir: Path = Path("output/raw_takes")
    master_dir: Path = Path("output/master")

    def pacing_for(self, track_type: str, program_overrides: dict[str, Any] | None = None) -> Pacing:
        """Layer the presets, the config file, and the program's own overrides."""
        values = copy.deepcopy(TRACK_PRESETS.get(track_type, {}))
        values.update({k: v for k, v in self.pacing_overrides.items() if v is not None})
        values.update({k: v for k, v in (program_overrides or {}).items() if v is not None})
        known = Pacing().as_dict()
        return Pacing(**{k: v for k, v in values.items() if k in known})

    def voice_for(self, program_overrides: dict[str, Any] | None = None) -> VoiceSettings:
        values = self.voice.as_dict()
        values.update({k: v for k, v in (program_overrides or {}).items() if v is not None})
        known = VoiceSettings().as_dict()
        return VoiceSettings(**{k: v for k, v in values.items() if k in known})


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> Config:
    """Read config.yaml. A missing file is fine — the defaults above stand in."""
    path = Path(path)
    if not path.exists():
        return Config()

    raw = yaml.safe_load(path.read_text()) or {}
    voice_raw = raw.get("elevenlabs", {}) or {}
    known_voice = VoiceSettings().as_dict()
    voice = VoiceSettings(**{k: v for k, v in voice_raw.items() if k in known_voice})

    audio = raw.get("audio", {}) or {}
    paths = raw.get("paths", {}) or {}

    return Config(
        voice=voice,
        pacing_overrides=raw.get("pacing", {}) or {},
        output_format=audio.get("output_format", "mp3"),
        bitrate=audio.get("bitrate", "192k"),
        raw_dir=Path(paths.get("raw_dir", "output/raw_takes")),
        master_dir=Path(paths.get("master_dir", "output/master")),
    )
