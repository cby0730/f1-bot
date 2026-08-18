"""Layout-contract tests for the clinch strip inside standings.

DB-free: build standings lists and pass PRE-COUNTED remaining ints directly.
Product scope is two lines under the header — remaining + magic-number OR
CLINCHED. Top-3 deficit rows and title.max_points are intentionally gone.
"""

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.messages import format_constructor_standings, format_driver_standings
from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding


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


def test_wdc_open_title_shows_magic_number_and_remaining():
    standings = _wdc_standings()
    text = format_driver_standings(standings, 2026, 10, 3, RenderContext())

    assert "10 races" in text and "3 sprints" in text
    assert "CLINCHED" not in text
    assert text.count("Magic number") == 1
    assert "Verstappen" in text
    # magic = (258 + 274) - 310 + 1 = 223
    assert "223" in text
    # product scope: no top-3 deficit rows, no max-points figure
    assert "−52" not in text
    assert "Max points" not in text


def test_wdc_clinched_shows_banner():
    standings = _wdc_standings()
    text = format_driver_standings(standings, 2026, 0, 0, RenderContext())

    assert "CLINCHED" in text
    assert "Verstappen" in text
    assert "Magic number" not in text


def test_wdc_lone_leader_is_clinched():
    standings = _wdc_standings()[:1]
    text = format_driver_standings(standings, 2026, 5, 0, RenderContext())
    assert "CLINCHED" in text
    assert "Verstappen" in text


def test_clinch_strip_escapes_markdown_in_names():
    """Names with '_' must be escaped — title.magic_number is italic."""
    standings = [
        DriverStanding(
            position=1,
            points=10.0,
            wins=0,
            driver=_driver("x", "Max", "Ver_stappen"),
            constructor_name="Red_Bull",
        ),
        DriverStanding(
            position=2,
            points=1.0,
            wins=0,
            driver=_driver("y", "Lando", "Norris"),
            constructor_name="McLaren",
        ),
    ]
    text = format_driver_standings(standings, 2026, 10, 0, RenderContext())
    assert r"Ver\_stappen" in text


def test_wcc_clinched_names_constructor_champion():
    standings = _wcc_standings()
    text = format_constructor_standings(standings, 2026, 0, 0, RenderContext())
    assert "CLINCHED" in text
    assert "McLaren" in text
    assert "Constructors'" in text
