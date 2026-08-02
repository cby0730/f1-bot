"""Layout-contract tests for format_title_wdc / format_title_wcc.

DB-free: build standings lists and pass PRE-COUNTED remaining ints directly (no
bounds, no schedule). Assert the structural contract from spec 004, not exact glyphs:
(a) title line, (b) round-progress line with remaining race & sprint counts,
(c) max-points figure, (d) CLINCHED banner naming leader OR one magic-number line,
(e) up to three ranked rows.
"""

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.messages import format_title_wcc, format_title_wdc
from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.utils.championship import (
    WCC_RACE_MAX,
    WDC_RACE_MAX,
    WDC_SPRINT_MAX,
    max_remaining_points,
)


def _driver(did, given, family, nat="British"):
    return Driver(driver_id=did, given_name=given, family_name=family, nationality=nat)


def _wdc_standings():
    return [
        DriverStanding(
            position=1,
            points=310.0,
            wins=9,
            driver=_driver("verstappen", "Max", "Verstappen", "Dutch"),
            constructor_name="Red Bull",
        ),
        DriverStanding(
            position=2,
            points=258.0,
            wins=4,
            driver=_driver("norris", "Lando", "Norris"),
            constructor_name="McLaren",
        ),
        DriverStanding(
            position=3,
            points=221.0,
            wins=2,
            driver=_driver("leclerc", "Charles", "Leclerc", "Monegasque"),
            constructor_name="Ferrari",
        ),
    ]


def _wcc_standings():
    return [
        ConstructorStanding(
            position=1,
            points=500.0,
            wins=10,
            constructor=Constructor(constructor_id="mclaren", name="McLaren"),
        ),
        ConstructorStanding(
            position=2,
            points=480.0,
            wins=8,
            constructor=Constructor(constructor_id="ferrari", name="Ferrari"),
        ),
    ]


# ---------- WDC ----------


def test_wdc_open_title_contract():
    standings = _wdc_standings()
    text = format_title_wdc(standings, remaining_races=10, remaining_sprints=3, season=2026, ctx=RenderContext())

    # (a) title line, (b) remaining counts present
    assert "WDC" in text
    assert "10 races" in text and "3 sprints" in text
    # (c) max-points figure equals the pure function
    expected_max = max_remaining_points(10, 3, WDC_RACE_MAX, WDC_SPRINT_MAX)
    assert str(expected_max) in text  # 274
    # (d) still open → exactly one magic-number line, no CLINCHED banner
    assert "CLINCHED" not in text
    assert text.count("Magic number") == 1
    assert "Verstappen" in text  # leader named in the magic-number line
    # (e) chaser rows show the deficit to the leader (310-258=52, 310-221=89)
    assert "−52" in text
    assert "−89" in text


def test_wdc_clinched_contract():
    standings = _wdc_standings()
    # Nothing left → leader (310) uncatchable by 258 → clinched.
    text = format_title_wdc(
        standings, remaining_races=0, remaining_sprints=0, season=2026, ctx=RenderContext()
    )

    assert "CLINCHED" in text
    assert "Verstappen" in text
    assert "Magic number" not in text  # no magic line once clinched


def test_wdc_open_title_magic_number_value():
    """The magic number is leader-vs-runner-up, computed once. 310 vs 258, 274 left:
    magic = (258 + 274) - 310 + 1 = 223."""
    standings = _wdc_standings()
    text = format_title_wdc(standings, remaining_races=10, remaining_sprints=3, season=2026, ctx=RenderContext())
    assert "223" in text


def test_wdc_lone_leader_is_clinched():
    """Degenerate 1-competitor table: nobody can catch a lone leader → clinched, no crash."""
    standings = _wdc_standings()[:1]
    text = format_title_wdc(
        standings, remaining_races=5, remaining_sprints=0, season=2026, ctx=RenderContext()
    )
    assert "CLINCHED" in text
    assert "Verstappen" in text


def test_wdc_points_render_whole_numbers():
    """Points round-trip through :.0f (no trailing .0)."""
    standings = _wdc_standings()
    text = format_title_wdc(
        standings, remaining_races=2, remaining_sprints=0, season=2026, ctx=RenderContext()
    )
    assert "310.0" not in text
    assert "310 pts" in text


def test_wdc_empty_standings_no_data():
    assert "No standings" in format_title_wdc(
        [], 5, 1, 2026, RenderContext()
    ) or "⚠️" in format_title_wdc([], 5, 1, 2026, RenderContext())


# ---------- WCC ----------


def test_wcc_uses_constructor_names_and_constants():
    standings = _wcc_standings()
    text = format_title_wcc(
        standings, remaining_races=3, remaining_sprints=0, season=2026, ctx=RenderContext()
    )

    # constructor names, not driver names
    assert "McLaren" in text
    assert "Ferrari" in text
    assert "🏭" in text
    # WCC race constant wired (43, not the WDC 25): 3 races → 129, not 75.
    assert str(3 * WCC_RACE_MAX) in text  # 129
    assert str(3 * WDC_RACE_MAX) not in text  # 75 must NOT be the figure


def test_wcc_clinched_names_constructor_champion():
    standings = _wcc_standings()
    # Leader 500 vs 480, nothing left → clinched.
    text = format_title_wcc(
        standings, remaining_races=0, remaining_sprints=0, season=2026, ctx=RenderContext()
    )
    assert "CLINCHED" in text
    assert "McLaren" in text
    assert "Constructors'" in text
