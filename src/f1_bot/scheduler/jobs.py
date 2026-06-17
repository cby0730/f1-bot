"""Background fetch jobs — called by the scheduler, write into Repository."""

import structlog
from telegram.ext import ContextTypes

log = structlog.get_logger(__name__)


async def fetch_schedule(context: ContextTypes.DEFAULT_TYPE) -> None:
    jolpica = context.bot_data["jolpica"]
    repo = context.bot_data["repo"]
    try:
        races = await jolpica.get_current_schedule()
        if races:
            await repo.save_schedule(races[0].season, races)
            log.info("schedule_refreshed", count=len(races), season=races[0].season)
    except Exception as e:
        log.warning("schedule_fetch_failed", error=str(e))


async def fetch_driver_standings(context: ContextTypes.DEFAULT_TYPE) -> None:
    jolpica = context.bot_data["jolpica"]
    repo = context.bot_data["repo"]
    try:
        standings = await jolpica.get_driver_standings()
        if standings:
            import datetime

            season = datetime.date.today().year
            await repo.save_driver_standings(season, standings, ttl=3600)
            log.info("driver_standings_refreshed", count=len(standings))
    except Exception as e:
        log.warning("driver_standings_fetch_failed", error=str(e))


async def fetch_constructor_standings(context: ContextTypes.DEFAULT_TYPE) -> None:
    jolpica = context.bot_data["jolpica"]
    repo = context.bot_data["repo"]
    try:
        standings = await jolpica.get_constructor_standings()
        if standings:
            import datetime

            season = datetime.date.today().year
            await repo.save_constructor_standings(season, standings, ttl=3600)
            log.info("constructor_standings_refreshed", count=len(standings))
    except Exception as e:
        log.warning("constructor_standings_fetch_failed", error=str(e))


async def fetch_last_results(context: ContextTypes.DEFAULT_TYPE) -> None:
    jolpica = context.bot_data["jolpica"]
    repo = context.bot_data["repo"]
    try:
        race, results = await jolpica.get_race_results()
        if race and results:
            await repo.save_race_results(race.season, race.round, results)
            log.info("race_results_refreshed", season=race.season, round=race.round)
    except Exception as e:
        log.warning("race_results_fetch_failed", error=str(e))


async def fetch_last_qualifying(context: ContextTypes.DEFAULT_TYPE) -> None:
    jolpica = context.bot_data["jolpica"]
    repo = context.bot_data["repo"]
    try:
        race, results = await jolpica.get_qualifying_results()
        if race and results:
            await repo.save_qualifying_results(race.season, race.round, results)
            log.info("qualifying_refreshed", season=race.season, round=race.round)
    except Exception as e:
        log.warning("qualifying_fetch_failed", error=str(e))
