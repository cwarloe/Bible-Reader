"""Guards the actual script library, not just the machinery.

If someone edits a program YAML into a state that would waste credits or fail a
generation run, that breaks here rather than at the API.
"""

from pathlib import Path

import pytest

from selftalk.config import load_config
from selftalk.model import discover_programs
from selftalk.validate import has_errors, validate_program

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = discover_programs(ROOT / "content")


def test_the_library_is_not_empty():
    assert PROGRAMS


@pytest.mark.parametrize("program", PROGRAMS, ids=lambda p: p.slug)
def test_every_program_passes_validation(program):
    config = load_config(ROOT / "config.yaml")
    pacing = config.pacing_for(program.track_type, program.pacing_overrides)
    findings = [f for f in validate_program(program, pacing) if f.severity == "error"]
    assert not findings, "\n".join(str(f) for f in findings)


def test_slugs_are_unique():
    slugs = [p.slug for p in PROGRAMS]
    assert len(slugs) == len(set(slugs))
