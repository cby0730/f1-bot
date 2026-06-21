"""Tests for scheduler sync functions — verify each sync function calls the right API methods and saves to repo."""

import datetime as dt
from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit, Race, RaceSession
from f1_bot.models.results import SessionResult
from f1_bot.scheduler.jobs import (
    _LIVE_WINDOW_MARGIN,
    _is_in_live_window,
    hourly_sync,
    sync_drivers_and_circuits,
    sync_openf1_laps,
    sync_openf1_session_results,
    sync_pitstops_window,
    sync_results_window,
    sync_schedule,
    sync_standings,
)


def _sample_race():
    circuit = Circuit(
        circuit_id="monza", name="Autodromo Nazionale Monza", locality="Monza", country="Italy"
    )
    return Race(
        season=2024,
        round=3,
        name="Italian Grand Prix",
        circuit=circuit,
        date=date(2024, 9, 1),
        time=time(13, 0, 0),
    )


def _sample_driver_standings():
    driver = Driver(
        driver_id="hamilton", given_name="Lewis", family_name="Hamilton", nationality="British"
    )
    return [
        DriverStanding(position=1, points=100, wins=2, driver=driver, constructor_name="Mercedes")
    ]


def _sample_constructor_standings():
    constructor = Constructor(constructor_id="mercedes", name="Mercedes", nationality="German")
    return [ConstructorStanding(position=1, points=200, wins=4, constructor=constructor)]


# --- sync_schedule ---


async def test_sync_schedule_saves_races():
    race = _sample_race()
    jolpica = MagicMock()
    jolpica.get_current_schedule = AsyncMock(return_value=[race])
    repo = MagicMock()
    repo.save_schedule = AsyncMock()
    repo.set_sync_metadata = AsyncMock()

    result = await sync_schedule(jolpica, repo)

    jolpica.get_current_schedule.assert_awaited_once()
    # race.season=2024, today().year=2026 — saved under both keys
    assert repo.save_schedule.await_count == 2
    repo.save_schedule.assert_any_await(2024, [race])
    assert len(result) == 1


async def test_sync_schedule_returns_empty_on_failure():
    jolpica = MagicMock()
    jolpica.get_current_schedule = AsyncMock(side_effect=Exception("network error"))
    repo = MagicMock()
    repo.save_schedule = AsyncMock()

    result = await sync_schedule(jolpica, repo)

    assert result == []
    repo.save_schedule.assert_not_awaited()


# --- sync_standings ---


async def test_sync_standings_saves_both():
    standings = _sample_driver_standings()
    c_standings = _sample_constructor_standings()
    jolpica = MagicMock()
    jolpica.get_driver_standings = AsyncMock(return_value=standings)
    jolpica.get_constructor_standings = AsyncMock(return_value=c_standings)
    repo = MagicMock()
    repo.save_driver_standings = AsyncMock()
    repo.save_constructor_standings = AsyncMock()
    repo.get_schedule_bounds = AsyncMock(return_value={"last_completed_round": 3})

    await sync_standings(jolpica, repo)

    jolpica.get_driver_standings.assert_awaited_once()
    repo.save_driver_standings.assert_awaited_once()
    jolpica.get_constructor_standings.assert_awaited_once()
    repo.save_constructor_standings.assert_awaited_once()


async def test_sync_standings_survives_exception():
    jolpica = MagicMock()
    jolpica.get_driver_standings = AsyncMock(side_effect=RuntimeError("timeout"))
    jolpica.get_constructor_standings = AsyncMock(side_effect=RuntimeError("timeout"))
    repo = MagicMock()
    repo.save_driver_standings = AsyncMock()
    repo.save_constructor_standings = AsyncMock()

    # Should not raise
    await sync_standings(jolpica, repo)
    repo.save_driver_standings.assert_not_awaited()
    repo.save_constructor_standings.assert_not_awaited()


# --- sync_drivers_and_circuits ---


async def test_sync_drivers_saves_drivers():
    driver = Driver(driver_id="ham", given_name="Lewis", family_name="Hamilton")
    jolpica = MagicMock()
    jolpica.get_drivers = AsyncMock(return_value=[driver])
    jolpica.get_circuits = AsyncMock(return_value=[])
    repo = MagicMock()
    repo.save_drivers = AsyncMock()
    repo.save_circuits = AsyncMock()

    await sync_drivers_and_circuits(jolpica, repo)

    repo.save_drivers.assert_awaited_once()


