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
import json

import structlog
from telegram.ext import ContextTypes

from f1_bot.formatting.timezone import combine_race_dt
from f1_bot.utils.sessions import session_entries

log = structlog.get_logger(__name__)

_LIVE_WINDOW_MARGIN = datetime.timedelta(minutes=30)
_RESULTS_WINDOW = datetime.timedelta(days=30)


def _earliest_session_start(race) -> datetime.datetime | None:
    """Return the earliest session start time for a race weekend."""
    times = []
    for session in (
        race.fp1,
        race.fp2,
        race.fp3,
        race.qualifying,
        race.sprint_qualifying,
        race.sprint,
    ):
        if session and session.date:
            times.append(combine_race_dt(session.date, session.time))
    times.append(combine_race_dt(race.date, race.time))
    return min(times) if times else None


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

    Each session type is fetched independently based on its own start time.
    If full=True, syncs all completed rounds (used for startup).
    """
    from f1_bot.utils.sessions import find_race_session

    now = datetime.datetime.now(tz=datetime.UTC)
    cutoff = datetime.datetime.min.replace(tzinfo=datetime.UTC) if full else (now - _RESULTS_WINDOW)

    for race in races:
        season = race.season
        race_dt = combine_race_dt(race.date, race.time)
        if race_dt < cutoff:
            continue  # outside sync window

        # If the entire weekend hasn't started yet, skip
        earliest = _earliest_session_start(race)
        if earliest is not None and earliest > now:
            continue

        rnd = race.round

        # Race: only after race completes
        if race_dt <= now:
            try:
                _, results = await jolpica.get_race_results(str(season), str(rnd))
                if results:
                    await repo.save_race_results(season, rnd, results)
            except Exception as e:
                log.warning("race_results_sync_failed", season=season, round=rnd, error=str(e))

        # Qualifying: after qualifying completes
        q_entry = find_race_session([race], rnd, "qualifying")
        if q_entry and q_entry.starts_at and q_entry.starts_at <= now:
            try:
                _, q_results = await jolpica.get_qualifying_results(str(season), str(rnd))
                if q_results:
                    await repo.save_qualifying_results(season, rnd, q_results)
            except Exception as e:
                log.warning(
                    "qualifying_results_sync_failed", season=season, round=rnd, error=str(e)
                )

        # Sprint: after sprint completes
        if race.sprint is not None:
            s_entry = find_race_session([race], rnd, "sprint")
            if s_entry and s_entry.starts_at and s_entry.starts_at <= now:
                try:
                    _, s_results = await jolpica.get_sprint_results(str(season), str(rnd))
                    if s_results:
                        await repo.save_sprint_results(season, rnd, s_results)
                except Exception as e:
                    log.warning(
                        "sprint_results_sync_failed", season=season, round=rnd, error=str(e)
                    )

        log.info("results_synced", season=season, round=rnd)


async def sync_standings(jolpica, repo) -> None:
    """Sync driver and constructor standings."""
    season = datetime.date.today().year
    bounds = await repo.get_schedule_bounds(season)
    round_after = bounds.get("last_completed_round") or 0

    try:
        standings = await jolpica.get_driver_standings()
        if standings:
            await repo.save_driver_standings(season, standings, round_after=round_after)
            log.info("driver_standings_synced", count=len(standings))
    except Exception as e:
        log.warning("driver_standings_sync_failed", error=str(e))

    try:
        standings = await jolpica.get_constructor_standings()
        if standings:
            await repo.save_constructor_standings(season, standings, round_after=round_after)
            log.info("constructor_standings_synced", count=len(standings))
    except Exception as e:
        log.warning("constructor_standings_sync_failed", error=str(e))


async def sync_drivers_and_circuits(jolpica, repo) -> None:
    """Sync drivers and circuits lists."""
    season = datetime.date.today().year
    try:
        drivers = await jolpica.get_drivers(str(season))
        if drivers:
            await repo.save_drivers(season, drivers)
    except Exception as e:
        log.warning("drivers_sync_failed", error=str(e))

    try:
        circuits = await jolpica.get_circuits(str(season))
        if circuits:
            await repo.save_circuits(season, circuits)
    except Exception as e:
        log.warning("circuits_sync_failed", error=str(e))


async def sync_pitstops_window(jolpica, repo, races: list, full: bool = False) -> None:
    """Sync pitstops for completed races within sync window."""
    now = datetime.datetime.now(tz=datetime.UTC)
    cutoff = datetime.datetime.min.replace(tzinfo=datetime.UTC) if full else (now - _RESULTS_WINDOW)

    for race in races:
        season = race.season
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


def make_openf1_driver_id(d: dict) -> str:
    # Use fallback if last_name or broadcast_name are missing
    last_name = (
        (d.get("last_name") or d.get("broadcast_name") or "driver")
        .lower()
        .strip()
        .replace(" ", "_")
    )
    return f"openf1_{d['driver_number']}_{last_name}"


async def _enrich_and_save_openf1_drivers(
    openf1, repo, season: int, session_key: int, results: list
) -> None:
    """Fetch drivers from OpenF1, cache them to database, and link driver_ids to SessionResult list."""
    try:
        openf1_drivers = await openf1.get_drivers(session_key=session_key)
    except Exception as e:
        log.warning("openf1_drivers_fetch_failed", session_key=session_key, error=str(e))
        openf1_drivers = []

    if openf1_drivers:
        from f1_bot.models.driver import Driver

        drivers_to_save = []
        d_map = {}
        for d in openf1_drivers:
            if "driver_number" not in d:
                continue
            d_id = make_openf1_driver_id(d)
            d_map[d["driver_number"]] = d_id

            nationality = d.get("country_code") or ""
            drv = Driver(
                driver_id=d_id,
                permanent_number=str(d["driver_number"]),
                code=d.get("name_acronym"),
                given_name=d.get("first_name") or "",
                family_name=d.get("last_name") or d.get("broadcast_name") or "",
                nationality=nationality,
                headshot_url=d.get("headshot_url"),
                team_name=d.get("team_name"),
                team_colour=d.get("team_colour"),
            )
            drivers_to_save.append(drv)

        if drivers_to_save:
            await repo.save_drivers(int(season), drivers_to_save)

        for r in results:
            r.driver_id = d_map.get(r.driver_number)


async def run_driver_id_backfill_migration(openf1, repo) -> None:
    """One-time startup migration to populate driver_id in historical session results."""
    migration_key = "backfill_session_results_driver_id_v2"
    if await repo.get_sync_metadata(migration_key):
        return

    log.info("database_migration_backfill_start")
    try:
        rows = await repo.get_all_results_by_type_prefix("session:")
        if not rows:
            await repo.set_sync_metadata(migration_key)
            log.info("database_migration_backfill_no_records")
            return

        for row in rows:
            season = row["season"]
            rnd = row["round"]
            session_type = row["type"]
            parts = session_type.split(":")
            if len(parts) == 3:
                save_key = f"{parts[1]}:{parts[2]}"
                session_key = int(parts[2])
            elif len(parts) == 2:
                session_key_str = parts[1]
                if not session_key_str.isdigit():
                    continue
                save_key = int(session_key_str)
                session_key = save_key
            else:
                continue

            from f1_bot.models.results import SessionResult

            results_list = [SessionResult.model_validate(r) for r in json.loads(row["data_json"])]

            await _enrich_and_save_openf1_drivers(openf1, repo, season, session_key, results_list)

            await repo.save_session_results(season, rnd, save_key, results_list)

        await repo.set_sync_metadata(migration_key)
        log.info("database_migration_backfill_complete")
    except Exception as e:
        log.error("database_migration_backfill_failed", error=str(e))


async def sync_openf1_session_results(openf1, repo, races: list, full: bool = False) -> None:
    """Sync FP1/FP2/FP3/SQ session results from OpenF1."""
    from f1_bot.utils.sessions import match_openf1_session

    now = datetime.datetime.now(tz=datetime.UTC)
    cutoff = datetime.datetime.min.replace(tzinfo=datetime.UTC) if full else (now - _RESULTS_WINDOW)
    season = races[0].season if races else datetime.date.today().year

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
                await _enrich_and_save_openf1_drivers(
                    openf1, repo, race.season, openf1_session.session_key, results
                )
                await repo.save_session_results(
                    race.season, race.round, f"{entry.key}:{openf1_session.session_key}", results
                )
                log.info("openf1_session_synced", session=entry.key, round=race.round)
        except Exception as e:
            log.warning(
                "openf1_session_sync_failed", session=entry.key, round=race.round, error=str(e)
            )


async def sync_openf1_laps(openf1, repo, races: list, full: bool = False) -> None:
    """Sync lap timings from OpenF1 for completed races (race session only this iteration)."""
    from f1_bot.utils.sessions import find_race_session, match_openf1_session

    now = datetime.datetime.now(tz=datetime.UTC)
    cutoff = datetime.datetime.min.replace(tzinfo=datetime.UTC) if full else (now - _RESULTS_WINDOW)
    season = races[0].season if races else datetime.date.today().year

    try:
        openf1_sessions = await openf1.get_sessions(year=season)
    except Exception as e:
        log.warning("openf1_sessions_fetch_failed", error=str(e))
        return

    for race in races:
        race_dt = combine_race_dt(race.date, race.time)
        if race_dt > now or race_dt < cutoff:
            continue

        race_entry = find_race_session([race], race.round, "race")
        if race_entry is None:
            continue

        if _is_in_live_window(race_entry, now):
            continue

        openf1_session = match_openf1_session(race_entry, openf1_sessions)
        if openf1_session is None:
            continue

        try:
            laps = await openf1.get_laps(session_key=openf1_session.session_key)
            if laps:
                await repo.save_lap_timings(race.season, race.round, laps)
                log.info("openf1_laps_synced", round=race.round, count=len(laps))
        except Exception as e:
            log.warning("openf1_laps_sync_failed", round=race.round, error=str(e))


# ---------------------------------------------------------------------------
# Orchestration: startup + hourly
# ---------------------------------------------------------------------------


async def startup_sync(jolpica, openf1, repo) -> None:
    """Full-season sync on bot startup. Blocks until complete."""
    log.info("startup_sync_begin")

    # Run database migration
    await run_driver_id_backfill_migration(openf1, repo)

    races = await sync_schedule(jolpica, repo)
    if not races:
        season = datetime.date.today().year
        races = await repo.get_schedule(season)
        if not races:
            log.warning("startup_sync_no_schedule")

    async def jolpica_group() -> None:
        if races:
            await sync_results_window(jolpica, repo, races, full=True)
            await sync_pitstops_window(jolpica, repo, races, full=True)
        await sync_standings(jolpica, repo)
        await sync_drivers_and_circuits(jolpica, repo)

    async def openf1_group() -> None:
        if races:
            await sync_openf1_session_results(openf1, repo, races, full=True)
            await sync_openf1_laps(openf1, repo, races, full=True)

    results = await asyncio.gather(jolpica_group(), openf1_group(), return_exceptions=True)
    failed = False
    for r in results:
        if isinstance(r, Exception):
            log.error("startup_sync_group_failed", error=str(r), exc_info=r)
            failed = True

    if not failed:
        await repo.set_sync_metadata("startup")
        log.info("startup_sync_complete")
    else:
        log.warning("startup_sync_incomplete_due_to_failures")


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

    async def jolpica_group() -> None:
        if races:
            await sync_results_window(jolpica, repo, races)
            await sync_pitstops_window(jolpica, repo, races)
        await sync_standings(jolpica, repo)
        await sync_drivers_and_circuits(jolpica, repo)

    async def openf1_group() -> None:
        if races:
            await sync_openf1_session_results(openf1, repo, races)
            await sync_openf1_laps(openf1, repo, races)

    results = await asyncio.gather(jolpica_group(), openf1_group(), return_exceptions=True)
    failed = False
    for r in results:
        if isinstance(r, Exception):
            log.error("hourly_sync_group_failed", error=str(r), exc_info=r)
            failed = True

    if not failed:
        await repo.set_sync_metadata("hourly")
        log.info("hourly_sync_complete")
    else:
        log.warning("hourly_sync_incomplete_due_to_failures")
