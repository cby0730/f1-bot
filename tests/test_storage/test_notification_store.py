"""Tests for notification subscription store methods."""

from datetime import UTC, datetime, timedelta

from f1_bot.models.notification import NotificationSubscription


async def test_save_and_get_notification(pg_store):
    fire_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    sub = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    sub_id = await pg_store.save_notification(sub)
    assert sub_id > 0

    subs = await pg_store.get_user_notifications(12345, 2026)
    assert len(subs) == 1
    assert subs[0].session_key == "race"
    assert subs[0].minutes_before == 30


async def test_save_duplicate_returns_existing_id(pg_store):
    fire_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    sub = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    first_id = await pg_store.save_notification(sub)
    assert first_id > 0
    second_id = await pg_store.save_notification(sub)
    assert second_id == first_id


async def test_delete_notification(pg_store):
    fire_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    sub = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    await pg_store.save_notification(sub)

    deleted = await pg_store.delete_notification(12345, 2026, 10, "race", 30)
    assert deleted is True

    subs = await pg_store.get_user_notifications(12345, 2026)
    assert len(subs) == 0


async def test_get_pending_notifications(pg_store):
    now = datetime(2026, 7, 1, 13, 0, tzinfo=UTC)

    # Due notification
    sub1 = NotificationSubscription(
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=now - timedelta(minutes=5),
    )
    # Future notification
    sub2 = NotificationSubscription(
        telegram_id=200,
        season=2026,
        round=10,
        session_key="qualifying",
        minutes_before=60,
        fire_at=now + timedelta(hours=1),
    )
    await pg_store.save_notification(sub1)
    await pg_store.save_notification(sub2)

    pending = await pg_store.get_pending_notifications(now)
    assert len(pending) == 1
    assert pending[0].telegram_id == 100


async def test_mark_notifications_sent(pg_store):
    fire_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    sub = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    sub_id = await pg_store.save_notification(sub)

    await pg_store.mark_notifications_sent([sub_id])

    # Should no longer appear in user's active notifications
    subs = await pg_store.get_user_notifications(12345, 2026)
    assert len(subs) == 0


async def test_resubscribe_after_notification_sent(pg_store):
    """After a notification fires and is marked sent, re-subscribing must succeed."""
    fire_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    sub = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    sub_id = await pg_store.save_notification(sub)
    await pg_store.mark_notifications_sent([sub_id])

    # Re-subscribe with a new fire_at (schedule changed)
    new_fire_at = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    sub2 = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=new_fire_at,
    )
    new_id = await pg_store.save_notification(sub2)
    assert new_id > 0

    subs = await pg_store.get_user_notifications(12345, 2026)
    assert len(subs) == 1
    assert subs[0].fire_at == new_fire_at


async def test_has_notification(pg_store):
    fire_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    sub = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    assert await pg_store.has_notification(12345, 2026, 10, "race", 30) is False

    await pg_store.save_notification(sub)
    assert await pg_store.has_notification(12345, 2026, 10, "race", 30) is True


async def test_get_next_fire_at(pg_store):
    t1 = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)
    t2 = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)

    sub1 = NotificationSubscription(
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=t1,
    )
    sub2 = NotificationSubscription(
        telegram_id=200,
        season=2026,
        round=10,
        session_key="qualifying",
        minutes_before=60,
        fire_at=t2,
    )
    await pg_store.save_notification(sub1)
    await pg_store.save_notification(sub2)

    next_fire = await pg_store.get_next_fire_at()
    assert next_fire == t2


async def test_delete_notifications_for_user(pg_store):
    fire_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    for i in range(3):
        sub = NotificationSubscription(
            telegram_id=12345,
            season=2026,
            round=10 + i,
            session_key="race",
            minutes_before=30,
            fire_at=fire_at,
        )
        await pg_store.save_notification(sub)

    count = await pg_store.delete_notifications_for_user(12345)
    assert count == 3

    subs = await pg_store.get_user_notifications(12345, 2026)
    assert len(subs) == 0
