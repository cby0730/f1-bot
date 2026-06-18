"""Background fetch jobs — called by the scheduler, write into Repository.

Hourly sync:
  1) Jolpica: full-season schedule (all rounds)
  2) Jolpica: race/qualifying/sprint results for past 1-month window
  3) Jolpica: standings, drivers, constructors
  4) OpenF1: session_result for FP1/FP2/FP3/SQ within past 1 month
     — skip any session still inside live window (session_end + 30min > now)
  5) OpenF1: lap timings for completed races in past 1 month
"""

import asyncio
import datetime

import structlog
from telegram.ext import ContextTypes

from f1_bot.utils.sessions import session_entries

log = structlog.get_logger(__name__)

_OPENF1_THROTTLE = 3.5  # seconds between OpenF1 requests
_LIVE_WINDOW_MARGIN = datetime.timedelta(minutes=30)
_RESULTS_WINDOW = datetime.timedelta(days=30)


# ---------------------------------------------------------------------------
# Jolpica sync helpers
# ---------------------------------------------------------------------------


async def sync_schedule(jolpica, repo) -> list:
    """Fetch and save full-season schedule. Returns the race list."""
    try:
        races = await jolpica.get_current_schedule()
        if races:
            season = races[0].season
            await repo.save_schedule(season, races)
            current_year = datetime.date.today().year
            if season != current_year:
                await repo.save_schedule(current_year, races)
            await repo.set_sync_metadata("schedule")
            log.info("schedule_synced", count=len(races), season=season)
            return races
    except Exception as e:
        log.warning("schedule_sync_failed", error=str(e))
    return []