def _circuit():
    return Circuit(circuit_id="monza", name="Monza", locality="Monza", country="Italy")


def _make_race(round_num: int, race_date: date, race_time: time = time(13, 0), sprint=False):
    """Build a race fixture with optional sprint session."""
    kwargs = dict(
        season=2025,
        round=round_num,
        name=f"Race {round_num}",
        circuit=_circuit(),
        date=race_date,
        time=race_time,
        qualifying=RaceSession(
            name="Qualifying", date=race_date - timedelta(days=1), time=time(14, 0)
        ),
    )
    if sprint:
        kwargs["sprint"] = RaceSession(
            name="Sprint", date=race_date - timedelta(days=1), time=time(10, 0)
        )
        kwargs["sprint_qualifying"] = RaceSession(
            name="Sprint Qualifying", date=race_date - timedelta(days=2), time=time(14, 0)
        )
    return Race(**kwargs)


# ---------------------------------------------------------------------------
# _is_in_live_window
# ---------------------------------------------------------------------------


class TestIsInLiveWindow:
    """Verify the live-window boundary logic using imported constants."""

    def _entry(self, starts_at):
        return type("Entry", (), {"starts_at": starts_at})()

    def test_none_starts_at_returns_false(self):
        now = dt.datetime(2025, 6, 1, 14, 0, tzinfo=dt.UTC)
        assert _is_in_live_window(self._entry(None), now) is False

    def test_session_well_in_past_returns_false(self):
        starts_at = dt.datetime(2025, 6, 1, 10, 0, tzinfo=dt.UTC)
        # 10 hours after session start — well beyond 3h + margin
        now = starts_at + timedelta(hours=10)
        assert _is_in_live_window(self._entry(starts_at), now) is False

    def test_session_well_in_future_returns_false(self):
        starts_at = dt.datetime(2025, 6, 1, 14, 0, tzinfo=dt.UTC)
        # 5 hours before session start — before the margin window
        now = starts_at - timedelta(hours=5)
        assert _is_in_live_window(self._entry(starts_at), now) is False

    def test_just_inside_pre_session_margin(self):
        starts_at = dt.datetime(2025, 6, 1, 14, 0, tzinfo=dt.UTC)
        # 1 second inside the pre-session margin
        now = starts_at - _LIVE_WINDOW_MARGIN + timedelta(seconds=1)
        assert _is_in_live_window(self._entry(starts_at), now) is True

    def test_just_outside_pre_session_margin(self):
        starts_at = dt.datetime(2025, 6, 1, 14, 0, tzinfo=dt.UTC)
        # 1 second before the margin starts
        now = starts_at - _LIVE_WINDOW_MARGIN - timedelta(seconds=1)
        assert _is_in_live_window(self._entry(starts_at), now) is False

    def test_just_inside_post_session_margin(self):
        starts_at = dt.datetime(2025, 6, 1, 14, 0, tzinfo=dt.UTC)
        session_end = starts_at + timedelta(hours=3)
        # 1 second inside post-session margin
        now = session_end + _LIVE_WINDOW_MARGIN - timedelta(seconds=1)
        assert _is_in_live_window(self._entry(starts_at), now) is True

    def test_just_outside_post_session_margin(self):
        starts_at = dt.datetime(2025, 6, 1, 14, 0, tzinfo=dt.UTC)
        session_end = starts_at + timedelta(hours=3)
        # 1 second beyond the post-session margin
        now = session_end + _LIVE_WINDOW_MARGIN + timedelta(seconds=1)
        assert _is_in_live_window(self._entry(starts_at), now) is False

    def test_during_session_returns_true(self):
        starts_at = dt.datetime(2025, 6, 1, 14, 0, tzinfo=dt.UTC)
        now = starts_at + timedelta(hours=1)
        assert _is_in_live_window(self._entry(starts_at), now) is True


# ---------------------------------------------------------------------------
# sync_results_window
# ---------------------------------------------------------------------------


