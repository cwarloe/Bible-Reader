import pytest

from selftalk.model import Block, ContentError, load_program


def test_audio_tags_are_not_spoken():
    block = Block(id="b", text="[calm, steady] You choose to grow. [pause] You achieve it.")
    assert block.spoken_text == "You choose to grow. You achieve it."
    assert block.word_count == 7


def test_pause_tags_are_counted_separately_from_tone_tags():
    block = Block(id="b", text="[deliberate emphasis] One. [pause] Two. [beat] Three.")
    assert block.pause_tag_count == 2


def test_char_count_includes_tags_because_elevenlabs_bills_them():
    block = Block(id="b", text="[calm] Hello.")
    assert block.char_count == len("[calm] Hello.")
    assert block.word_count == 1


def test_load_program_reads_blocks_and_synthesis(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text(
        "title: T\n"
        "track_type: daytime\n"
        "perspective: first_person\n"
        "blocks:\n"
        "  - id: one\n"
        "    text: I walk in love.\n"
        "synthesis:\n"
        "  id: coda\n"
        "  text: You walk in love.\n"
    )
    program = load_program(path)
    assert program.slug == "p"
    assert [b.id for b in program.all_blocks()] == ["one", "coda"]


@pytest.mark.parametrize(
    "body, expected",
    [
        ("title: T\ntrack_type: morning\n", "no blocks"),
        ("track_type: morning\nblocks: [{id: a, text: b}]\n", "missing required field 'title'"),
        ("title: T\ntrack_type: morning\nblocks:\n  - id: a\n", "missing required field"),
    ],
)
def test_unloadable_programs_raise_content_error(tmp_path, body, expected):
    path = tmp_path / "p.yaml"
    path.write_text(body)
    with pytest.raises(ContentError, match=expected):
        load_program(path)
