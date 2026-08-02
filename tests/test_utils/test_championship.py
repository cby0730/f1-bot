"""Tests for utils/championship.py — the clinch math, boundaries first (Rule 9).

The point of this suite is the *boundaries*: magic-number-of-1, the strict-tie rule,
and enumerate-not-subtract. Each asserts WHY the behaviour matters, not just a value.
"""

from dataclasses import dataclass

from f1_bot.utils.championship import (
    WCC_RACE_MAX,
    WCC_SPRINT_MAX,
    WDC_RACE_MAX,
    WDC_SPRINT_MAX,
    clinch_status,
    max_remaining_points,
    remaining_events,
)


@dataclass
class _FakeSprint:
    """Any non-None object satisfies `.sprint is not None`."""


@dataclass
class _FakeRace:
    round: int
    sprint: object | None = None


# ---------- max_remaining_points ----------


def test_max_remaining_points_race_only():
    assert max_remaining_points(3, 0, WDC_RACE_MAX, WDC_SPRINT_MAX) == 75


def test_max_remaining_points_sprint_only():
    assert max_remaining_points(0, 2, WDC_RACE_MAX, WDC_SPRINT_MAX) == 16


def test_max_remaining_points_mixed():
    # 10 races + 3 sprints, WDC: 10*25 + 3*8 = 274 (matches the spec's worked example)
    assert max_remaining_points(10, 3, WDC_RACE_MAX, WDC_SPRINT_MAX) == 274


def test_max_remaining_points_wcc_constants():
    # WCC ceilings are the two-car sums: 43 per race, 15 per sprint.
    assert max_remaining_points(2, 1, WCC_RACE_MAX, WCC_SPRINT_MAX) == 2 * 43 + 15


def test_max_remaining_points_zero_remaining():
    assert max_remaining_points(0, 0, WDC_RACE_MAX, WDC_SPRINT_MAX) == 0


# ---------- clinch_status ----------


def test_clinch_not_clinched_catchable():
    # Leader 100, chaser 80, 75 still available → chaser can reach 155 > 100.
    status = clinch_status(100, 80, 75)
    assert status.clinched is False
    # magic = (80 + 75) - 100 + 1 = 56
    assert status.magic_number == 56


def test_clinch_magic_number_of_one():
    """The off-by-one boundary — one point short of uncatchable.

    chaser 24 + max_remaining 75 = 99 (the ceiling). leader sitting exactly at 99 is
    NOT clinched (99 > 99 is False, the strict rule), and needs exactly one more point
    (100 > 99) to clinch → magic == 1. This is the single most important assertion.
    """
    status = clinch_status(99, 24, 75)
    assert status.clinched is False
    assert status.magic_number == 1


def test_clinch_exact_clinch():
    """Leader one point past the chaser's ceiling → clinched, magic None.

    chaser 24 + 75 = 99 (the ceiling); at leader 99 magic == 1 (off-by-one test).
    leader 100 (100 > 99) is the first clinched value.
    """
    status = clinch_status(100, 24, 75)
    assert status.clinched is True
    assert status.magic_number is None


def test_clinch_tie_stays_open():
    """Strict rule: leader_pts == chaser_pts + max_remaining → NOT clinched.

    We never over-claim a title that a count-back (unmodelled) could still flip.
    """
    status = clinch_status(100, 25, 75)  # 25 + 75 == 100
    assert status.clinched is False
    assert status.magic_number == 1  # needs 1 more to break the tie decisively


def test_clinch_season_over_leader_ahead():
    """max_remaining == 0 and leader ahead → clinched (the final-champion case)."""
    status = clinch_status(310, 258, 0)
    assert status.clinched is True
    assert status.magic_number is None


def test_clinch_season_over_dead_heat_stays_open():
    """Equal points, nothing left → strict rule keeps it open (rare, safe)."""
    status = clinch_status(300, 300, 0)
    assert status.clinched is False


# ---------- remaining_events ----------


def test_remaining_events_basic():
    races = [
        _FakeRace(round=1),
        _FakeRace(round=2, sprint=_FakeSprint()),
        _FakeRace(round=3),
        _FakeRace(round=4, sprint=_FakeSprint()),
        _FakeRace(round=5),
    ]
    # After round 2: rounds 3,4,5 remain (3 races); only round 4 has a sprint.
    assert remaining_events(races, 2) == (3, 1)


def test_remaining_events_enumerate_not_subtract():
    """The desync guard: a schedule with a GAP must be enumerated, not subtracted.

    Rounds [1,2,3,7] (4-6 not in the DB) with round_after=3 → exactly ONE remaining
    (round 7). A `max_round - N` subtraction would give 7-3 = 4, which is wrong. This
    assertion forbids the subtraction shortcut.
    """
    races = [
        _FakeRace(round=1),
        _FakeRace(round=2),
        _FakeRace(round=3),
        _FakeRace(round=7),
    ]
    assert remaining_events(races, 3) == (1, 0)


def test_remaining_events_round_after_zero():
    """round_after=0 → the whole schedule remains (season-start snapshot)."""
    races = [_FakeRace(round=1, sprint=_FakeSprint()), _FakeRace(round=2)]
    assert remaining_events(races, 0) == (2, 1)


def test_remaining_events_season_over():
    """No race with round > N → (0, 0)."""
    races = [_FakeRace(round=1), _FakeRace(round=2)]
    assert remaining_events(races, 2) == (0, 0)
