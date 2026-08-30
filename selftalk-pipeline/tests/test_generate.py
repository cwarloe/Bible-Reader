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
