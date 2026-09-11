"""Tests for the /start welcome message and eight-button menu."""

from unittest.mock import AsyncMock, MagicMock

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.i18n import COMMAND_ORDER, t
from f1_bot.handlers import start
from f1_bot.handlers.start import (
    _MENU,
    _menu_keyboard,
    _start_menu_callback,
    _welcome_text,
    start_handler,
)

_WELCOME_EN = _welcome_text("en")
_WELCOME_ZH = _welcome_text("zh-Hant")
_HIDDEN = ("help", "countdown", "title", "timezone", "language", "compare", "pitstops", "laps")
_EXPECTED_CALLBACKS = tuple(f"start:{token}" for token, _, _ in _MENU)
_SETTINGS_LABEL = "⚙️ Settings / 設定"


def test_welcome_has_no_slash_commands():
    """Welcome copy must not list slash commands (URLs may still contain '/')."""
    for lang, text in (("en", _WELCOME_EN), ("zh-Hant", _WELCOME_ZH)):
        for command in (*COMMAND_ORDER, *_HIDDEN):
            assert f"/{command}" not in text, f"/{command} leaked into {lang} welcome"


def test_welcome_mentions_bilingual_settings():
    assert "Settings / 設定" in _WELCOME_EN
    assert "Settings / 設定" in _WELCOME_ZH


def test_menu_keyboard_is_four_rows_of_two():
    kb = _menu_keyboard("en").inline_keyboard
    assert len(kb) == 4
    assert all(len(row) == 2 for row in kb)
    data = tuple(btn.callback_data for row in kb for btn in row)
    assert data == _EXPECTED_CALLBACKS


def test_menu_labels_nonempty_and_callback_data_within_64_bytes():
    for lang in ("en", "zh-Hant"):
        kb = _menu_keyboard(lang).inline_keyboard
        for row in kb:
            for btn in row:
                assert btn.text
                assert len(btn.callback_data.encode()) <= 64


def test_settings_button_is_bilingual_in_both_catalogs():
    assert t("start.btn_settings", "en") == _SETTINGS_LABEL
    assert t("start.btn_settings", "zh-Hant") == _SETTINGS_LABEL
    kb_en = _menu_keyboard("en").inline_keyboard
    kb_zh = _menu_keyboard("zh-Hant").inline_keyboard
    assert kb_en[3][1].text == _SETTINGS_LABEL
    assert kb_zh[3][1].text == _SETTINGS_LABEL


def test_zh_hant_menu_uses_chinese_labels():
    kb = _menu_keyboard("zh-Hant").inline_keyboard
    labels = [btn.text for row in kb for btn in row]
    assert labels[0] == t("start.btn_next", "zh-Hant")
    assert "下一場" in labels[0]
    assert labels[1] == t("start.btn_schedule", "zh-Hant")
    assert "賽曆" in labels[1]


def test_start_register_installs_start_and_menu_callback():
    """/help is not a command — typing it must not produce a welcome message."""
    registered_commands = set()
    patterns = []

    class App:
        def add_handler(self, h):
            commands = getattr(h, "commands", None)
            if commands:
                registered_commands.update(commands)
            pattern = getattr(h, "pattern", None)
            if pattern is not None:
                patterns.append(pattern.pattern if hasattr(pattern, "pattern") else str(pattern))

    start.register(App())
    assert registered_commands == {"start"}
    assert "^start:" in patterns


def _start_update():
    update = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot_data = {"repo": MagicMock()}
    return update, context


async def test_start_handler_sends_welcome_and_eight_buttons():
    update, context = _start_update()
    await start_handler(update, context)
    update.effective_message.reply_text.assert_awaited_once()
    args, kwargs = update.effective_message.reply_text.await_args
    assert "Welcome to *F1 Bot*" in args[0]
    assert "Settings / 設定" in args[0]
    kb = kwargs["reply_markup"].inline_keyboard
    assert len(kb) == 4
    data = [btn.callback_data for row in kb for btn in row]
    assert data == list(_EXPECTED_CALLBACKS)


def _callback(data: str):
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = data
    update = MagicMock()
    update.callback_query = query
    update.effective_message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot_data = {"repo": MagicMock()}
    return update, context, query


async def test_unknown_token_shows_invalid_selection_alert():
    update, context, query = _callback("start:bogus")
    await _start_menu_callback(update, context)
    query.answer.assert_awaited_once()
    kwargs = query.answer.await_args.kwargs
    assert kwargs.get("show_alert") is True
    assert kwargs.get("text") == t("common.invalid_selection", "en")
    update.effective_message.reply_text.assert_not_called()
    query.edit_message_text.assert_not_called()


async def test_known_token_answers_exactly_once_then_dispatches():
    """A missing answer() leaves the client spinner spinning."""
    update, context, query = _callback("start:settings")
    await _start_menu_callback(update, context)
    assert query.answer.await_count == 1
    assert query.answer.await_args.kwargs == {} or query.answer.await_args.args == ()
    update.effective_message.reply_text.assert_awaited_once()


async def test_start_settings_dispatch_does_not_edit_welcome():
    update, context, query = _callback("start:settings")
    await _start_menu_callback(update, context)
    query.edit_message_text.assert_not_called()
    text = update.effective_message.reply_text.await_args.args[0]
    assert "Settings" in text


async def test_zh_hant_start_handler_uses_chinese_welcome(monkeypatch):
    async def _zh_ctx(update, repo, default_lang="en"):
        return RenderContext(lang="zh-Hant", tz="UTC")

    monkeypatch.setattr("f1_bot.handlers.start.resolve_context", _zh_ctx)
    update, context = _start_update()
    await start_handler(update, context)
    text = update.effective_message.reply_text.await_args.args[0]
    assert "歡迎使用" in text
    kb = update.effective_message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard
    assert kb[3][1].text == _SETTINGS_LABEL
    assert "下一場" in kb[0][0].text
