"""Tests for driver profile and circuit info formatters."""

from f1_bot.formatting.messages import format_circuit_info, format_driver_profile
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit


def _driver(**kwargs):
    defaults = dict(
        driver_id="hamilton",
        given_name="Lewis",
        family_name="Hamilton",
        nationality="British",
        permanent_number="44",
        code="HAM",
        date_of_birth="1985-01-07",
        url="https://en.wikipedia.org/wiki/Lewis_Hamilton",
    )
    return Driver(**{**defaults, **kwargs})


def _standing(driver, pos=3, pts=150.0, wins=2):
    return DriverStanding(
        position=pos, points=pts, wins=wins, driver=driver, constructor_name="Mercedes"
    )


def _circuit(**kwargs):
    defaults = dict(
        circuit_id="monaco",
        name="Circuit de Monaco",
        locality="Monte-Carlo",
        country="Monaco",
        lat=43.7347,
        lng=7.4205,
        url="https://en.wikipedia.org/wiki/Circuit_de_Monaco",
    )
    return Circuit(**{**defaults, **kwargs})


# --- format_driver_profile ---


def test_driver_profile_shows_full_name():
    text = format_driver_profile(_driver())
    assert "Lewis Hamilton" in text


def test_driver_profile_shows_number_and_code():
    text = format_driver_profile(_driver())
    assert "44" in text
    assert "HAM" in text


def test_driver_profile_shows_nationality():
    text = format_driver_profile(_driver())
    assert "British" in text


def test_driver_profile_shows_standing_when_provided():
    d = _driver()
    text = format_driver_profile(d, _standing(d))
    assert "150" in text
    assert "2 wins" in text


def test_driver_profile_no_standing_still_renders():
    text = format_driver_profile(_driver(), standing=None)
    assert "Lewis Hamilton" in text
    assert "150" not in text


def test_driver_profile_shows_wikipedia_link():
    text = format_driver_profile(_driver())
    assert "Wikipedia" in text


# --- format_circuit_info ---


def test_circuit_info_shows_name_and_location():
    text = format_circuit_info(_circuit())
    assert "Circuit de Monaco" in text
    assert "Monte-Carlo" in text
    assert "Monaco" in text


def test_circuit_info_shows_coordinates():
    text = format_circuit_info(_circuit())
    assert "43.7" in text


def test_circuit_info_shows_wikipedia_link():
    text = format_circuit_info(_circuit())
    assert "Wikipedia" in text


def test_circuit_info_no_url_no_link():
    text = format_circuit_info(_circuit(url=None))
    assert "Wikipedia" not in text
