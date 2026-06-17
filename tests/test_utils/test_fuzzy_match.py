"""Tests for fuzzy_match utilities."""

from f1_bot.models.driver import Driver
from f1_bot.models.race import Circuit
from f1_bot.utils.fuzzy_match import best_match, match_circuit, match_driver


def _driver(driver_id, given, family, code=None, number=None):
    return Driver(
        driver_id=driver_id,
        given_name=given,
        family_name=family,
        code=code,
        permanent_number=number,
    )


def _circuit(circuit_id, name, locality, country):
    return Circuit(circuit_id=circuit_id, name=name, locality=locality, country=country)


DRIVERS = [
    _driver("hamilton", "Lewis", "Hamilton", code="HAM", number="44"),
    _driver("max_verstappen", "Max", "Verstappen", code="VER", number="1"),
    _driver("leclerc", "Charles", "Leclerc", code="LEC", number="16"),
    _driver("norris", "Lando", "Norris", code="NOR", number="4"),
]

CIRCUITS = [
    _circuit("monaco", "Circuit de Monaco", "Monte-Carlo", "Monaco"),
    _circuit("monza", "Autodromo Nazionale di Monza", "Monza", "Italy"),
    _circuit("silverstone", "Silverstone Circuit", "Silverstone", "UK"),
    _circuit("spa", "Circuit de Spa-Francorchamps", "Stavelot", "Belgium"),
]


# --- best_match ---


def test_best_match_exact_field():
    result = best_match("Hamilton", DRIVERS, [lambda d: d.family_name])
    assert result is not None
    assert result.driver_id == "hamilton"


def test_best_match_returns_none_below_threshold():
    result = best_match("xyz123", DRIVERS, [lambda d: d.family_name])
    assert result is None


def test_best_match_empty_list():
    assert best_match("anything", [], [lambda d: d]) is None


# --- match_driver ---


def test_match_driver_by_family_name():
    assert match_driver("hamilton", DRIVERS).driver_id == "hamilton"


def test_match_driver_case_insensitive():
    assert match_driver("VERSTAPPEN", DRIVERS).driver_id == "max_verstappen"


def test_match_driver_by_three_letter_code():
    assert match_driver("LEC", DRIVERS).driver_id == "leclerc"


def test_match_driver_partial_name():
    # "norr" is close enough to "Norris"
    result = match_driver("norr", DRIVERS)
    assert result is not None
    assert result.driver_id == "norris"


def test_match_driver_by_number():
    assert match_driver("44", DRIVERS).driver_id == "hamilton"


def test_match_driver_no_match_returns_none():
    assert match_driver("zzzunknown", DRIVERS) is None


# --- match_circuit ---


def test_match_circuit_by_locality():
    assert match_circuit("monaco", CIRCUITS).circuit_id == "monaco"


def test_match_circuit_by_country():
    result = match_circuit("belgium", CIRCUITS)
    assert result is not None
    assert result.circuit_id == "spa"


def test_match_circuit_by_partial_name():
    result = match_circuit("silverstone", CIRCUITS)
    assert result is not None
    assert result.circuit_id == "silverstone"


def test_match_circuit_no_match_returns_none():
    assert match_circuit("zzzunknown", CIRCUITS) is None
