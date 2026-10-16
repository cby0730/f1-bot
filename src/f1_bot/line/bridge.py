"""Run LINE events through the existing Telegram handlers.

Handlers talk to Telegram only through the ``Update`` they receive
(``reply_text`` / ``edit_message_text`` / ``answer``), and PTB binds those
shortcuts to the bot the ``Update`` was deserialised with. So each LINE event is
rewritten into the ``Update`` the equivalent Telegram interaction would produce,
bound to a ``_RecordingBot``, and processed by the same ``Application``. What the
handlers "sent" is then rendered as a single LINE reply — reply tokens are
single-use, so all output for one event must go out in one call.
"""

import time

import structlog
from telegram import Update
from telegram._utils.defaultvalue import DefaultValue
from telegram.ext import Application

from f1_bot.formatting.i18n import COMMAND_ORDER
from f1_bot.line.client import LineClient
from f1_bot.line.render import MAX_MESSAGES, Output, to_line_messages

log = structlog.get_logger(__name__)

# Locked per-platform default (roadmap-line-adapter.md): written as the user's DB
# preference on first contact, so every existing read path picks it up.
LINE_DEFAULT_LANG = "zh-Hant"

_COMMANDS = frozenset(COMMAND_ORDER)


class _RecordingBot:
    """Stands in for ``telegram.Bot`` on bridged updates and records what is sent."""

    defaults = None
    # CommandHandler compares a "/cmd@name" suffix against this; LINE text never has one.
    username = "line"

    def __init__(self) -> None:
        self.outputs: list[Output] = []

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None, **_):
        self._record(text, parse_mode, reply_markup)

    async def edit_message_text(self, text, parse_mode=None, reply_markup=None, **_):
        # LINE cannot edit a sent message, so an edit arrives as a new one.
        self._record(text, parse_mode, reply_markup)

    async def answer_callback_query(self, callback_query_id, text=None, **_):
        if text:
            self.outputs.append(Output(text))

    def _record(self, text, parse_mode, reply_markup) -> None:
        self.outputs.append(
            Output(text, DefaultValue.get_value(parse_mode), DefaultValue.get_value(reply_markup))
        )


def command_for_text(text: str) -> str:
    """``/next``, ``next`` and ``Next`` all mean /next; anything else opens /start."""
    words = text.split(maxsplit=1)
    word = words[0].lstrip("/").lower() if words else ""
    return word if word in _COMMANDS else "start"


def _identity(user_id: int) -> tuple[dict, dict]:
    user = {"id": user_id, "is_bot": False, "first_name": "LINE"}
    chat = {"id": user_id, "type": "private"}
    return user, chat


def command_update(user_id: int, command: str, bot: _RecordingBot) -> Update:
    user, chat = _identity(user_id)
    text = f"/{command}"
    message = {
        "message_id": 0,
        "date": int(time.time()),
        "chat": chat,
        "from": user,
        "text": text,
        "entities": [{"type": "bot_command", "offset": 0, "length": len(text)}],
    }
    return Update.de_json({"update_id": 0, "message": message}, bot)


def postback_update(user_id: int, data: str, bot: _RecordingBot) -> Update:
    user, chat = _identity(user_id)
    # A non-zero date keeps PTB from treating the message as InaccessibleMessage.
    message = {"message_id": 0, "date": int(time.time()), "chat": chat, "text": ""}
    query = {"id": "line", "chat_instance": "line", "from": user, "data": data, "message": message}
    return Update.de_json({"update_id": 0, "callback_query": query}, bot)


class LineBridge:
    def __init__(self, app: Application, client: LineClient) -> None:
        self._app = app
        self._client = client

    async def handle_event(self, event: dict) -> None:
        line_user_id = event.get("source", {}).get("userId")
        if not line_user_id:
            return
        kind = event.get("type")
        if kind == "unfollow":
            user_id = await self._user_id(line_user_id)
            await self._app.bot_data["repo"].remove_dead_user(user_id)
            log.info("line_user_unfollowed", user_id=user_id)
            return
        if kind == "postback":
            make_update, payload = postback_update, event["postback"]["data"]
        elif kind in ("message", "follow"):
            # follow carries no message, and non-text messages have no text: both → /start.
            message = event.get("message", {})
            text = message.get("text", "") if message.get("type") == "text" else ""
            make_update, payload = command_update, command_for_text(text)
        else:
            return

        user_id = await self._user_id(line_user_id)
        bot = _RecordingBot()
        await self._app.process_update(make_update(user_id, payload, bot))

        messages = to_line_messages(bot.outputs)
        if len(messages) > MAX_MESSAGES:
            log.warning("line_reply_truncated", produced=len(messages), sent=MAX_MESSAGES)
            messages = messages[:MAX_MESSAGES]
        if messages:
            await self._client.reply(event["replyToken"], messages)

    async def _user_id(self, line_user_id: str) -> int:
        repo = self._app.bot_data["repo"]
        user_id, created = await repo.get_or_create_line_user(line_user_id)
        if created:
            await repo.set_user_language(user_id, LINE_DEFAULT_LANG)
        return user_id
