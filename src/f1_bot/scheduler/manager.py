"""SchedulerManager — registers the single hourly sync job via python-telegram-bot's JobQueue."""

import structlog
from telegram.ext import Application

from f1_bot.scheduler.jobs import hourly_sync

log = structlog.get_logger(__name__)

# All sync work runs in a single hourly cycle.
_POLL_INTERVAL = 1 * 3600  # 1 h


def register_jobs(app: Application) -> None:
    jq = app.job_queue
    if jq is None:
        log.warning("job_queue_unavailable")
        return

    # Single unified hourly job replaces the old 6 staggered jobs.
    # first=60: give startup sync time to finish before first hourly run.
    jq.run_repeating(hourly_sync, interval=_POLL_INTERVAL, first=60, name="hourly_sync")

    log.info("scheduler_jobs_registered", job_count=1)
