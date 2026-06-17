"""Tests for timezone utilities — conversion, countdown, validation."""

from datetime import UTC, date, datetime, time

from f1_bot.formatting.timezone import (
    combine_race_dt,
    format_countdown,
    format_dt,
    is_valid_timezone,
)


def test_is_valid_timezone_accepts_iana():
    assert is_valid_timezone("Asia/Taipei")
    assert is_valid_timezone("Europe/London")
    assert is_valid_timezone("UTC")


def test_is_valid_timezone_rejects_garbage():
    assert not is_valid_timezone("Mars/Olympus")
    assert not is_valid_timezone("not-a-tz")


def test_combine_race_dt_with_time():
    dt = combine_race_dt(date(2024, 5, 26), time(13, 0, 0))
    assert dt == datetime(2024, 5, 26, 13, 0, 0, tzinfo=UTC)


def test_combine_race_dt_without_time():
    dt = combine_race_dt(date(2024, 5, 26), None)
    assert dt.year == 2024 and dt.month == 5 and dt.day == 26
    assert dt.tzinfo is not None


def test_format_dt_converts_timezone():
    utc_dt = datetime(2024, 5, 26, 13, 0, 0, tzinfo=UTC)
    result = format_dt(utc_dt, "Asia/Taipei")
    # UTC+8 means 13:00 UTC = 21:00 Taipei
    assert "21:00" in result
    assert "CST" in result or "Taipei" in result or "+" in result


def test_format_dt_utc_unchanged():
    utc_dt = datetime(2024, 5, 26, 13, 0, 0, tzinfo=UTC)
    result = format_dt(utc_dt, "UTC")
    assert "13:00" in result


def test_format_countdown_future():
    future = datetime(2099, 1, 1, tzinfo=UTC)
    result = format_countdown(future)
    assert "d" in result  # shows days
    assert "In progress" not in result


def test_format_countdown_past():
    past = datetime(2000, 1, 1, tzinfo=UTC)
    result = format_countdown(past)
    assert result == "In progress / finished"


def test_format_countdown_just_hours():
    from datetime import timedelta

    # Use a large minute value so rounding can't drop it to 0
    target = datetime.now(tz=UTC) + timedelta(hours=3, minutes=45)
    result = format_countdown(target)
    # At least the hour component must appear
    assert "3h" in result or "4h" in result  # boundary tolerance
    assert "m" in result  # minutes component present when no days
