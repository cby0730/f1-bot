"""Tests for /title — hidden alias of /standings; stale title:* still render the strip."""

import datetime
from unittest.mock import AsyncMock, MagicMock

from telegram import CallbackQuery, Chat, Message, Update, User

from f1_bot.handlers.title import title_callback, title_handler
from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Race


def _driver(did, given, family):
    return Driver(driver_id=did, given_name=given, family_name=family, nationality="British")


def _driver_standings():
    return [
        DriverStanding(
            position=1,
            points=310.0,
            wins=9,
            driver=_driver("verstappen", "Max", "Verstappen"),
            constructor_name="Red Bull",
        ),
        DriverStanding(
            position=2,
            points=258.0,
            wins=4,
            driver=_driver("norris", "Lando", "Norris"),
            constructor_name="McLaren",
        ),
    ]


def _constructor_standings():
    return [
        ConstructorStanding(
            position=1,
            points=500.0,
            wins=10,
            constructor=Constructor(constructor_id="mclaren", name="McLaren"),
        ),
        ConstructorStanding(
            position=2,
            points=480.0,
            wins=8,
            constructor=Constructor(constructor_id="ferrari", name="Ferrari"),
        ),
    ]


def _schedule():
    return [
        Race(
            season=2026,
            round=r,
            name=f"R{r}",
            circuit={
                "circuit_id": "c",
                "name": "Circ",
                "locality": "Town",
                "country": "Land",
            },
            date="2026-01-01",
        )
        for r in range(1, 5)
    ]


def _repo(driver_st=None, constructor_st=None, round_after=2):
    repo = MagicMock()
    repo.get_driver_standings = AsyncMock(return_value=driver_st or [])
    repo.get_constructor_standings = AsyncMock(return_value=constructor_st or [])
    repo.get_standings_round = AsyncMock(return_value=round_after)
    repo.get_schedule = AsyncMock(return_value=_schedule())
    repo.get_user_preference = AsyncMock(return_value=None)
    return repo


def _context(repo):
    ctx = MagicMock()
    ctx.bot_data = {"repo": repo}
    return ctx


def _update():
    update = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    return update


def _callback_update(data: str):
    bot = MagicMock()
    bot.answer_callback_query = AsyncMock(return_value=True)
    bot.edit_message_text = AsyncMock(return_value=True)
    user = User(id=7, first_name="T", is_bot=False)
    chat = Chat(id=7, type="private")
    msg = Message(message_id=1, date=datetime.datetime.now(datetime.UTC), chat=chat, from_user=user)
    msg.set_bot(bot)
    query = CallbackQuery(id="1", from_user=user, chat_instance="ci", data=data, message=msg)
    query.set_bot(bot)
    return Update(update_id=1, callback_query=query), bot


async def test_title_handler_renders_standings_view():
    """/title is an alias: standings table + strip, new keyboard uses standings:."""
    repo = _repo(driver_st=_driver_standings())
    update = _update()

    await title_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "Verstappen" in text
    assert "Driver Standings" in text
    kb = update.effective_message.reply_text.await_args.kwargs["reply_markup"]
    row = kb.inline_keyboard[0]
    assert row[0].callback_data == "standings:wdc"
    assert row[1].callback_data == "standings:wcc"


async def test_title_handler_empty_standings_short_circuits():
    repo = _repo(driver_st=[])
    update = _update()

    await title_handler(update, _context(repo))

    text = update.effective_message.reply_text.await_args.args[0]
    assert "⚠️" in text or "No standings" in text
    repo.get_standings_round.assert_not_called()
    repo.get_schedule.assert_not_called()


async def test_title_callback_wdc_uses_drivers_cutoff():
    repo = _repo(driver_st=_driver_standings())
    update, bot = _callback_update("title:wdc")

    await title_callback(update, _context(repo))

    bot.answer_callback_query.assert_awaited()
    repo.get_standings_round.assert_awaited_once_with(2026, "drivers")
    text = bot.edit_message_text.await_args.kwargs["text"]
    assert "Verstappen" in text


async def test_title_callback_wcc_uses_constructors_cutoff():
    """Stale title:wcc must still read the constructors snapshot — not 404, not drivers."""
    repo = _repo(constructor_st=_constructor_standings())
    update, bot = _callback_update("title:wcc")

    await title_callback(update, _context(repo))

    bot.answer_callback_query.assert_awaited()
    repo.get_standings_round.assert_awaited_once_with(2026, "constructors")
    text = bot.edit_message_text.await_args.kwargs["text"]
    assert "McLaren" in text
    kb = bot.edit_message_text.await_args.kwargs["reply_markup"]
    assert kb.inline_keyboard[0][0].callback_data == "standings:wdc"


async def test_title_callback_does_not_mutate_query_data():
    repo = _repo(driver_st=_driver_standings())
    update, _bot = _callback_update("title:wdc")

    await title_callback(update, _context(repo))

    assert update.callback_query.data == "title:wdc"


async def test_title_callback_swallows_bad_request():
    from telegram.error import BadRequest

    repo = _repo(driver_st=_driver_standings())
    update, bot = _callback_update("title:wdc")
    bot.edit_message_text = AsyncMock(side_effect=BadRequest("Message is not modified"))

    await title_callback(update, _context(repo))
    bot.answer_callback_query.assert_awaited()
    bot.edit_message_text.assert_awaited()
