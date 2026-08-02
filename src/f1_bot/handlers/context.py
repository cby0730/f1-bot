"""Per-request language + timezone resolution (Telegram platform layer).

Lives here, not in `formatting/`, because it reads a Telegram `Update`. Every
handler goes through this one seam so the priority rule exists in exactly one
place.
"""

from telegram import Update

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.i18n import DEFAULT_LANG


async def resolve_context(update: Update, repo, default_lang: str = DEFAULT_LANG) -> RenderContext:
    """Resolve the render context for the user behind `update`.

    Order is **DB preference > platform default** — two layers, not three. There is
    deliberately no `language_code` auto-detection layer: `language_code` is the
    user's *client UI* language, not a reading preference, and because the
    `language` column is `NOT NULL DEFAULT 'en'` every existing row already reads
    as English, so a middle layer would never fire for anyone who has ever run
    `/timezone`. See the spec's "Rollout & first-run behavior".

    `default_lang` is a **parameter**: Telegram passes `en`; a future LINE adapter
    passes `zh-Hant` without touching the core.
    """
    user = update.effective_user if isinstance(update, Update) else None
    if user is None:
        return RenderContext(lang=default_lang, tz="UTC")
    pref = await repo.get_user_preference(user.id)
    if pref:
        return RenderContext(lang=pref.language, tz=pref.timezone)
    return RenderContext(lang=default_lang, tz="UTC")
