"""Tests for notification handler — /remind and notify: callback flow."""

from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from f1_bot.handlers.notifications import _notify_pick, _notify_sess, _notify_set, _remind_command
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
    """When reminders exist, /remind shows grouped list."""
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

    text = update.effective_message.reply_text.call_args[0][0]
    assert "Active Reminders" in text
    assert "Race" in text
    assert "30min" in text


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


async def test_bell_button_in_next_overview_keyboard():
    """next_overview_keyboard includes 🔔 Remind Me button."""
    from f1_bot.handlers.pagination import next_overview_keyboard

    kb = next_overview_keyboard(16, [16, 17, 18])
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    bell_buttons = [b for b in all_buttons if "🔔" in b.text]
    assert len(bell_buttons) == 1
    assert bell_buttons[0].callback_data == "notify:pick:16"
