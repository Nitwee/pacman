"""Tests for the Animation playback class."""

from graphics.animation import Animation
from graphics.assets import AnimationDef


def _three_frame_loop() -> AnimationDef:
    return AnimationDef(
        frames=("a", "b", "c"),
        frame_duration_ms=100,
        loop=True,
    )


def _three_frame_oneshot() -> AnimationDef:
    return AnimationDef(
        frames=("a", "b", "c"),
        frame_duration_ms=100,
        loop=False,
    )


def test_starts_on_first_frame() -> None:
    anim = Animation(_three_frame_loop())
    assert anim.current_frame() == "a"
    assert anim.finished is False


def test_advance_one_frame() -> None:
    anim = Animation(_three_frame_loop())
    anim.update(100)
    assert anim.current_frame() == "b"


def test_partial_dt_keeps_current_frame() -> None:
    anim = Animation(_three_frame_loop())
    anim.update(40)
    anim.update(40)
    assert anim.current_frame() == "a"
    anim.update(40)  # cumulative 120ms >= 100 → advance
    assert anim.current_frame() == "b"


def test_multi_frame_jump_when_dt_exceeds_budget() -> None:
    anim = Animation(_three_frame_loop())
    anim.update(250)  # = 2 frames + 50ms leftover
    assert anim.current_frame() == "c"


def test_loop_wraps_to_start() -> None:
    anim = Animation(_three_frame_loop())
    anim.update(300)  # exactly one full cycle
    assert anim.current_frame() == "a"


def test_oneshot_holds_last_frame() -> None:
    anim = Animation(_three_frame_oneshot())
    anim.update(1000)  # well past the end
    assert anim.current_frame() == "c"
    assert anim.finished is True


def test_finished_true_only_for_oneshot_at_end() -> None:
    looping = Animation(_three_frame_loop())
    looping.update(1000)
    assert looping.finished is False
    oneshot = Animation(_three_frame_oneshot())
    assert oneshot.finished is False
    oneshot.update(200)
    assert oneshot.finished is True


def test_update_after_finished_is_noop() -> None:
    anim = Animation(_three_frame_oneshot())
    anim.update(1000)
    anim.update(1000)
    assert anim.current_frame() == "c"


def test_reset_restarts_from_zero() -> None:
    anim = Animation(_three_frame_loop())
    anim.update(250)
    anim.reset()
    assert anim.current_frame() == "a"
    anim.update(50)  # elapsed counter cleared, no advance
    assert anim.current_frame() == "a"


def test_two_instances_are_independent() -> None:
    """Two entities playing the same anim keep their own clocks."""
    definition = _three_frame_loop()
    a = Animation(definition)
    b = Animation(definition)
    a.update(150)
    assert a.current_frame() == "b"
    assert b.current_frame() == "a"
