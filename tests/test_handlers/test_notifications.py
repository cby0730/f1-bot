"""Tests for notification handler — /remind and notify: callback flow."""

from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from f1_bot.handlers.notifications import (
    MAX_REMINDERS,
    _build_remind_view,
    _notify_del,
    _notify_pick,
    _notify_sess,
    _notify_set,
    _remind_command,
)
from f1_bot.models.notification import NotificationSubscription
from f1_bot.models.race import Circuit, Race, RaceSession


def _make_race(round_num: int = 16, days_ahead: int = 10) -> Race:
    future = date.today() + timedelta(days=days_ahead)
    return Race(
        season=2026,
        round=round_num,
        name=f"Grand Prix {round_num}",
        circuit=Circuit(circuit_id="test", name="Test Circuit", locality="Test", country="Test"),
        date=future,
        time=time(13, 0),
        fp1=RaceSession(name="FP1", date=future - timedelta(days=2), time=time(10, 0)),
        qualifying=RaceSession(
            name="Qualifying", date=future - timedelta(days=1), time=time(14, 0)
        ),
    )


def _make_update(callback_data: str, user_id: int = 12345):
    update = MagicMock(spec=["callback_query", "effective_user"])
    query = AsyncMock()
    query.data = callback_data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update.callback_query = query
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    return update


def _make_context(repo=None, jq=None):
    context = MagicMock()
    context.bot_data = {
        "repo": repo or AsyncMock(),
    }
    context.application = MagicMock()
    context.application.job_queue = jq or MagicMock()
    return context