async def sync_results_window(jolpica, repo, races: list, full: bool = False) -> None:
    """Sync race/qualifying/sprint results for rounds within the past-1-month window.

    If full=True, syncs all completed rounds (used for startup).
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    cutoff = datetime.datetime.min.replace(tzinfo=datetime.UTC) if full else (now - _RESULTS_WINDOW)
    season = datetime.date.today().year

    for race in races:
        from f1_bot.formatting.timezone import combine_race_dt

        race_dt = combine_race_dt(race.date, race.time)
        if race_dt > now:
            continue  # future race, no results yet
        if race_dt < cutoff:
            continue  # outside sync window

        rnd = race.round
        try:
            # Race results
            _, results = await jolpica.get_race_results(str(season), str(rnd))
            if results:
                await repo.save_race_results(season, rnd, results)

            # Qualifying results
            _, q_results = await jolpica.get_qualifying_results(str(season), str(rnd))
            if q_results:
                await repo.save_qualifying_results(season, rnd, q_results)

            # Sprint results (only for sprint rounds)
            if race.sprint is not None:
                _, s_results = await jolpica.get_sprint_results(str(season), str(rnd))
                if s_results:
                    await repo.save_sprint_results(season, rnd, s_results)

            log.info("results_synced", season=season, round=rnd)
        except Exception as e:
            log.warning("results_sync_failed", season=season, round=rnd, error=str(e))


async def sync_standings(jolpica, repo) -> None:
    """Sync driver and constructor standings."""
    season = datetime.date.today().year
    try:
        standings = await jolpica.get_driver_standings()
        if standings:
            bounds = await repo.get_schedule_bounds(season)
            round_after = bounds.get("last_completed_round") or 0
            await repo.save_driver_standings(season, standings, round_after=round_after)
            log.info("driver_standings_synced", count=len(standings))
    except Exception as e:
        log.warning("driver_standings_sync_failed", error=str(e))

    try:
        standings = await jolpica.get_constructor_standings()
        if standings:
            bounds = await repo.get_schedule_bounds(season)
            round_after = bounds.get("last_completed_round") or 0
            await repo.save_constructor_standings(season, standings, round_after=round_after)
            log.info("constructor_standings_synced", count=len(standings))
    except Exception as e:
        log.warning("constructor_standings_sync_failed", error=str(e))


async def sync_drivers_and_circuits(jolpica, repo) -> None:
    """Sync drivers and circuits lists."""
    season = str(datetime.date.today().year)
    try:
        drivers = await jolpica.get_drivers(season)
        if drivers:
            await repo.save_drivers(int(season), drivers)
    except Exception as e:
        log.warning("drivers_sync_failed", error=str(e))

    try:
        circuits = await jolpica.get_circuits(season)
        if circuits:
            await repo.save_circuits(int(season), circuits)
    except Exception as e:
        log.warning("circuits_sync_failed", error=str(e))


async def sync_pitstops_window(jolpica, repo, races: list, full: bool = False) -> None:
    """Sync pitstops for completed races within sync window."""
    now = datetime.datetime.now(tz=datetime.UTC)
    cutoff = datetime.datetime.min.replace(tzinfo=datetime.UTC) if full else (now - _RESULTS_WINDOW)
    season = datetime.date.today().year

    for race in races:
        from f1_bot.formatting.timezone import combine_race_dt

        race_dt = combine_race_dt(race.date, race.time)
        if race_dt > now or race_dt < cutoff:
            continue

        try:
            stops = await jolpica.get_pit_stops(str(season), str(race.round))
            if stops:
                await repo.save_pit_stops(season, race.round, stops)
        except Exception as e:
            log.warning("pitstops_sync_failed", round=race.round, error=str(e))


# ---------------------------------------------------------------------------
# OpenF1 sync helpers
# ---------------------------------------------------------------------------


def _is_in_live_window(entry, now: datetime.datetime) -> bool:
    """Check if a session is within the OpenF1 live window (not available on free tier)."""
    if entry.starts_at is None:
        return False
    # Approximate session end as starts_at + 3 hours (generous for any session type)
    session_end = entry.starts_at + datetime.timedelta(hours=3)
    return (entry.starts_at - _LIVE_WINDOW_MARGIN) <= now <= (session_end + _LIVE_WINDOW_MARGIN)


async def sync_openf1_session_results(openf1, jolpica, repo, races: list, full: bool = False) -> None:
    """Sync FP1/FP2/FP3/SQ session results from OpenF1."""
    from f1_bot.utils.sessions import match_openf1_session

    now = datetime.datetime.now(tz=datetime.UTC)
    cutoff = datetime.datetime.min.replace(tzinfo=datetime.UTC) if full else (now - _RESULTS_WINDOW)
    season = datetime.date.today().year

    # Fetch all OpenF1 sessions for the year once
    try:
        openf1_sessions = await openf1.get_sessions(year=season)
    except Exception as e:
        log.warning("openf1_sessions_fetch_failed", error=str(e))
        return

    openf1_keys = {"fp1", "fp2", "fp3", "sprint_qualifying"}
    entries_to_sync = []

    for race in races:
        all_entries = session_entries([race])
        for entry in all_entries:
            if entry.key not in openf1_keys:
                continue
            if entry.starts_at is None:
                continue
            if entry.starts_at > now:
                continue  # future session
            if entry.starts_at < cutoff:
                continue  # outside window

            if _is_in_live_window(entry, now):
                log.debug("skipping_live_window", session=entry.key, round=race.round)
                continue

            entries_to_sync.append((race, entry))

    for race, entry in entries_to_sync:
        openf1_session = match_openf1_session(entry, openf1_sessions)
        if openf1_session is None:
            continue

        try:
            results = await openf1.get_session_results(session_key=openf1_session.session_key)
            if results:
                await repo.save_session_results(season, race.round, openf1_session.session_key, results)
                log.info("openf1_session_synced", session=entry.key, round=race.round)
            await asyncio.sleep(_OPENF1_THROTTLE)
        except Exception as e:
            log.warning("openf1_session_sync_failed", session=entry.key, round=race.round, error=str(e))


async def sync_openf1_laps(openf1, repo, races: list, full: bool = False) -> None:
    """Sync lap timings from OpenF1 for completed races (race session only this iteration)."""
    from f1_bot.utils.sessions import find_race_session, match_openf1_session

    now = datetime.datetime.now(tz=datetime.UTC)
    cutoff = datetime.datetime.min.replace(tzinfo=datetime.UTC) if full else (now - _RESULTS_WINDOW)
    season = datetime.date.today().year

    try:
        openf1_sessions = await openf1.get_sessions(year=season)
    except Exception as e:
        log.warning("openf1_sessions_fetch_failed", error=str(e))
        return

    for race in races:
        from f1_bot.formatting.timezone import combine_race_dt

        race_dt = combine_race_dt(race.date, race.time)
        if race_dt > now or race_dt < cutoff:
            continue

        if _is_in_live_window(
            type("Entry", (), {"starts_at": race_dt})(), now
        ):
            continue

        # Find matching OpenF1 race session
        race_entry = find_race_session([race], race.round, "race")
        if race_entry is None:
            continue

        openf1_session = match_openf1_session(race_entry, openf1_sessions)
        if openf1_session is None:
            continue

        try:
            laps = await openf1.get_laps(session_key=openf1_session.session_key)
            if laps:
                await repo.save_lap_timings(season, race.round, laps)
                log.info("openf1_laps_synced", round=race.round, count=len(laps))
            await asyncio.sleep(_OPENF1_THROTTLE)
        except Exception as e:
            log.warning("openf1_laps_sync_failed", round=race.round, error=str(e))


# ---------------------------------------------------------------------------
# Orchestration: startup + hourly
# ---------------------------------------------------------------------------


async def startup_sync(jolpica, openf1, repo) -> None:
    """Full-season sync on bot startup. Blocks until complete."""
    log.info("startup_sync_begin")

    races = await sync_schedule(jolpica, repo)
    if not races:
        log.warning("startup_sync_no_schedule")
        return

    await sync_results_window(jolpica, repo, races, full=True)
    await sync_standings(jolpica, repo)
    await sync_drivers_and_circuits(jolpica, repo)
    await sync_pitstops_window(jolpica, repo, races, full=True)
    await sync_openf1_session_results(openf1, jolpica, repo, races, full=True)
    await sync_openf1_laps(openf1, repo, races, full=True)

    await repo.set_sync_metadata("startup")
    log.info("startup_sync_complete")


async def hourly_sync(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Single hourly job that runs all sync tasks sequentially."""
    jolpica = context.bot_data["jolpica"]
    openf1 = context.bot_data["openf1"]
    repo = context.bot_data["repo"]

    log.info("hourly_sync_begin")

    races = await sync_schedule(jolpica, repo)
    if not races:
        # Try from cache
        season = datetime.date.today().year
        races = await repo.get_schedule(season)

    if races:
        await sync_results_window(jolpica, repo, races)
        await sync_pitstops_window(jolpica, repo, races)
        await sync_openf1_session_results(openf1, jolpica, repo, races)
        await sync_openf1_laps(openf1, repo, races)

    await sync_standings(jolpica, repo)
    await sync_drivers_and_circuits(jolpica, repo)

    await repo.set_sync_metadata("hourly")
    log.info("hourly_sync_complete")
