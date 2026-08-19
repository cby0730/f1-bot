from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import _esc
from f1_bot.formatting.timezone import TIMEZONE_REGIONS, is_valid_timezone, region_label
from f1_bot.handlers.context import resolve_context

_CB_REGION = "tz:region:"
_CB_SET = "tz:set:"


def _region_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Region menu.

    `callback_data` carries the stable slug while the button carries the translated
    label, so translating a label can never invalidate an in-flight keyboard.
    """
    rows = [
        [InlineKeyboardButton(region_label(region, lang), callback_data=f"{_CB_REGION}{region}")]
        for region in TIMEZONE_REGIONS
    ]
    return InlineKeyboardMarkup(rows)


def _city_keyboard(region: str, lang: str) -> InlineKeyboardMarkup:
    # City names stay literal — they are proper nouns, an explicit non-goal.
    cities = TIMEZONE_REGIONS.get(region, [])
    rows = [[InlineKeyboardButton(label, callback_data=f"{_CB_SET}{tz}")] for label, tz in cities]
    rows.append(
        [InlineKeyboardButton(t("common.back_prev", lang), callback_data=f"{_CB_REGION}__back__")]
    )
    return InlineKeyboardMarkup(rows)


async def timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    await update.effective_message.reply_text(
        t("settings.tz_picker", ctx.lang, tz=ctx.tz),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_region_keyboard(ctx.lang),
    )


async def timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)

    if query.data.startswith(_CB_REGION):
        region = query.data[len(_CB_REGION) :]
        if region == "__back__":
            await query.edit_message_text(
                t("settings.tz_picker_back", ctx.lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_region_keyboard(ctx.lang),
            )
        elif region not in TIMEZONE_REGIONS:
            await query.edit_message_text(
                t("common.invalid_selection", ctx.lang), parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                t("settings.tz_city", ctx.lang, region=region_label(region, ctx.lang)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_city_keyboard(region, ctx.lang),
            )

    elif query.data.startswith(_CB_SET):
        tz_name = query.data[len(_CB_SET) :]
        if not is_valid_timezone(tz_name):
            await query.edit_message_text(
                t("settings.tz_unknown_short", ctx.lang, tz=_esc(tz_name)),
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await _save_tz(repo, update.effective_user.id, tz_name, query, ctx.lang)


async def _save_tz(repo, telegram_id: int, tz_name: str, query, lang: str) -> None:
    # Single-column upsert: writing a whole UserPreference here would carry the
    # `language` field's default along and silently reset the user's language.
    await repo.set_user_timezone(telegram_id, tz_name)
    text = t("settings.tz_saved", lang, tz=tz_name)
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("timezone", timezone_handler))
    app.add_handler(CallbackQueryHandler(timezone_callback, pattern=r"^tz:"))