class TestSyncResultsWindow:
    """Verify sync_results_window respects the date window and isolates errors."""

    def _races_around_today(self):
        """Two races: one within 30-day window, one outside."""
        today = date.today()
        inside = _make_race(5, today - timedelta(days=10))
        outside = _make_race(2, today - timedelta(days=60))
        future = _make_race(10, today + timedelta(days=30))
        return [outside, inside, future]

    async def test_full_false_syncs_only_window(self):
        races = self._races_around_today()
        jolpica = MagicMock()
        jolpica.get_race_results = AsyncMock(return_value=(None, []))
        jolpica.get_qualifying_results = AsyncMock(return_value=(None, []))
        repo = MagicMock()
        repo.save_race_results = AsyncMock()

        await sync_results_window(jolpica, repo, races, full=False)

        # Only the "inside" race (round 5) should be synced; outside (round 2) skipped, future (10) skipped
        calls = jolpica.get_race_results.await_args_list
        rounds_synced = [c.args[1] for c in calls]
        assert "5" in rounds_synced
        assert "2" not in rounds_synced
        assert "10" not in rounds_synced

    async def test_full_true_syncs_all_completed(self):
        races = self._races_around_today()
        jolpica = MagicMock()
        jolpica.get_race_results = AsyncMock(return_value=(None, []))
        jolpica.get_qualifying_results = AsyncMock(return_value=(None, []))
        repo = MagicMock()
        repo.save_race_results = AsyncMock()

        await sync_results_window(jolpica, repo, races, full=True)

        # Both completed races synced (round 2 and 5), future (10) still skipped
        calls = jolpica.get_race_results.await_args_list
        rounds_synced = [c.args[1] for c in calls]
        assert "5" in rounds_synced
        assert "2" in rounds_synced
        assert "10" not in rounds_synced

    async def test_error_isolation_one_round_fails_others_succeed(self):
        today = date.today()
        r1 = _make_race(3, today - timedelta(days=5))
        r2 = _make_race(4, today - timedelta(days=3))

        jolpica = MagicMock()
        # First round raises, second round succeeds
        jolpica.get_race_results = AsyncMock(
            side_effect=[Exception("timeout"), (None, [MagicMock()])]
        )
        jolpica.get_qualifying_results = AsyncMock(return_value=(None, []))
        repo = MagicMock()
        repo.save_race_results = AsyncMock()
        repo.save_qualifying_results = AsyncMock()

        # Should not raise
        await sync_results_window(jolpica, repo, [r1, r2], full=False)

        # Second round's results were saved despite first round failing
        repo.save_race_results.assert_awaited_once()

    async def test_sprint_results_fetched_for_sprint_round(self):
        today = date.today()
        race = _make_race(5, today - timedelta(days=5), sprint=True)

        jolpica = MagicMock()
        jolpica.get_race_results = AsyncMock(return_value=(None, []))
        jolpica.get_qualifying_results = AsyncMock(return_value=(None, []))
        jolpica.get_sprint_results = AsyncMock(return_value=(None, []))
        repo = MagicMock()
        repo.save_race_results = AsyncMock()
        repo.save_qualifying_results = AsyncMock()
        repo.save_sprint_results = AsyncMock()

        await sync_results_window(jolpica, repo, [race], full=False)

        jolpica.get_sprint_results.assert_awaited_once()


# ---------------------------------------------------------------------------
# sync_pitstops_window
# ---------------------------------------------------------------------------


class TestSyncPitstopsWindow:
    """Verify sync_pitstops_window respects window and isolates errors."""

    async def test_only_syncs_within_window(self):
        today = date.today()
        inside = _make_race(5, today - timedelta(days=10))
        outside = _make_race(2, today - timedelta(days=60))

        jolpica = MagicMock()
        jolpica.get_pit_stops = AsyncMock(return_value=[MagicMock()])
        repo = MagicMock()
        repo.save_pit_stops = AsyncMock()

        await sync_pitstops_window(jolpica, repo, [outside, inside], full=False)

        # Only round 5 synced
        assert repo.save_pit_stops.await_count == 1
        args = repo.save_pit_stops.await_args_list[0].args
        assert args[0] == date.today().year
        assert args[1] == 5

    async def test_error_isolation(self):
        today = date.today()
        r1 = _make_race(3, today - timedelta(days=5))
        r2 = _make_race(4, today - timedelta(days=3))

        jolpica = MagicMock()
        jolpica.get_pit_stops = AsyncMock(side_effect=[Exception("fail"), [MagicMock()]])
        repo = MagicMock()
        repo.save_pit_stops = AsyncMock()

        await sync_pitstops_window(jolpica, repo, [r1, r2], full=False)

        # Second round saved despite first failing
        assert repo.save_pit_stops.await_count == 1


