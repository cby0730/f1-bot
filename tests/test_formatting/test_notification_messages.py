"""Tests for notification message formatting."""

from datetime import date, time

from f1_bot.formatting.messages import format_notification_message, format_reminders_list
from f1_bot.models.notification import NotificationSubscription
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


def test_format_reminders_list_empty():
    result = format_reminders_list([], [], "UTC")
    assert "no active reminders" in result.lower()


def test_format_reminders_list_grouped():
    from datetime import UTC, datetime

    races = [_race(10), _race(11)]
    object.__setattr__(races[1], "round", 11)
    object.__setattr__(races[1], "name", "Austrian Grand Prix")

    subs = [
        NotificationSubscription(
            id=1,
            telegram_id=100,
            season=2026,
            round=10,
            session_key="race",
            minutes_before=30,
            fire_at=datetime(2026, 7, 5, 13, 30, tzinfo=UTC),
        ),
        NotificationSubscription(
            id=2,
            telegram_id=100,
            season=2026,
            round=10,
            session_key="qualifying",
            minutes_before=60,
            fire_at=datetime(2026, 7, 4, 13, 0, tzinfo=UTC),
        ),
        NotificationSubscription(
            id=3,
            telegram_id=100,
            season=2026,
            round=11,
            session_key="race",
            minutes_before=15,
            fire_at=datetime(2026, 7, 12, 13, 45, tzinfo=UTC),
        ),
    ]

    result = format_reminders_list(subs, races, "UTC")
    assert "Active Reminders" in result
    assert "R10" in result
    assert "Race" in result
    assert "Qualifying" in result
