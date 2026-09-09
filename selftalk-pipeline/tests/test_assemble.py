from selftalk.assemble import plan_layout
from selftalk.config import Pacing
from selftalk.model import Block, Program


def make_program(blocks, synthesis=None, track_type="daytime"):
    return Program(
        slug="p",
        title="T",
        track_type=track_type,
        perspective="first_person",
        blocks=blocks,
        synthesis=synthesis,
    )


def test_daytime_layout_repeats_each_block():
    program = make_program([Block(id="a", text="One."), Block(id="b", text="Two.")])
    pacing = Pacing(repeat=3, pause_repeat_ms=1100, pause_block_ms=2200)
    assert plan_layout(program, pacing) == [
        ("a", 3, 1100, 2200),
        ("b", 3, 1100, 2200),
    ]


def test_morning_layout_speaks_each_block_once():
    program = make_program([Block(id="a", text="One.")], track_type="morning")
    pacing = Pacing(repeat=1, pause_repeat_ms=0, pause_block_ms=1200)
    assert plan_layout(program, pacing) == [("a", 1, 0, 1200)]


def test_synthesis_is_spoken_once_after_a_transition_pause():
    program = make_program([Block(id="a", text="One.")], synthesis=Block(id="coda", text="You."))
    pacing = Pacing(repeat=3, pause_repeat_ms=1100, pause_block_ms=2200, pause_transition_ms=3500)
    layout = plan_layout(program, pacing)
    # The gap before the coda replaces the previous block's ordinary trailing gap.
    assert layout == [("a", 3, 1100, 3500), ("coda", 1, 0, 0)]


def test_per_block_overrides_survive_into_the_layout():
    program = make_program([Block(id="a", text="One.", repeat=1, pause_after_ms=500)])
    layout = plan_layout(program, Pacing(repeat=3, pause_block_ms=2200))
    assert layout == [("a", 1, 0, 500)]


def total_silence_in_layout(layout):
    return sum((repeat - 1) * gap + trailing for _, repeat, gap, trailing in layout)


def test_estimator_and_assembler_agree_on_the_silence_budget():
    """The estimator predicts runtime; the assembler produces it. If these two
    ever disagree about silence, `stats` starts lying about the finished track."""
    from selftalk.estimate import estimate_program

    program = make_program(
        [
            Block(id="intro", text="One.", repeat=1),
            Block(id="a", text="Two."),
            Block(id="b", text="Three.", pause_after_ms=400),
        ],
        synthesis=Block(id="coda", text="You."),
    )
    pacing = Pacing(repeat=3, pause_repeat_ms=1100, pause_block_ms=2200,
                    pause_transition_ms=3500, pause_tag_ms=0)

    assert estimate_program(program, pacing).silence_ms == total_silence_in_layout(
        plan_layout(program, pacing)
    )