# ---------------------------------------------------------------------------
# sync_openf1_session_results
# ---------------------------------------------------------------------------


class TestSyncOpenF1SessionResults:
    """Verify OpenF1 session sync matches, skips, and isolates errors."""

    async def test_skips_sessions_in_live_window(self):
        """Sessions currently live should be skipped."""
        today = date.today()
        now_time = dt.datetime.now(tz=dt.UTC)
        # Create a race whose qualifying is happening RIGHT NOW
        race = Race(
            season=2025,
            round=5,
            name="Race 5",
            circuit=_circuit(),
            date=today + timedelta(days=1),
            time=time(13, 0),
            fp1=RaceSession(name="FP1", date=today - timedelta(days=1), time=time(10, 0)),
            qualifying=RaceSession(
                name="Qualifying",
                date=now_time.date(),
                time=now_time.time().replace(microsecond=0),
            ),
        )
        openf1 = MagicMock()
        openf1.get_sessions = AsyncMock(return_value=[])
        openf1.get_session_results = AsyncMock(return_value=[])
        jolpica = MagicMock()
        repo = MagicMock()
        repo.save_session_results = AsyncMock()

        await sync_openf1_session_results(openf1, jolpica, repo, [race], full=True)

        # Should not have fetched results for the live session
        openf1.get_session_results.assert_not_awaited()

    async def test_error_in_one_session_does_not_abort_others(self):
        today = date.today()
        race = Race(
            season=2025,
            round=5,
            name="Race 5",
            circuit=_circuit(),
            date=today,
            time=time(13, 0),
            fp1=RaceSession(name="FP1", date=today - timedelta(days=2), time=time(10, 0)),
            fp2=RaceSession(name="FP2", date=today - timedelta(days=2), time=time(14, 0)),
        )
        openf1_session_1 = MagicMock(session_key=101)
        openf1_session_2 = MagicMock(session_key=102)

        openf1 = MagicMock()
        openf1.get_sessions = AsyncMock(return_value=[openf1_session_1, openf1_session_2])
        openf1.get_session_results = AsyncMock(side_effect=[Exception("fail"), [MagicMock()]])
        jolpica = MagicMock()
        repo = MagicMock()
        repo.save_session_results = AsyncMock()

        with patch("f1_bot.utils.sessions.match_openf1_session") as mock_match:
            mock_match.side_effect = [openf1_session_1, openf1_session_2]
            await sync_openf1_session_results(openf1, jolpica, repo, [race], full=True)

        # Second session should still be saved
        assert repo.save_session_results.await_count == 1

    async def test_sync_openf1_session_results_saves_drivers_and_links_driver_id(self):
        today = date.today()
        race = Race(
            season=2025,
            round=5,
            name="Race 5",
            circuit=_circuit(),
            date=today,
            time=time(13, 0),
            fp1=RaceSession(name="FP1", date=today - timedelta(days=2), time=time(10, 0)),
        )
        openf1_session = MagicMock(session_key=101)

        # Mock OpenF1 client responses
        openf1 = MagicMock()
        openf1.get_sessions = AsyncMock(return_value=[openf1_session])

        session_result = SessionResult(position=1, driver_number=44, duration="1:12.345")
        openf1.get_session_results = AsyncMock(return_value=[session_result])

        driver_profile = {
            "driver_number": 44,
            "first_name": "Lewis",
            "last_name": "Hamilton",
            "country_code": "GBR",
            "name_acronym": "HAM",
            "team_name": "Mercedes",
            "team_colour": "00D2BE",
        }
        openf1.get_drivers = AsyncMock(return_value=[driver_profile])

        repo = MagicMock()
        repo.save_drivers = AsyncMock()
        repo.save_session_results = AsyncMock()

        with patch("f1_bot.utils.sessions.match_openf1_session") as mock_match:
            mock_match.return_value = openf1_session
            await sync_openf1_session_results(openf1, None, repo, [race], full=True)

        # Verify that drivers were saved
        repo.save_drivers.assert_awaited_once()
        saved_drivers = repo.save_drivers.call_args[0][1]
        assert len(saved_drivers) == 1
        assert saved_drivers[0].driver_id == "openf1_44_hamilton"
        assert saved_drivers[0].nationality == "GBR"

        # Verify that session results were saved with the driver_id linked
        repo.save_session_results.assert_awaited_once()
        saved_results = repo.save_session_results.call_args[0][3]
        assert len(saved_results) == 1
        assert saved_results[0].driver_id == "openf1_44_hamilton"


