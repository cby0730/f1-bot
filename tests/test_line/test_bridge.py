"""LINE events through the real Telegram handlers, against a real database."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from telegram.ext import Application, ExtBot

from f1_bot.formatting.i18n import t
from f1_bot.handlers import register_all_handlers
from f1_bot.line.bridge import LINE_DEFAULT_LANG, LineBridge, command_for_text
from f1_bot.line.render import markdown_to_plain
from f1_bot.models.notification import NotificationSubscription

LINE_USER = "U" + "a" * 32


class _CapturingClient:
    def __init__(self) -> None:
        self.replies: list[tuple[str, list[dict]]] = []

    async def reply(self, reply_token: str, messages: list[dict]) -> None:
        self.replies.append((reply_token, messages))


@pytest_asyncio.fixture
async def line_app(repo):
    app = Application.builder().token("123:TEST").build()
    register_all_handlers(app)
    app.bot_data["repo"] = repo
    # The bridge never calls Telegram; skip initialize()'s getMe round-trip.
    with patch.object(ExtBot, "initialize", AsyncMock()):
        await app.initialize()
    yield app
    with patch.object(ExtBot, "shutdown", AsyncMock()):
        await app.shutdown()


@pytest.fixture
def client():
    return _CapturingClient()


@pytest.fixture
def bridge(line_app, client):
    return LineBridge(line_app, client)


def _text(text: str, user: str = LINE_USER) -> dict:
    return {
        "type": "message",
        "replyToken": "rt",
        "source": {"type": "user", "userId": user},
        "message": {"type": "text", "id": "1", "text": text},
    }


def _postback(data: str) -> dict:
    return {
        "type": "postback",
        "replyToken": "rt",
        "source": {"type": "user", "userId": LINE_USER},
        "postback": {"data": data},
    }


def _only_reply(client) -> list[dict]:
    assert len(client.replies) == 1
    token, messages = client.replies[0]
    assert token == "rt"
    return messages


def _postbacks(flex: dict) -> list[str]:
    return [
        b["action"]["data"] for row in flex["contents"]["body"]["contents"] for b in row["contents"]
    ]


@pytest.mark.parametrize(
    ("text", "command"),
    [
        ("/next", "next"),
        ("next", "next"),
        ("  Standings please", "standings"),
        ("/SETTINGS", "settings"),
        ("hello", "start"),
        ("", "start"),
        ("/unknown", "start"),
    ],
)
def test_command_for_text(text, command):
    assert command_for_text(text) == command


async def test_first_contact_creates_negative_id_with_zh_hant(bridge, client, repo):
    await bridge.handle_event(_text("/settings"))

    user_id, created = await repo.get_or_create_line_user(LINE_USER)
    assert user_id < 0 and not created
    assert await repo.get_user_language(user_id) == LINE_DEFAULT_LANG

    text, flex = _only_reply(client)
    assert text == {
        "type": "text",
        "text": markdown_to_plain(t("settings.hub", LINE_DEFAULT_LANG)),
    }
    assert "*" not in text["text"]
    assert flex["type"] == "flex"
    assert _postbacks(flex) == ["set:tz", "set:lang"]


async def test_follow_sends_welcome_menu_as_plain_text(bridge, client):
    await bridge.handle_event(
        {"type": "follow", "replyToken": "rt", "source": {"type": "user", "userId": LINE_USER}}
    )
    text, flex = _only_reply(client)
    assert "*" not in text["text"]
    assert "GitHub: https://github.com/cby0730/f1-bot" in text["text"]
    assert _postbacks(flex) == [
        "start:next",
        "start:schedule",
        "start:results",
        "start:standings",
        "start:driver",
        "start:circuit",
        "start:remind",
        "start:settings",
    ]


async def test_unrecognised_text_and_stickers_open_start_menu(bridge, client):
    await bridge.handle_event(_text("hi there"))
    sticker = _text("")
    sticker["message"] = {"type": "sticker", "id": "2"}
    await bridge.handle_event(sticker)
    assert len(client.replies) == 2
    for _, messages in client.replies:
        assert "start:next" in _postbacks(messages[1])


async def test_postback_edit_arrives_as_new_message_and_language_switch_persists(
    bridge, client, repo
):
    await bridge.handle_event(_postback("set:lang"))
    _, picker = _only_reply(client)
    assert _postbacks(picker) == ["lang:set:en", "lang:set:zh-Hant"]

    client.replies.clear()
    await bridge.handle_event(_postback("lang:set:en"))
    (confirmation,) = _only_reply(client)
    assert "English" in confirmation["text"]
    user_id, _ = await repo.get_or_create_line_user(LINE_USER)
    assert await repo.get_user_language(user_id) == "en"


async def test_alert_becomes_text_message(bridge, client):
    # No schedule in the DB: the /next callback answers with a show_alert popup.
    await bridge.handle_event(_postback("next:back:_:1"))
    assert _only_reply(client) == [
        {"type": "text", "text": t("common.schedule_unavailable", LINE_DEFAULT_LANG)}
    ]


async def test_command_without_slash_reaches_handler(bridge, client):
    await bridge.handle_event(_text("Standings"))
    assert _only_reply(client) == [
        {
            "type": "text",
            "text": t(
                "common.no_data",
                LINE_DEFAULT_LANG,
                what=t("common.noun_standings", LINE_DEFAULT_LANG),
            ),
        }
    ]


async def test_two_line_users_get_distinct_ids(bridge, repo):
    await bridge.handle_event(_text("/start"))
    await bridge.handle_event(_text("/start", user="U" + "b" * 32))
    a, _ = await repo.get_or_create_line_user(LINE_USER)
    b, _ = await repo.get_or_create_line_user("U" + "b" * 32)
    assert {a, b} == {-1, -2}


async def test_unfollow_removes_reminders_without_replying(bridge, client, repo):
    user_id, _ = await repo.get_or_create_line_user(LINE_USER)
    await repo.subscribe_notification(
        NotificationSubscription(
            telegram_id=user_id,
            season=2026,
            round=1,
            session_key="race",
            minutes_before=30,
            fire_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await bridge.handle_event({"type": "unfollow", "source": {"type": "user", "userId": LINE_USER}})

    assert await repo.get_user_notifications(user_id, 2026) == []
    assert client.replies == []


async def test_event_without_user_is_ignored(bridge, client, repo):
    event = _text("/start")
    event["source"] = {"type": "group", "groupId": "C1"}
    await bridge.handle_event(event)
    assert client.replies == []
