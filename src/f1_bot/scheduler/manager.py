"""SchedulerManager — registers background jobs via python-telegram-bot's JobQueue."""

import structlog
from telegram.ext import Application

from f1_bot.scheduler.jobs import (
    fetch_constructor_standings,
    fetch_driver_standings,
    fetch_last_qualifying,
    fetch_last_results,
    fetch_schedule,
)

log = structlog.get_logger(__name__)

# Intervals in seconds
_SCHEDULE_INTERVAL = 6 * 3600  # 6 h
_STANDINGS_INTERVAL = 1 * 3600  # 1 h
_RESULTS_INTERVAL = 1 * 3600  # 1 h


def register_jobs(app: Application) -> None:
    jq = app.job_queue
    if jq is None:
        log.warning("job_queue_unavailable")
        return

    jq.run_repeating(fetch_schedule, interval=_SCHEDULE_INTERVAL, first=10, name="fetch_schedule")
    jq.run_repeating(
        fetch_driver_standings, interval=_STANDINGS_INTERVAL, first=15, name="fetch_wdc"
    )
    jq.run_repeating(
        fetch_constructor_standings, interval=_STANDINGS_INTERVAL, first=20, name="fetch_wcc"
    )
    jq.run_repeating(fetch_last_results, interval=_RESULTS_INTERVAL, first=25, name="fetch_results")
    jq.run_repeating(
        fetch_last_qualifying, interval=_RESULTS_INTERVAL, first=30, name="fetch_qualifying"
    )

    log.info("scheduler_jobs_registered", job_count=5)