# ---------------------------------------------------------------------------
# sync_openf1_laps
# ---------------------------------------------------------------------------


class TestSyncOpenF1Laps:
    """Verify OpenF1 laps sync respects window and handles errors."""

    async def test_happy_path_saves_laps(self):
        today = date.today()
        race = _make_race(5, today - timedelta(days=10))

        openf1_session = MagicMock(session_key=200)
        openf1 = MagicMock()
        openf1.get_sessions = AsyncMock(return_value=[openf1_session])
        openf1.get_laps = AsyncMock(return_value=[MagicMock()])
        repo = MagicMock()
        repo.save_lap_timings = AsyncMock()

        with patch("f1_bot.utils.sessions.match_openf1_session", return_value=openf1_session):
            with patch("f1_bot.utils.sessions.find_race_session") as mock_find:
                mock_entry = MagicMock()
                mock_entry.starts_at = dt.datetime.combine(
                    today - timedelta(days=10), time(13, 0), tzinfo=dt.UTC
                )
                mock_find.return_value = mock_entry
                await sync_openf1_laps(openf1, repo, [race], full=True)

        repo.save_lap_timings.assert_awaited_once()

    async def test_error_isolation(self):
        today = date.today()
        r1 = _make_race(3, today - timedelta(days=5))
        r2 = _make_race(4, today - timedelta(days=3))

        openf1_session = MagicMock(session_key=300)
        openf1 = MagicMock()
        openf1.get_sessions = AsyncMock(return_value=[openf1_session])
        openf1.get_laps = AsyncMock(side_effect=[Exception("fail"), [MagicMock()]])
        repo = MagicMock()
        repo.save_lap_timings = AsyncMock()

        with patch("f1_bot.utils.sessions.match_openf1_session", return_value=openf1_session):
            with patch("f1_bot.utils.sessions.find_race_session") as mock_find:
                mock_entry = MagicMock()
                mock_entry.starts_at = dt.datetime(2025, 1, 1, 13, 0, tzinfo=dt.UTC)
                mock_find.return_value = mock_entry
                await sync_openf1_laps(openf1, repo, [r1, r2], full=True)

        # Second round saved despite first failing
        assert repo.save_lap_timings.await_count == 1


# ---------------------------------------------------------------------------
# hourly_sync
# ---------------------------------------------------------------------------


class TestHourlySync:
    """Verify hourly_sync orchestration."""

    async def test_calls_sync_functions_with_context_data(self):
        context = MagicMock()
        context.bot_data = {
            "jolpica": MagicMock(),
            "openf1": MagicMock(),
            "repo": MagicMock(),
        }
        context.bot_data["repo"].get_schedule = AsyncMock(return_value=[])
        context.bot_data["repo"].set_sync_metadata = AsyncMock()
        context.bot_data["repo"].get_schedule_bounds = AsyncMock(
            return_value={"last_completed_round": 3}
        )

        with patch(
            "f1_bot.scheduler.jobs.sync_schedule", new_callable=AsyncMock, return_value=[]
        ) as mock_sched:
            with patch(
                "f1_bot.scheduler.jobs.sync_standings", new_callable=AsyncMock
            ) as mock_stand:
                with patch(
                    "f1_bot.scheduler.jobs.sync_drivers_and_circuits", new_callable=AsyncMock
                ) as mock_dc:
                    await hourly_sync(context)

        mock_sched.assert_awaited_once_with(context.bot_data["jolpica"], context.bot_data["repo"])
        mock_stand.assert_awaited_once()
        mock_dc.assert_awaited_once()
