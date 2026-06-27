"""Notification sender using PTB's run_once for precise scheduling."""

import asyncio
from datetime import UTC, datetime

import structlog
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter

log = structlog.get_logger(__name__)


async def schedule_next_notification(jq, repo) -> None:
    """Cancel existing notification job and schedule the next one based on DB."""
    for job in jq.get_jobs_by_name("notification_send"):
        job.schedule_removal()

    next_fire = await repo.get_next_fire_at()
    if next_fire:
        now = datetime.now(UTC)
        # If fire_at is in the past, fire immediately (1 second from now)
        delay = max((next_fire - now).total_seconds(), 1)
        jq.run_once(send_notifications, when=delay, name="notification_send")
        log.info("notification_scheduled", fire_at=next_fire.isoformat(), delay_s=round(delay))


async def send_notifications(context) -> None:
    """PTB job callback: send all pending notifications."""
    repo = context.bot_data["repo"]
    jq = context.job_queue
    bot = context.bot
    rate_limiter = context.bot_data.get("notification_limiter")

    now = datetime.now(UTC)
    pending = await repo.get_pending_notifications(now)
    if not pending:
        await schedule_next_notification(jq, repo)
        return

    from f1_bot.formatting.messages import format_notification_message

    sent_ids: list[int] = []

    for sub in pending:
        if rate_limiter:
            await rate_limiter.acquire()
        try:
            races = await repo.get_schedule(sub.season)
            race = next((r for r in races if r.round == sub.round), None)
            msg = format_notification_message(race, sub.session_key, sub.minutes_before)
            await bot.send_message(chat_id=sub.telegram_id, text=msg, parse_mode=ParseMode.MARKDOWN)
            sent_ids.append(sub.id)
        except Forbidden:
            log.warning("user_blocked_bot", telegram_id=sub.telegram_id)
            await repo.remove_dead_user(sub.telegram_id)
            sent_ids.append(sub.id)
        except RetryAfter as e:
            log.warning("rate_limited", retry_after=e.retry_after)
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(
                    chat_id=sub.telegram_id, text=msg, parse_mode=ParseMode.MARKDOWN
                )
                sent_ids.append(sub.id)
            except Exception:
                log.exception("notification_retry_failed", telegram_id=sub.telegram_id)
        except Exception:
            log.exception("notification_send_failed", telegram_id=sub.telegram_id)

    if sent_ids:
        await repo.mark_notifications_sent(sent_ids)

    await schedule_next_notification(jq, repo)
