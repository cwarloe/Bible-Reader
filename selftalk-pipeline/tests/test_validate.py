from selftalk.config import Pacing
from selftalk.model import Block, Program
from selftalk.validate import has_errors, validate_program


def make_program(blocks, **kwargs):
    defaults = dict(
        slug="p",
        title="T",
        track_type="morning",
        perspective="second_person",
        blocks=blocks,
    )
    defaults.update(kwargs)
    return Program(**defaults)


def messages(program, pacing=None):
    return [f.message for f in validate_program(program, pacing or Pacing())]


def test_ssml_is_rejected_because_v3_may_read_it_aloud():
    program = make_program([Block(id="a", text='One. <break time="1.0s" /> Two.')])
    findings = validate_program(program, Pacing())
    assert has_errors(findings)
    assert any("SSML" in f.message for f in findings)


def test_pause_audio_tag_is_accepted():
    program = make_program([Block(id="a", text="One. [pause] Two.")])
    assert not has_errors(validate_program(program, Pacing()))


def test_block_over_the_generation_limit_is_an_error():
    program = make_program([Block(id="a", text="x" * 5001)])
    findings = validate_program(program, Pacing())
    assert has_errors(findings)
    assert any("single-generation limit" in f.message for f in findings)


def test_long_but_legal_block_is_only_a_warning():
    findings = validate_program(make_program([Block(id="a", text="x" * 3500)]), Pacing())
    assert not has_errors(findings)
    assert any("long single take" in f.message for f in findings)


def test_duplicate_block_ids_are_rejected():
    program = make_program([Block(id="a", text="One."), Block(id="a", text="Two.")])
    assert has_errors(validate_program(program, Pacing()))


def test_block_id_must_be_filename_safe():
    program = make_program([Block(id="Bad Id/../x", text="One.")])
    assert has_errors(validate_program(program, Pacing()))


def test_unknown_track_type_is_rejected():
    program = make_program([Block(id="a", text="One.")], track_type="afternoon")
    assert has_errors(validate_program(program, Pacing()))


def test_tag_only_block_has_nothing_to_say():
    findings = validate_program(make_program([Block(id="a", text="[calm]")]), Pacing())
    assert any("no spoken text" in f.message for f in findings)


def test_unbalanced_bracket_is_flagged():
    findings = validate_program(make_program([Block(id="a", text="[calm One.")]), Pacing())
    assert any("bracket" in f.message for f in findings)


def test_second_person_daytime_track_is_flagged_as_probable_mislabel():
    program = make_program(
        [Block(id="a", text="One.")],
        track_type="daytime",
        perspective="second_person",
    )
    assert any("first-person" in m for m in messages(program))


def test_track_far_from_its_target_is_flagged():
    program = make_program([Block(id="a", text="One.")], target_minutes=8)
    assert any("short of the 8-minute target" in m for m in messages(program))


def test_track_on_target_is_not_flagged():
    pacing = Pacing(repeat=1, words_per_minute=100, pause_block_ms=0)
    program = make_program(
        [Block(id="a", text=" ".join(["word"] * 800))],
        target_minutes=8,
    )
    assert not any("target" in m for m in messages(program, pacing))
