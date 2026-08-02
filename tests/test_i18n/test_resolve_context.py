"""`resolve_context` — the single seam that decides a request's (lang, tz).

The resolution order is deliberately **two layers: DB preference > platform
default**. There is no `language_code` middle layer — dropping it is a recorded
design decision (see the spec's "Rollout & first-run behavior"), because coupling
auto-detection with a `NOT NULL DEFAULT 'en'` backfill silently pinned existing
users to English forever. These tests document that order so it is not
re-introduced.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from telegram import Chat, Message, Update, User

from f1_bot.formatting.i18n import DEFAULT_LANG
from f1_bot.handlers.context import resolve_context
from f1_bot.models.user import UserPreference


def _update(user_id: int = 555, language_code: str | None = None) -> Update:
    """A *real* Telegram Update.

    `resolve_context` guards with `isinstance(update, Update)`, so a MagicMock
    would be treated as "no user" and always return the default — masking exactly
    the DB-preference path these tests exercise. `language_code` is set on the
    Telegram user so we can prove the resolver ignores it.
    """
    user = User(id=user_id, is_bot=False, first_name="T", language_code=language_code)
    chat = Chat(id=user_id, type="private")
    message = Message(message_id=1, date=datetime.now(UTC), chat=chat, from_user=user)
    return Update(update_id=1, message=message)


# --- 8. Two-layer priority --------------------------------------------------


async def test_db_preference_wins():
    """A user with a stored preference gets that language and timezone.

    WHY: documents layer 1 — an explicit choice is authoritative.
    """
    repo = AsyncMock()
    repo.get_user_preference = AsyncMock(
        return_value=UserPreference(telegram_id=555, language="zh-Hant", timezone="Asia/Taipei")
    )

    ctx = await resolve_context(_update(), repo)

    assert ctx.lang == "zh-Hant"
    assert ctx.tz == "Asia/Taipei"


async def test_no_row_falls_back_to_default():
    """A user with no `user_preferences` row gets the platform default + UTC.

    WHY: documents layer 2 — the fallback when the user has never chosen.
    """
    repo = AsyncMock()
    repo.get_user_preference = AsyncMock(return_value=None)

    ctx = await resolve_context(_update(), repo)

    assert ctx.lang == DEFAULT_LANG == "en"
    assert ctx.tz == "UTC"


# --- 9. Platform-parameterized default -------------------------------------


async def test_default_lang_is_a_platform_parameter():
    """`default_lang="zh-Hant"` (a future LINE adapter) is honored for a no-row user.

    WHY: the default is the *platform's* property, passed in — not a constant
    baked into the resolver. LINE will default zh-Hant without touching this code.
    """
    repo = AsyncMock()
    repo.get_user_preference = AsyncMock(return_value=None)

    ctx = await resolve_context(_update(), repo, default_lang="zh-Hant")

    assert ctx.lang == "zh-Hant"
    assert ctx.tz == "UTC"


# --- 10. First-run: no silent English-pinning, no language_code sniffing ----


async def test_existing_row_never_set_language_reads_as_english():
    """A row whose `language` is the column default ('en') resolves to en — even
    when the Telegram client locale is zh-Hant.

    WHY: this is the adopted rollout. `language_code="zh-Hant"` on the Update is
    the client *UI* language, NOT a reading preference; `resolve_context` must not
    consult it (the rejected auto-detect trap). A user's row created by `/timezone`
    alone carries `language='en'` and stays English until they run `/language`.
    """
    repo = AsyncMock()
    repo.get_user_preference = AsyncMock(
        return_value=UserPreference(telegram_id=555, language="en", timezone="Asia/Taipei")
    )

    # Client locale is zh-Hant; the resolver must still return en from the DB row.
    ctx = await resolve_context(_update(language_code="zh-Hant"), repo)

    assert ctx.lang == "en"
    assert ctx.tz == "Asia/Taipei"
