"""/language command + `lang:` callback.

The picker is single-level (two shipped languages, no drill-down). The load-bearing
behaviours: it confirms in the language the user just *chose* (not the old one),
validates every code against `SHIPPED_LANGS`, writes nothing on a spoofed callback,
and answers its callback exactly once.
"""

from unittest.mock import AsyncMock, MagicMock

from f1_bot.formatting.i18n import SHIPPED_LANGS
from f1_bot.handlers.language import language_callback, language_handler, language_keyboard

# NOTE (history): these tests originally xfailed a real production bug — `t(key,
# lang, **kwargs)` named its second parameter `lang`, colliding with the `{lang}`
# placeholder that every `settings.lang_*` template interpolates, so every
# `t("settings.lang_*", ctx.lang, lang=...)` site crashed with
# `TypeError: t() got multiple values for argument 'lang'` and the ENTIRE /language
# command was dead. It is now FIXED: `t`'s signature is `def t(key, lang, /, **kwargs)`
# (positional-only `lang`), so the confirmation/picker/error paths interpolate `{lang}`
# cleanly. The xfail markers have been removed accordingly — the assertions below
# (always the CORRECT, un-weakened behaviour) now pass outright.


def _cmd(repo, args=None):
    """A command-style (update, context) pair. `language_handler` resolves context
    via `resolve_context`, which returns the default (en) for a non-`Update` mock —
    exactly what we want here (current language = en)."""
    update = MagicMock()
    update.effective_user.id = 123
    update.effective_message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot_data = {"repo": repo}
    context.args = args or []
    return update, context


def _callback(repo, data):
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = data
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 123
    context = MagicMock()
    context.bot_data = {"repo": repo}
    return update, context, query


# --- 17. Picker lists both shipped languages, marks the current -------------


def test_picker_lists_both_languages_and_marks_current():
    """The keyboard has one button per shipped language, the current one ticked,
    each named in its *own* language.

    WHY: a user stranded in a language they cannot read must still recognise their
    own language and their current selection to escape.
    """
    kb = language_keyboard("en").inline_keyboard

    assert len(kb) == len(SHIPPED_LANGS) == 2
    buttons = [row[0] for row in kb]
    assert buttons[0].text == "✅ English"  # current
    assert buttons[0].callback_data == "lang:set:en"
    assert buttons[1].text == "繁體中文"  # not current -> no tick, named in itself
    assert buttons[1].callback_data == "lang:set:zh-Hant"

    # And when zh-Hant is current, the tick moves.
    kb_zh = language_keyboard("zh-Hant").inline_keyboard
    assert kb_zh[0][0].text == "English"
    assert kb_zh[1][0].text == "✅ 繁體中文"


async def test_handler_no_args_shows_picker():
    """Bare `/language` renders the picker header (`settings.lang_picker`).

    WHY (regression guard): that header interpolates `{lang}` via
    `t("settings.lang_picker", ctx.lang, lang=...)`. If `t`'s signature stops being
    positional-only (`def t(key, lang, /, ...)`), the keyword `lang=` collides with
    the positional `ctx.lang` and the whole command raises `TypeError` before a
    reply is ever sent — so this awaited-once assertion fails loudly.
    """
    repo = MagicMock()
    update, context = _cmd(repo)

    await language_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once()
    kb = update.effective_message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard
    assert {row[0].callback_data for row in kb} == {"lang:set:en", "lang:set:zh-Hant"}


# --- 18. Set via callback + confirm in the NEW language ---------------------


async def test_callback_set_persists_and_confirms_in_new_language():
    """`lang:set:zh-Hant` saves zh-Hant and the confirmation is in Chinese.

    WHY: confirming in the *old* language would be the one message guaranteed
    unreadable to the user who just switched away from it.

    WHY (regression guard): the confirmation renders `settings.lang_saved`, which
    interpolates `{lang}`. This path only produces Chinese text if
    `t("settings.lang_saved", code, lang=...)` succeeds — which requires `t`'s
    `lang` param to stay positional-only. Revert the `/` and this raises TypeError.
    """
    repo = MagicMock()
    repo.set_user_language = AsyncMock()
    update, context, query = _callback(repo, "lang:set:zh-Hant")

    await language_callback(update, context)

    repo.set_user_language.assert_awaited_once_with(123, "zh-Hant")
    text = query.edit_message_text.await_args.args[0]
    assert "語言已設定" in text  # Chinese confirmation, not "Language set to"
    assert "繁體中文" in text


# --- 19. Direct form /language zh-Hant --------------------------------------


async def test_direct_form_valid_code_saves():
    """`/language zh-Hant` (direct form) saves and confirms in Chinese.

    WHY (regression guard): same `settings.lang_saved` `{lang}` interpolation as the
    callback path — asserting the Chinese confirmation here catches a reverted
    positional-only `t()` signature on the command (not just the button) route.
    """
    repo = MagicMock()
    repo.set_user_language = AsyncMock()
    update, context = _cmd(repo, args=["zh-Hant"])

    await language_handler(update, context)

    repo.set_user_language.assert_awaited_once_with(123, "zh-Hant")
    text = update.effective_message.reply_text.await_args.args[0]
    assert "語言已設定" in text


async def test_direct_form_unknown_code_rejected_no_write():
    """`/language fr` is validated against SHIPPED_LANGS: error, no write.

    WHY: a hand-typed code must not persist an unsupported language.

    WHY (regression guard): the rejection renders `settings.lang_unknown`, which
    also interpolates `{lang}` (the offending code). This exercises the third and
    last interpolation site, so a reverted positional-only `t()` is caught on the
    error path too, not only the happy paths.
    """
    repo = MagicMock()
    repo.set_user_language = AsyncMock()
    update, context = _cmd(repo, args=["fr"])

    await language_handler(update, context)

    repo.set_user_language.assert_not_called()
    text = update.effective_message.reply_text.await_args.args[0]
    assert "Unknown language" in text or "❌" in text


# --- 20. Callback guard against spoofed codes ------------------------------


async def test_callback_unknown_code_invalid_selection_no_write():
    """A crafted `lang:set:xx` answers "Invalid selection", crashes nothing, writes
    nothing.

    WHY: callback data is spoofable; an unknown code is a hostile/stale input, not
    a language to persist.
    """
    repo = MagicMock()
    repo.set_user_language = AsyncMock()
    update, context, query = _callback(repo, "lang:set:xx")

    await language_callback(update, context)

    repo.set_user_language.assert_not_called()
    text = query.edit_message_text.await_args.args[0]
    assert "Invalid selection" in text


# --- 21. answer() discipline ------------------------------------------------


async def test_callback_answers_exactly_once():
    """The `lang:` callback calls `query.answer()` exactly once.

    WHY: documented repo-wide convention — double-answering a callback query is a
    PTB error and a UI glitch.

    Driven through the unknown-code path deliberately: it exercises the real
    callback (answer -> validate -> edit) and asserts the answer-once property in
    isolation, independent of the `{lang}` interpolation on the save/picker paths.
    """
    repo = MagicMock()
    repo.set_user_language = AsyncMock()
    update, context, query = _callback(repo, "lang:set:xx")

    await language_callback(update, context)

    assert query.answer.await_count == 1
    repo.set_user_language.assert_not_called()
