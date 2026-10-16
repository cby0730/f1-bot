"""Notification sender using PTB's run_once for precise scheduling."""

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter

from f1_bot.line.render import markdown_to_plain, text_message
from f1_bot.models.notification import NotificationSubscription

log = structlog.get_logger(__name__)

# A failed send is retried until it is this far past its fire_at, then dropped.
# Without a bound a permanently failing row (e.g. "chat not found") stays
# MIN(fire_at) and is retried every second forever. Measured from fire_at, not
# session start, so a 3hr reminder can be dropped with the session still ahead —
# accepted: a reminder an hour late has already failed at its job.
_MAX_LATENESS = timedelta(hours=1)


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


async def _push_line(bot_data: dict, repo, user_id: int, msg: str) -> None:
    """LINE users carry negative ids (see the line_users table).

    A LINE user who blocks the bot is cleaned up by the webhook's unfollow event,
    so there is no Forbidden-style branch here.
    """
    line_user_id = await repo.get_line_user_id(user_id)
    await bot_data["line"].push(line_user_id, [text_message(markdown_to_plain(msg))])


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
    failed: list[NotificationSubscription] = []
    schedule_cache: dict[int, list] = {}

    for sub in pending:
        if rate_limiter:
            await rate_limiter.acquire()
        try:
            if sub.season not in schedule_cache:
                schedule_cache[sub.season] = await repo.get_schedule(sub.season)
            races = schedule_cache[sub.season]
            race = next((r for r in races if r.round == sub.round), None)
            # This job has no Update, so resolve_context() is unavailable: read the
            # language directly. No tz lookup — the push message renders no clock time.
            lang = await repo.get_user_language(sub.telegram_id)
            msg = format_notification_message(race, sub.session_key, sub.minutes_before, lang)
            if sub.telegram_id < 0:
                await _push_line(context.bot_data, repo, sub.telegram_id, msg)
            else:
                await bot.send_message(
                    chat_id=sub.telegram_id, text=msg, parse_mode=ParseMode.MARKDOWN
                )
            sent_ids.append(sub.id)
        except Forbidden:
            log.warning("user_blocked_bot", telegram_id=sub.telegram_id)
            await repo.remove_dead_user(sub.telegram_id)
            sent_ids.append(sub.id)
        except RetryAfter as e:
            log.warning("rate_limited", retry_after=e.retry_after)
            delay = (
                e.retry_after.total_seconds()
                if hasattr(e.retry_after, "total_seconds")
                else e.retry_after
            )
            await asyncio.sleep(delay)
            try:
                await bot.send_message(
                    chat_id=sub.telegram_id, text=msg, parse_mode=ParseMode.MARKDOWN
                )
                sent_ids.append(sub.id)
            except Exception:
                log.exception("notification_retry_failed", telegram_id=sub.telegram_id)
                failed.append(sub)
        except Exception:
            log.exception("notification_send_failed", telegram_id=sub.telegram_id)
            failed.append(sub)

    expired_ids = [sub.id for sub in failed if now - sub.fire_at > _MAX_LATENESS]
    if expired_ids:
        log.warning("notifications_expired", ids=expired_ids)
    if len(failed) > len(expired_ids):
        log.warning("notifications_deferred", failed=len(failed) - len(expired_ids))

    if sent_ids or expired_ids:
        await repo.mark_notifications_sent(sent_ids + expired_ids)

    await schedule_next_notification(jq, repo)
