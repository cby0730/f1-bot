"""Tests for notification message formatting."""

from datetime import date, time

from f1_bot.formatting.messages import format_notification_message
from f1_bot.models.race import Circuit, Race


def _race(round_num: int = 10) -> Race:
    return Race(
        season=2026,
        round=round_num,
        name="British Grand Prix",
        circuit=Circuit(
            circuit_id="silverstone", name="Silverstone", locality="Silverstone", country="UK"
        ),
        date=date(2026, 7, 5),
        time=time(14, 0),
    )


def test_format_notification_message_with_race():
    race = _race()
    msg = format_notification_message(race, "race", 30)
    assert "British Grand Prix" in msg
    assert "Race" in msg
    assert "30 minutes" in msg
    assert "🔔" in msg


def test_format_notification_message_without_race():
    msg = format_notification_message(None, "qualifying", 60)
    assert "Qualifying" in msg
    assert "60 minutes" in msg
