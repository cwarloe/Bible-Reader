from selftalk.config import Pacing
from selftalk.estimate import estimate_block, estimate_program, format_duration, words_needed_for
from selftalk.model import Block, Program


def test_speech_time_follows_words_per_minute():
    block = Block(id="b", text=" ".join(["word"] * 105))
    pacing = Pacing(repeat=1, words_per_minute=105, pause_block_ms=0)
    assert estimate_block(block, pacing).speech_ms == 60_000


def test_triplication_triples_speech_and_adds_two_gaps():
    block = Block(id="b", text=" ".join(["word"] * 105))
    pacing = Pacing(repeat=3, pause_repeat_ms=1000, pause_block_ms=2000, words_per_minute=105)
    estimate = estimate_block(block, pacing)
    assert estimate.speech_ms == 180_000
    # Two gaps between three repeats, plus the trailing block gap.
    assert estimate.silence_ms == 2 * 1000 + 2000


def test_block_level_repeat_overrides_the_track_default():
    block = Block(id="b", text="one two three", repeat=1)
    pacing = Pacing(repeat=3, words_per_minute=105, pause_block_ms=0, pause_repeat_ms=999)
    estimate = estimate_block(block, pacing)
    assert estimate.repeat == 1
    assert estimate.silence_ms == 0


def test_pause_after_ms_overrides_the_track_gap():
    block = Block(id="b", text="one", pause_after_ms=50)
    pacing = Pacing(repeat=1, pause_block_ms=9999, words_per_minute=105)
    assert estimate_block(block, pacing).silence_ms == 50


def test_inline_pause_tags_add_silence_on_every_repeat():
    block = Block(id="b", text="one [pause] two")
    pacing = Pacing(repeat=2, pause_tag_ms=500, pause_repeat_ms=0, pause_block_ms=0)
    assert estimate_block(block, pacing).silence_ms == 2 * 500


def test_synthesis_is_spoken_once_and_gets_a_transition_pause():
    words = " ".join(["word"] * 105)
    program = Program(
        slug="p",
        title="T",
        track_type="daytime",
        perspective="first_person",
        blocks=[Block(id="a", text=words)],
        synthesis=Block(id="coda", text=words),
    )
    pacing = Pacing(repeat=3, pause_repeat_ms=0, pause_block_ms=0,
                    pause_transition_ms=3000, words_per_minute=105)
    estimate = estimate_program(program, pacing)
    # Three passes of the drill block, one of the coda.
    assert estimate.speech_ms == 4 * 60_000
    assert estimate.silence_ms == 3000


def test_words_needed_accounts_for_the_silence_budget():
    pacing = Pacing(words_per_minute=100)
    assert words_needed_for(8, pacing, silence_ms=0) == 800
    assert words_needed_for(8, pacing, silence_ms=60_000) == 700


def test_format_duration_rounds_to_the_nearest_second():
    assert format_duration(61_400) == "1m 01s"
