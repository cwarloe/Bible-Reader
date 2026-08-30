"""ElevenLabs generation with content-addressed caching.

Every take is stored under a hash of the exact inputs that produced it: the
text, the voice, the model, and the voice settings. Re-running generation after
editing one line regenerates that line and nothing else — which is the
difference between a few hundred characters and re-rendering an entire suite.

Uses urllib rather than the ElevenLabs SDK so the pipeline has no HTTP
dependency to keep in sync.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import VoiceSettings
from .model import Block, Program

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
MANIFEST_NAME = "manifest.json"


class GenerationError(RuntimeError):
    pass


def take_hash(block: Block, voice: VoiceSettings) -> str:
    """Content address for one take. Any input change yields a new hash."""
    payload = json.dumps(
        {"text": block.text, **voice.as_dict()},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def take_path(raw_dir: Path, program: Program, block: Block, voice: VoiceSettings, ext: str = "mp3") -> Path:
    return raw_dir / program.slug / f"{block.id}.{take_hash(block, voice)}.{ext}"


@dataclass
class GenerationPlan:
    """What a generate run would do, before it does it."""

    to_generate: list[tuple[Block, Path]]
    cached: list[tuple[Block, Path]]
    stale: list[Path]

    @property
    def billable_chars(self) -> int:
        return sum(block.char_count for block, _ in self.to_generate)


def plan_generation(
    program: Program,
    voice: VoiceSettings,
    raw_dir: Path,
    ext: str = "mp3",
) -> GenerationPlan:
    """Work out which takes are missing, which are reusable, and which are orphans."""
    to_generate: list[tuple[Block, Path]] = []
    cached: list[tuple[Block, Path]] = []
    wanted: set[Path] = set()

    for block in program.all_blocks():
        path = take_path(raw_dir, program, block, voice, ext)
        wanted.add(path)
        (cached if path.exists() else to_generate).append((block, path))

    program_dir = raw_dir / program.slug
    existing = set(program_dir.glob(f"*.{ext}")) if program_dir.exists() else set()
    stale = sorted(existing - wanted)

    return GenerationPlan(to_generate=to_generate, cached=cached, stale=stale)


def synthesize(text: str, voice: VoiceSettings, api_key: str, timeout: int = 120) -> bytes:
    """One text-to-speech call. Returns raw audio bytes."""
    if not voice.voice_id:
        raise GenerationError("no voice_id configured; set elevenlabs.voice_id in config.yaml")

    body = json.dumps(
        {
            "text": text,
            "model_id": voice.model_id,
            "voice_settings": {
                "stability": voice.stability,
                "similarity_boost": voice.similarity_boost,
                "style": voice.style,
                "speed": voice.speed,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL.format(voice_id=voice.voice_id),
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise GenerationError(f"ElevenLabs returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GenerationError(f"could not reach ElevenLabs: {exc.reason}") from exc


def resolve_api_key(explicit: str | None = None) -> str:
    key = explicit or os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        raise GenerationError(
            "no API key: set ELEVENLABS_API_KEY in your environment or .env"
        )
    return key


def write_manifest(raw_dir: Path, program: Program, voice: VoiceSettings, ext: str = "mp3") -> Path:
    """Record which take file belongs to which block, for the assembler and for
    anyone reading the output directory later."""
    program_dir = raw_dir / program.slug
    program_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "slug": program.slug,
        "title": program.title,
        "track_type": program.track_type,
        "voice": voice.as_dict(),
        "takes": [
            {
                "id": block.id,
                "hash": take_hash(block, voice),
                "file": take_path(raw_dir, program, block, voice, ext).name,
                "chars": block.char_count,
                "words": block.word_count,
            }
            for block in program.all_blocks()
        ],
    }
    path = program_dir / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path
