"""Tests for notification_sender — schedule_next_notification and send_notifications."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from telegram.error import Forbidden, RetryAfter

from f1_bot.models.notification import NotificationSubscription
from f1_bot.scheduler.notification_sender import schedule_next_notification, send_notifications


async def test_schedule_next_removes_existing_jobs():
    """schedule_next_notification removes old jobs before scheduling."""
    repo = AsyncMock()
    repo.get_next_fire_at = AsyncMock(return_value=None)

    old_job = MagicMock()
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[old_job])

    await schedule_next_notification(jq, repo)

    old_job.schedule_removal.assert_called_once()
    jq.run_once.assert_not_called()  # No pending notifications


async def test_schedule_next_schedules_when_pending():
    """schedule_next_notification schedules run_once when there's a pending notification."""
    fire_at = datetime.now(UTC) + timedelta(hours=1)
    repo = AsyncMock()
    repo.get_next_fire_at = AsyncMock(return_value=fire_at)

    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    await schedule_next_notification(jq, repo)

    jq.run_once.assert_called_once()
    call_kwargs = jq.run_once.call_args
    assert call_kwargs[1]["name"] == "notification_send"


async def test_schedule_next_past_fires_immediately():
    """If fire_at is in the past, delay should be 1 second (minimum)."""
    fire_at = datetime.now(UTC) - timedelta(hours=1)
    repo = AsyncMock()
    repo.get_next_fire_at = AsyncMock(return_value=fire_at)

    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    await schedule_next_notification(jq, repo)

    jq.run_once.assert_called_once()
    delay = jq.run_once.call_args[1]["when"]
    assert delay == 1


async def test_send_notifications_marks_after_sending():
    """send_notifications marks notifications as sent AFTER successful delivery."""
    now = datetime.now(UTC)
    sub = NotificationSubscription(
        id=42,
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=now,
    )

    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=[sub])
    repo.mark_notifications_sent = AsyncMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_next_fire_at = AsyncMock(return_value=None)

    bot = AsyncMock()
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.bot = bot
    context.job_queue = jq

    await send_notifications(context)

    bot.send_message.assert_awaited_once()
    repo.mark_notifications_sent.assert_awaited_once_with([42])


async def test_send_notifications_handles_forbidden():
    """When user blocked the bot, remove their notifications."""
    now = datetime.now(UTC)
    sub = NotificationSubscription(
        id=42,
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=now,
    )

    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=[sub])
    repo.mark_notifications_sent = AsyncMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.remove_dead_user = AsyncMock()
    repo.get_next_fire_at = AsyncMock(return_value=None)

    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=Forbidden("blocked"))

    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.bot = bot
    context.job_queue = jq

    await send_notifications(context)

    repo.remove_dead_user.assert_awaited_once_with(100)
    repo.mark_notifications_sent.assert_awaited_once_with([42])


async def test_send_notifications_partial_failure_only_marks_successful():
    """When some sends fail, only successful IDs are marked sent; failed IDs survive for retry."""
    now = datetime.now(UTC)
    subs = [
        NotificationSubscription(
            id=1,
            telegram_id=100,
            season=2026,
            round=10,
            session_key="race",
            minutes_before=30,
            fire_at=now,
        ),
        NotificationSubscription(
            id=2,
            telegram_id=200,
            season=2026,
            round=10,
            session_key="race",
            minutes_before=30,
            fire_at=now,
        ),
        NotificationSubscription(
            id=3,
            telegram_id=300,
            season=2026,
            round=10,
            session_key="race",
            minutes_before=30,
            fire_at=now,
        ),
    ]

    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=subs)
    repo.mark_notifications_sent = AsyncMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_next_fire_at = AsyncMock(return_value=None)

    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=[None, Exception("network error"), None])

    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.bot = bot
    context.job_queue = jq

    await send_notifications(context)

    # id=2 failed with transient error — must NOT be deleted, will retry next cycle
    repo.mark_notifications_sent.assert_awaited_once_with([1, 3])


async def test_send_no_pending_reschedules():
    """When no pending notifications, it reschedules for the next one."""
    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=[])
    repo.get_next_fire_at = AsyncMock(return_value=None)

    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.bot = AsyncMock()
    context.job_queue = jq

    await send_notifications(context)

    # Should not try to send anything
    context.bot.send_message.assert_not_awaited()


async def test_send_with_rate_limiter():
    """send_notifications respects notification_limiter."""
    now = datetime.now(UTC)
    sub = NotificationSubscription(
        id=1,
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=now,
    )

    limiter = AsyncMock()

    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=[sub])
    repo.mark_notifications_sent = AsyncMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_next_fire_at = AsyncMock(return_value=None)

    context = MagicMock()
    context.bot_data = {"repo": repo, "notification_limiter": limiter}
    context.bot = AsyncMock()
    context.job_queue = MagicMock()
    context.job_queue.get_jobs_by_name = MagicMock(return_value=[])

    await send_notifications(context)

    limiter.acquire.assert_awaited_once()


async def test_send_retry_after_second_failure_not_marked():
    """When RetryAfter retry also fails, notification survives for next cycle."""
    now = datetime.now(UTC)
    sub = NotificationSubscription(
        id=7,
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=now,
    )

    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=[sub])
    repo.mark_notifications_sent = AsyncMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_next_fire_at = AsyncMock(return_value=None)

    bot = AsyncMock()
    bot.send_message = AsyncMock(
        side_effect=[RetryAfter(retry_after=1), Exception("still failing")]
    )

    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.bot = bot
    context.job_queue = jq

    await send_notifications(context)

    # Failed notification must NOT be deleted — row survives for retry
    repo.mark_notifications_sent.assert_not_awaited()


async def test_send_schedule_cache_avoids_duplicate_queries():
    """Schedule is fetched once per season, not once per notification."""
    now = datetime.now(UTC)
    subs = [
        NotificationSubscription(
            id=i,
            telegram_id=100 + i,
            season=2026,
            round=10,
            session_key="race",
            minutes_before=30,
            fire_at=now,
        )
        for i in range(1, 4)
    ]

    repo = AsyncMock()
    repo.get_pending_notifications = AsyncMock(return_value=subs)
    repo.mark_notifications_sent = AsyncMock()
    repo.get_schedule = AsyncMock(return_value=[])
    repo.get_next_fire_at = AsyncMock(return_value=None)

    bot = AsyncMock()
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])

    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.bot = bot
    context.job_queue = jq

    await send_notifications(context)

    # 3 notifications, all season=2026 — schedule fetched only once
    repo.get_schedule.assert_awaited_once_with(2026)
