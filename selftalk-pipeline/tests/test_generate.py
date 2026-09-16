from pathlib import Path

from selftalk.config import VoiceSettings
from selftalk.generate import plan_generation, take_hash, take_path
from selftalk.model import Block, Program


def make_program(blocks, synthesis=None):
    return Program(
        slug="p",
        title="T",
        track_type="daytime",
        perspective="first_person",
        blocks=blocks,
        synthesis=synthesis,
    )


def test_hash_changes_when_text_changes():
    voice = VoiceSettings(voice_id="v1")
    a = take_hash(Block(id="a", text="One."), voice)
    b = take_hash(Block(id="a", text="Two."), voice)
    assert a != b


def test_hash_changes_when_voice_settings_change():
    block = Block(id="a", text="One.")
    assert take_hash(block, VoiceSettings(voice_id="v1")) != take_hash(block, VoiceSettings(voice_id="v2"))
    assert take_hash(block, VoiceSettings(voice_id="v1", stability=0.5)) != take_hash(
        block, VoiceSettings(voice_id="v1", stability=0.9)
    )


def test_hash_is_stable_for_identical_input():
    voice = VoiceSettings(voice_id="v1")
    assert take_hash(Block(id="a", text="One."), voice) == take_hash(Block(id="a", text="One."), voice)


def test_block_id_does_not_affect_the_hash_only_the_filename():
    """Two blocks with the same text still get their own take file, but renaming
    a block is a rename, not a content change."""
    voice = VoiceSettings(voice_id="v1")
    assert take_hash(Block(id="a", text="One."), voice) == take_hash(Block(id="b", text="One."), voice)


def test_existing_take_is_reused_and_edited_line_is_regenerated(tmp_path: Path):
    voice = VoiceSettings(voice_id="v1")
    program = make_program([Block(id="a", text="One."), Block(id="b", text="Two.")])

    plan = plan_generation(program, voice, tmp_path)
    assert len(plan.to_generate) == 2 and not plan.cached

    # Pretend both were generated.
    for block in program.blocks:
        path = take_path(tmp_path, program, block, voice)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")

    plan = plan_generation(program, voice, tmp_path)
    assert not plan.to_generate and len(plan.cached) == 2

    # Editing one line must regenerate exactly that line.
    edited = make_program([Block(id="a", text="One, revised."), Block(id="b", text="Two.")])
    plan = plan_generation(edited, voice, tmp_path)
    assert [b.id for b, _ in plan.to_generate] == ["a"]
    assert [b.id for b, _ in plan.cached] == ["b"]
    # The superseded take is reported as stale rather than silently orphaned.
    assert len(plan.stale) == 1


def test_billable_chars_counts_only_what_will_be_generated(tmp_path: Path):
    voice = VoiceSettings(voice_id="v1")
    program = make_program([Block(id="a", text="12345"), Block(id="b", text="1234567890")])
    assert plan_generation(program, voice, tmp_path).billable_chars == 15


def test_synthesis_block_is_included_in_the_plan(tmp_path: Path):
    voice = VoiceSettings(voice_id="v1")
    program = make_program([Block(id="a", text="One.")], synthesis=Block(id="coda", text="You."))
    plan = plan_generation(program, voice, tmp_path)
    assert {b.id for b, _ in plan.to_generate} == {"a", "coda"}


def test_sample_trims_to_the_first_n_in_program_order(tmp_path: Path):
    voice = VoiceSettings(voice_id="v1")
    program = make_program([Block(id=str(i), text=f"Line {i}.") for i in range(5)])

    plan = plan_generation(program, voice, tmp_path).sample(2)
    assert [b.id for b, _ in plan.to_generate] == ["0", "1"]
    assert plan.billable_chars == len("Line 0.") + len("Line 1.")


def test_sample_larger_than_the_plan_is_a_no_op(tmp_path: Path):
    voice = VoiceSettings(voice_id="v1")
    program = make_program([Block(id="a", text="One.")])
    full = plan_generation(program, voice, tmp_path)
    assert full.sample(10).to_generate == full.to_generate
    assert full.sample(None) is full


def test_sample_skips_cached_takes_rather_than_counting_them(tmp_path: Path):
    """A sample of 2 means two new generations, not two blocks — otherwise a
    partly-cached track would sample nothing."""
    voice = VoiceSettings(voice_id="v1")
    program = make_program([Block(id=str(i), text=f"Line {i}.") for i in range(4)])

    already = take_path(tmp_path, program, program.blocks[0], voice)
    already.parent.mkdir(parents=True, exist_ok=True)
    already.write_bytes(b"audio")

    plan = plan_generation(program, voice, tmp_path).sample(2)
    assert [b.id for b, _ in plan.to_generate] == ["1", "2"]


def test_parse_voices_extracts_id_name_and_labels():
    from selftalk.generate import parse_voices

    parsed = parse_voices(
        {
            "voices": [
                {
                    "voice_id": "abc123",
                    "name": "Paul",
                    "category": "premade",
                    "labels": {"accent": "american", "age": "middle-aged", "gender": "male"},
                }
            ]
        }
    )
    assert parsed == [
        {
            "voice_id": "abc123",
            "name": "Paul",
            "category": "premade",
            "labels": "american, middle-aged, male",
        }
    ]


def test_parse_voices_tolerates_missing_labels():
    from selftalk.generate import parse_voices

    parsed = parse_voices({"voices": [{"voice_id": "x", "name": "Bare"}]})
    assert parsed[0]["labels"] == ""


def test_parse_voices_rejects_an_unexpected_payload():
    from selftalk.generate import GenerationError, parse_voices

    import pytest

    with pytest.raises(GenerationError, match="no 'voices' list"):
        parse_voices({"error": "nope"})


def test_api_key_comes_from_dotenv_when_the_environment_is_empty(tmp_path: Path, monkeypatch):
    from selftalk.generate import resolve_api_key

    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comment\n\nexport ELEVENLABS_API_KEY='sk-from-dotenv'\n")
    assert resolve_api_key(dotenv_path=env) == "sk-from-dotenv"


def test_explicit_key_beats_the_environment_and_dotenv(tmp_path: Path, monkeypatch):
    from selftalk.generate import resolve_api_key

    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-from-env")
    env = tmp_path / ".env"
    env.write_text("ELEVENLABS_API_KEY=sk-from-dotenv\n")
    assert resolve_api_key("sk-explicit", dotenv_path=env) == "sk-explicit"
    assert resolve_api_key(dotenv_path=env) == "sk-from-env"


def test_missing_key_everywhere_is_a_clear_error(tmp_path: Path, monkeypatch):
    from selftalk.generate import GenerationError, resolve_api_key

    import pytest

    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(GenerationError, match="no API key"):
        resolve_api_key(dotenv_path=tmp_path / "absent")
