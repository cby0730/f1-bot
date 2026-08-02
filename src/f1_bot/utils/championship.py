"""Championship clinch math for /title — pure, DB-free, directly unit-testable.

Mirrors the other pure-logic utils (``utils/sessions.py``, ``utils/fuzzy_match.py``).
All /title math lives here so the formatters stay layout-only and the boundary cases
(magic-number-of-1, tie-stays-open) can be asserted on integers, not rendered strings.
"""

from dataclasses import dataclass

# F1 2025+ single-event maximum points (fastest-lap bonus removed).
WDC_RACE_MAX = 25
WDC_SPRINT_MAX = 8
WCC_RACE_MAX = 43  # 25 + 18, a 1-2 finish (both cars summed)
WCC_SPRINT_MAX = 15  # 8 + 7


def remaining_events(races: list, round_after: int) -> tuple[int, int]:
    """(remaining_races, remaining_sprints) for events after snapshot ``round_after``.

    ENUMERATES the races that actually exist and tests ``round > round_after`` on each —
    never ``total - round_after``. Immune to schedule gaps / non-contiguous rounds.
    ``races`` is get_schedule()'s list; each item has ``.round`` and ``.sprint``. Kept
    here (not in the formatter) so it is a pure, directly-testable function.
    """
    remaining = [r for r in races if r.round > round_after]
    return len(remaining), sum(1 for r in remaining if r.sprint is not None)


def max_remaining_points(
    remaining_races: int, remaining_sprints: int, race_max: int, sprint_max: int
) -> int:
    """Largest points total still winnable across all remaining events."""
    return remaining_races * race_max + remaining_sprints * sprint_max


@dataclass(frozen=True)
class ClinchStatus:
    clinched: bool  # leader is mathematically uncatchable by the chaser
    magic_number: int | None  # points leader still needs; None once clinched


def clinch_status(leader_pts: float, chaser_pts: float, max_remaining: int) -> ClinchStatus:
    """Points-only clinch test of leader vs. ONE chaser.

    Clinched iff  ``leader_pts > chaser_pts + max_remaining``  (STRICT; equality =>
    not clinched, the conservative choice — a tie is decided by count-back we do not
    model, so we never claim a title that count-back could still flip).

    magic_number = points the leader must still add to become uncatchable =
        ``(chaser_pts + max_remaining) - leader_pts + 1``
    Clamped to >= 0; reported only while not clinched.
    """
    if leader_pts > chaser_pts + max_remaining:
        return ClinchStatus(clinched=True, magic_number=None)
    gap = (chaser_pts + max_remaining) - leader_pts + 1
    return ClinchStatus(clinched=False, magic_number=max(0, int(gap)))
