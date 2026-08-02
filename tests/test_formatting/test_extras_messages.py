"""Tests for driver profile and circuit info formatters."""

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.emoji import circuit_flag_icon
from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import (
    _CMP_LABEL_WIDTH,
    _display_width,
    _pad_display,
    format_circuit_info,
    format_driver_profile,
)
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
    text = format_driver_profile(_driver(), None, RenderContext())
    assert "Lewis Hamilton" in text


def test_driver_profile_shows_number_and_code():
    text = format_driver_profile(_driver(), None, RenderContext())
    assert "44" in text
    assert "HAM" in text


def test_driver_profile_shows_nationality():
    text = format_driver_profile(_driver(), None, RenderContext())
    assert "British" in text


def test_driver_profile_shows_standing_when_provided():
    d = _driver()
    text = format_driver_profile(d, _standing(d), RenderContext())
    assert "150" in text
    assert "2 wins" in text


def test_driver_profile_no_standing_still_renders():
    text = format_driver_profile(_driver(), standing=None, ctx=RenderContext())
    assert "Lewis Hamilton" in text
    assert "150" not in text


def test_driver_profile_shows_wikipedia_link():
    text = format_driver_profile(_driver(), None, RenderContext())
    assert "Wikipedia" in text


# --- format_circuit_info ---


def test_circuit_info_shows_name_and_location():
    text = format_circuit_info(_circuit(), None, RenderContext())
    assert "Circuit de Monaco" in text
    assert "Monte-Carlo" in text
    assert "Monaco" in text


def test_circuit_info_shows_coordinates():
    text = format_circuit_info(_circuit(), None, RenderContext())
    assert "43.7" in text


def test_circuit_info_shows_wikipedia_link():
    text = format_circuit_info(_circuit(), None, RenderContext())
    assert "Wikipedia" in text


def test_circuit_info_no_url_no_link():
    text = format_circuit_info(_circuit(url=None), None, RenderContext())
    assert "Wikipedia" not in text


def test_driver_profile_escapes_parentheses_in_url():
    d = _driver(url="http://en.wikipedia.org/wiki/George_Russell_(racing_driver)")
    text = format_driver_profile(d, None, RenderContext())
    assert "George_Russell_%28racing_driver%29" in text


def test_circuit_info_escapes_parentheses_in_url():
    c = _circuit(url="http://en.wikipedia.org/wiki/George_Russell_(racing_driver)")
    text = format_circuit_info(c, None, RenderContext())
    assert "George_Russell_%28racing_driver%29" in text


def test_circuit_flag_icon_specific_mappings():
    assert circuit_flag_icon("UK") == "🇬🇧"
    assert circuit_flag_icon("USA") == "🇺🇸"
    assert circuit_flag_icon("UAE") == "🇦🇪"
    assert circuit_flag_icon("Monaco") == "🇲🇨"
    assert circuit_flag_icon("UnknownCountryString") == "🏴"


def test_circuit_flag_icon_no_fallbacks():
    # Test all known countries in CIRCUIT_COUNTRY_TO_ISO3 mapping do not resolve to 🏴
    from f1_bot.formatting.emoji import CIRCUIT_COUNTRY_TO_ISO3

    for country in CIRCUIT_COUNTRY_TO_ISO3:
        flag = circuit_flag_icon(country)
        assert flag != "🏴", f"Country '{country}' fell back to black flag 🏴"


# --- /compare CJK monospace alignment (spec 005) ---
#
# The /compare grid renders inside a Telegram monospace block. Alignment of the
# "─" separators depends on padding to *display columns*, not code points: a CJK
# glyph advances two monospace columns, a Latin letter one. These tests pin that
# contract so a revert to code-point padding ({label:<N}) — which under-pads every
# CJK label by one space per glyph — fails loudly.

# The label keys rendered down the left column of the /compare grid, in render order.
_COMPARE_LABEL_KEYS = (
    "compare.row_points",
    "compare.row_quali",
    "compare.row_race",
    "compare.row_wins",
    "compare.row_podiums",
    "compare.row_dnfs",
)


def test_display_width_counts_cjk_as_two_columns():
    """A CJK glyph is two monospace columns; a Latin letter is one.

    This is the invariant every /compare alignment assertion below rests on. If
    _display_width regressed to len() (code points), '積分' would read as 2, not 4,
    and the padded value columns would drift by two spaces.
    """
    assert _display_width("積分") == 4
    assert _display_width("Points") == 6


def test_compare_labels_pad_to_same_display_column_across_languages():
    """Each zh-Hant label must pad to the SAME display column as its en counterpart.

    WHY: the value column ("  a ─ b") starts immediately after the padded label, so
    if the padded en and zh labels ended at different display columns the "─"
    separators would not line up between an English and a Chinese screenshot.
    Reverting _pad_display to code-point padding ('{label:<N}') pads CJK to N code
    points — a display width of N + (extra columns per wide glyph) — so the zh side
    would exceed _CMP_LABEL_WIDTH and this equality would break.
    """
    for key in _COMPARE_LABEL_KEYS:
        en = _pad_display(t(key, "en"), _CMP_LABEL_WIDTH)
        zh = _pad_display(t(key, "zh-Hant"), _CMP_LABEL_WIDTH)
        assert _display_width(en) == _CMP_LABEL_WIDTH, key
        assert _display_width(zh) == _CMP_LABEL_WIDTH, key


def test_compare_label_width_covers_widest_shipped_label():
    """_CMP_LABEL_WIDTH must be >= the widest shipped label's display width.

    If a label were wider than the target column it would overflow (_pad_display
    adds no padding), pushing that one row's numbers right and breaking the grid.
    Computed from the live catalog so adding a longer label in either language
    fails here until _CMP_LABEL_WIDTH is bumped.
    """
    widest = max(
        _display_width(t(key, lang))
        for key in _COMPARE_LABEL_KEYS
        for lang in ("en", "zh-Hant")
    )
    assert _CMP_LABEL_WIDTH >= widest
