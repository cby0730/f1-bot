from datetime import UTC, date, datetime, time

from f1_bot.models.race import Circuit, Race, RaceSession, Session
from f1_bot.utils.sessions import (
    find_next_session,
    find_next_sessions,
    find_race_session,
    find_recent_completed_session,
    find_recent_completed_sessions,
    match_openf1_session,
    normalize_session_key,
    session_entries,
)


def _circuit():
    return Circuit(circuit_id="monza", name="Monza", locality="Monza", country="Italy")


def _race():
    return Race(
        season=2024,
        round=16,
        name="Italian Grand Prix",
        circuit=_circuit(),
        date=date(2024, 9, 1),
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=date(2024, 8, 30), time=time(11, 30)),
        fp2=RaceSession(name="FP2", date=date(2024, 8, 30), time=time(15, 0)),
        fp3=RaceSession(name="FP3", date=date(2024, 8, 31), time=time(10, 30)),
        qualifying=RaceSession(name="Qualifying", date=date(2024, 8, 31), time=time(14, 0)),
    )


def test_find_next_session_returns_next_any_session():
    now = datetime(2024, 8, 30, 12, 0, tzinfo=UTC)

    entry = find_next_session([_race()], now=now)

    assert entry is not None
    assert entry.key == "fp2"


def test_find_next_qualifying_includes_qualifying_sessions():
    now = datetime(2024, 8, 30, 12, 0, tzinfo=UTC)

    entry = find_next_session([_race()], group="qualifying", now=now)

    assert entry is not None
    assert entry.key == "qualifying"


def test_find_recent_completed_session_can_filter_by_alias():
    now = datetime(2024, 8, 31, 16, 0, tzinfo=UTC)

    entry = find_recent_completed_session([_race()], "quali", now=now)

    assert entry is not None
    assert entry.key == "qualifying"


def test_find_race_session_resolves_round_and_session_alias():
    entry = find_race_session([_race()], 16, "fp3")

    assert entry is not None
    assert entry.label == "FP3"


def test_match_openf1_session_uses_date_and_session_name():
    entry = find_race_session([_race()], 16, "fp1")
    sessions = [
        Session(
            session_key=123,
            session_name="Practice 1",
            session_type="Practice",
            meeting_key=99,
            date_start="2024-08-30T11:30:00+00:00",
            year=2024,
        )
    ]

    match = match_openf1_session(entry, sessions)

    assert match is not None
    assert match.session_key == 123


def test_find_next_sessions_limit():
    now = datetime(2024, 8, 30, 10, 0, tzinfo=UTC)
    entries = find_next_sessions([_race()], limit=3, now=now)
    assert len(entries) == 3
    assert entries[0].key == "fp1"
    assert entries[1].key == "fp2"
    assert entries[2].key == "fp3"


def test_find_recent_completed_sessions_limit():
    now = datetime(2024, 8, 31, 16, 0, tzinfo=UTC)
    entries = find_recent_completed_sessions([_race()], limit=3, now=now)
    # completed in past: fp1, fp2, fp3, qualifying (since it is 16:00, fp3 at 10:30 and quali at 14:00 are completed)
    # ordered newest first: qualifying, fp3, fp2
    assert len(entries) == 3
    assert entries[0].key == "qualifying"
    assert entries[1].key == "fp3"
    assert entries[2].key == "fp2"


# ---------------------------------------------------------------------------
# normalize_session_key
# ---------------------------------------------------------------------------



def test_normalize_session_key_race():
    assert normalize_session_key("race") == "race"


def test_normalize_session_key_alias_sq():
    assert normalize_session_key("sq") == "sprint_qualifying"


def test_normalize_session_key_alias_sprintshootout():
    assert normalize_session_key("sprintshootout") == "sprint_qualifying"


def test_normalize_session_key_fp1():
    assert normalize_session_key("fp1") == "fp1"


def test_normalize_session_key_unknown_returns_none():
    assert normalize_session_key("unknown") is None


def test_normalize_session_key_none_returns_none():
    assert normalize_session_key(None) is None


def test_normalize_session_key_case_insensitive():
    assert normalize_session_key("RACE") == "race"
    assert normalize_session_key("Qualifying") == "qualifying"


def test_normalize_session_key_strips_separators():
    """Underscores, hyphens, spaces are stripped before lookup."""
    assert normalize_session_key("sprint_qualifying") == "sprint_qualifying"
    assert normalize_session_key("sprint-qualifying") == "sprint_qualifying"
    assert normalize_session_key("sprint qualifying") == "sprint_qualifying"


# ---------------------------------------------------------------------------
# session_entries — degenerate cases
# ---------------------------------------------------------------------------


def test_session_entries_empty_races_returns_empty():
    assert session_entries([]) == []


def test_session_entries_race_with_all_none_sessions():
    """A race with no optional sessions still produces at least the race entry."""
    race = Race(
        season=2024,
        round=1,
        name="Test GP",
        circuit=_circuit(),
        date=date(2024, 3, 1),
        time=time(13, 0),
        # All optional sessions are None by default
    )
    entries = session_entries([race])
    # Should have at least the mandatory "race" entry
    keys = [e.key for e in entries]
    assert "race" in keys
    # fp1, fp2, fp3 etc should NOT be present
    assert "fp1" not in keys
    assert "fp2" not in keys
    assert "fp3" not in keys