async def test_remind_empty(repo):
    """When no reminders exist, /remind shows empty message."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.effective_message = AsyncMock()

    context = _make_context(repo=repo)

    await _remind_command(update, context)

    update.effective_message.reply_text.assert_awaited_once()
    text = update.effective_message.reply_text.call_args[0][0]
    assert "no active reminders" in text.lower()


async def test_remind_with_subscriptions(repo):
    """Single-round auto-skips to State B with delete buttons."""
    race = _make_race()
    await repo.save_schedule(2026, [race])

    fire_at = datetime.now(UTC) + timedelta(hours=1)
    sub = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=16,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    await repo.subscribe_notification(sub)

    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.effective_message = AsyncMock()

    context = _make_context(repo=repo)

    await _remind_command(update, context)

    call_args = update.effective_message.reply_text.call_args
    text = call_args[0][0]
    assert "R16" in text
    markup = call_args.kwargs.get("reply_markup") or call_args[1].get("reply_markup")
    buttons = [btn.text for row in markup.inline_keyboard for btn in row]
    assert any("Race" in b and "30min" in b for b in buttons)


async def test_notify_pick_shows_sessions():
    """notify:pick shows session selection buttons."""
    repo = AsyncMock()
    repo.get_schedule = AsyncMock(return_value=[_make_race()])

    update = _make_update("notify:pick:16")
    context = _make_context(repo=repo)

    with patch("f1_bot.handlers.notifications.find_next_sessions") as mock_fns:
        mock_fns.return_value = [
            MagicMock(key="fp1"),
            MagicMock(key="qualifying"),
            MagicMock(key="race"),
        ]
        await _notify_pick(update, context)

    update.callback_query.edit_message_text.assert_awaited_once()
    update.callback_query.answer.assert_awaited_once()
    call_kwargs = update.callback_query.edit_message_text.call_args
    markup = call_kwargs.kwargs.get("reply_markup") or call_kwargs[1].get("reply_markup")
    # Should have session buttons + back
    assert markup is not None
    buttons = [btn.text for row in markup.inline_keyboard for btn in row]
    assert "FP1" in buttons
    assert "Race" in buttons
    assert "🔙 Back" in buttons


async def test_notify_sess_shows_timing_presets():
    """notify:sess shows timing preset buttons."""
    repo = AsyncMock()
    repo.has_notification = AsyncMock(return_value=False)

    update = _make_update("notify:sess:race:16")
    context = _make_context(repo=repo)

    await _notify_sess(update, context)

    update.callback_query.edit_message_text.assert_awaited_once()
    update.callback_query.answer.assert_awaited_once()
    call_kwargs = update.callback_query.edit_message_text.call_args
    markup = call_kwargs.kwargs.get("reply_markup") or call_kwargs[1].get("reply_markup")
    buttons = [btn.text for row in markup.inline_keyboard for btn in row]
    assert "15min" in buttons
    assert "30min" in buttons
    assert "1hr" in buttons
    assert "3hr" in buttons


async def test_notify_sess_shows_checkmarks_for_existing():
    """Already-subscribed presets show ✅."""
    repo = AsyncMock()
    repo.has_notification = AsyncMock(side_effect=lambda tid, s, r, sk, m: m == 30)

    update = _make_update("notify:sess:race:16")
    context = _make_context(repo=repo)

    await _notify_sess(update, context)

    call_kwargs = update.callback_query.edit_message_text.call_args
    markup = call_kwargs.kwargs.get("reply_markup") or call_kwargs[1].get("reply_markup")
    buttons = [btn.text for row in markup.inline_keyboard for btn in row]
    assert "✅ 30min" in buttons
    assert "15min" in buttons  # not checked
    update.callback_query.answer.assert_awaited_once()


async def test_notify_set_subscribes(repo):
    """notify:set creates a subscription when none exists."""
    race = _make_race()
    await repo.save_schedule(2026, [race])

    update = _make_update("notify:set:30:qualifying:16")
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])
    jq.run_once = MagicMock()
    context = _make_context(repo=repo, jq=jq)

    await _notify_set(update, context)

    # Verify subscription was created
    has = await repo.has_notification(12345, 2026, 16, "qualifying", 30)
    assert has is True

    # Answer should confirm with toast — exactly once (no double-answer)
    update.callback_query.answer.assert_awaited_once()
    answer_text = update.callback_query.answer.call_args[0][0]
    assert "Reminder set" in answer_text


async def test_notify_set_unsubscribes(repo):
    """notify:set removes subscription when it already exists."""
    race = _make_race()
    await repo.save_schedule(2026, [race])

    fire_at = datetime.now(UTC) + timedelta(hours=1)
    sub = NotificationSubscription(
        telegram_id=12345,
        season=2026,
        round=16,
        session_key="qualifying",
        minutes_before=30,
        fire_at=fire_at,
    )
    await repo.subscribe_notification(sub)

    update = _make_update("notify:set:30:qualifying:16")
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])
    jq.run_once = MagicMock()
    context = _make_context(repo=repo, jq=jq)

    await _notify_set(update, context)

    has = await repo.has_notification(12345, 2026, 16, "qualifying", 30)
    assert has is False

    # Answer should confirm removal — exactly once
    update.callback_query.answer.assert_awaited_once()
    answer_text = update.callback_query.answer.call_args[0][0]
    assert "Reminder removed" in answer_text


async def test_build_remind_view_single_round_auto_skip(repo):
    """Single round skips State A and shows State B directly (no Back button)."""
    race = _make_race(round_num=10)
    await repo.save_schedule(2026, [race])

    fire_at = datetime.now(UTC) + timedelta(hours=1)
    for sk, mins in [("race", 30), ("qualifying", 60)]:
        await repo.subscribe_notification(
            NotificationSubscription(
                telegram_id=100,
                season=2026,
                round=10,
                session_key=sk,
                minutes_before=mins,
                fire_at=fire_at,
            )
        )

    text, kb = await _build_remind_view(repo, 100)

    assert "R10" in text
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("🗑" in b for b in buttons)
    cb_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert all(d.startswith("notify:del:") for d in cb_data)
    assert not any("Back" in b for b in buttons)


async def test_build_remind_view_multi_round_state_a(repo):
    """Multiple rounds show State A overview with per-round buttons."""
    races = [_make_race(round_num=10), _make_race(round_num=11, days_ahead=17)]
    await repo.save_schedule(2026, races)

    fire_at = datetime.now(UTC) + timedelta(hours=1)
    for rnd in [10, 11]:
        await repo.subscribe_notification(
            NotificationSubscription(
                telegram_id=100,
                season=2026,
                round=rnd,
                session_key="race",
                minutes_before=30,
                fire_at=fire_at,
            )
        )

    text, kb = await _build_remind_view(repo, 100)

    assert "Active Reminders" in text
    cb_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert any(d.startswith("notify:list:") for d in cb_data)
    assert any("clearall" in d for d in cb_data)


async def test_notify_del_removes_and_rerenders(repo):
    """Deleting a reminder re-renders State B for the same round."""
    race = _make_race(round_num=10)
    await repo.save_schedule(2026, [race])

    fire_at = datetime.now(UTC) + timedelta(hours=1)
    sub1 = NotificationSubscription(
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    sub2 = NotificationSubscription(
        telegram_id=100,
        season=2026,
        round=10,
        session_key="qualifying",
        minutes_before=60,
        fire_at=fire_at,
    )
    sub1_id = await repo.subscribe_notification(sub1)
    await repo.subscribe_notification(sub2)

    update = _make_update(f"notify:del:{sub1_id}:10", user_id=100)
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])
    jq.run_once = MagicMock()
    context = _make_context(repo=repo, jq=jq)

    await _notify_del(update, context)

    update.callback_query.answer.assert_awaited_once()
    assert "removed" in update.callback_query.answer.call_args[0][0].lower()
    call_kwargs = update.callback_query.edit_message_text.call_args
    markup = call_kwargs.kwargs.get("reply_markup") or call_kwargs[1].get("reply_markup")
    buttons = [btn.text for row in markup.inline_keyboard for btn in row]
    assert any("Qualifying" in b for b in buttons)
    assert not any("Race — 30min" in b for b in buttons)


async def test_notify_del_last_shows_empty(repo):
    """Deleting the last reminder shows the empty message."""
    race = _make_race(round_num=10)
    await repo.save_schedule(2026, [race])

    fire_at = datetime.now(UTC) + timedelta(hours=1)
    sub = NotificationSubscription(
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=fire_at,
    )
    sub_id = await repo.subscribe_notification(sub)

    update = _make_update(f"notify:del:{sub_id}:10", user_id=100)
    jq = MagicMock()
    jq.get_jobs_by_name = MagicMock(return_value=[])
    jq.run_once = MagicMock()
    context = _make_context(repo=repo, jq=jq)

    await _notify_del(update, context)

    call_kwargs = update.callback_query.edit_message_text.call_args
    text = call_kwargs[0][0]
    assert "no active reminders" in text.lower()


async def test_notify_set_cap_rejects_at_limit(repo):
    """Subscribing at MAX_REMINDERS shows an alert and does not create."""
    race = _make_race(round_num=10)
    await repo.save_schedule(2026, [race])

    fire_at = datetime.now(UTC) + timedelta(hours=1)
    for i in range(MAX_REMINDERS):
        await repo.subscribe_notification(
            NotificationSubscription(
                telegram_id=100,
                season=2026,
                round=10,
                session_key=f"session_{i}",
                minutes_before=15 + i,
                fire_at=fire_at,
            )
        )

    update = _make_update("notify:set:30:race:10", user_id=100)
    context = _make_context(repo=repo)

    await _notify_set(update, context)

    update.callback_query.answer.assert_awaited_once()
    answer_text = update.callback_query.answer.call_args[0][0]
    assert "Limit reached" in answer_text
    assert update.callback_query.answer.call_args.kwargs.get("show_alert") is True


async def test_delete_notification_by_id_ownership_guard(pg_store):
    """Cannot delete another user's notification by ID."""
    sub = NotificationSubscription(
        telegram_id=100,
        season=2026,
        round=10,
        session_key="race",
        minutes_before=30,
        fire_at=datetime.now(UTC) + timedelta(hours=1),
    )
    sub_id = await pg_store.save_notification(sub)

    deleted = await pg_store.delete_notification_by_id(sub_id, telegram_id=999)
    assert deleted is False

    deleted = await pg_store.delete_notification_by_id(sub_id, telegram_id=100)
    assert deleted is True


async def test_bell_button_in_next_overview_keyboard():
    """next_overview_keyboard includes 🔔 Remind Me button."""
    from f1_bot.handlers.pagination import next_overview_keyboard

    kb = next_overview_keyboard(16, [16, 17, 18])
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    bell_buttons = [b for b in all_buttons if "🔔" in b.text]
    assert len(bell_buttons) == 1
    assert bell_buttons[0].callback_data == "notify:pick:16"
