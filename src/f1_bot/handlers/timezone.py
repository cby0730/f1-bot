from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.messages import _esc
from f1_bot.formatting.timezone import TIMEZONE_REGIONS, is_valid_timezone
from f1_bot.models.user import UserPreference

_CB_REGION = "tz:region:"
_CB_SET = "tz:set:"


def _region_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(region, callback_data=f"{_CB_REGION}{region}")]
        for region in TIMEZONE_REGIONS
    ]
    return InlineKeyboardMarkup(rows)


def _city_keyboard(region: str) -> InlineKeyboardMarkup:
    cities = TIMEZONE_REGIONS.get(region, [])
    rows = [[InlineKeyboardButton(label, callback_data=f"{_CB_SET}{tz}")] for label, tz in cities]
    rows.append([InlineKeyboardButton("« Back", callback_data=f"{_CB_REGION}__back__")])
    return InlineKeyboardMarkup(rows)


async def timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]

    # Direct input: /timezone Asia/Taipei
    if context.args:
        tz_name = context.args[0]
        if not is_valid_timezone(tz_name):
            await update.effective_message.reply_text(
                f"❌ Unknown timezone: `{_esc(tz_name)}`\n\n"
                "Use a standard IANA name like `Asia/Taipei`, `Europe/London`, `America/New_York`.\n"
                "Or just type /timezone to pick from a list.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await _save_tz(repo, update.effective_user.id, tz_name, update)
        return

    # Show region picker
    current_tz = await repo.get_user_timezone(update.effective_user.id)
    await update.effective_message.reply_text(
        f"🌍 *Set your timezone*\n\nCurrent: `{current_tz}`\n\nChoose your region:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_region_keyboard(),
    )


async def timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]

    if query.data.startswith(_CB_REGION):
        region = query.data[len(_CB_REGION) :]
        if region == "__back__":
            await query.edit_message_text(
                "🌍 *Set your timezone*\n\nChoose your region:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_region_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"🌍 *{region}* — pick a city:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_city_keyboard(region),
            )

    elif query.data.startswith(_CB_SET):
        tz_name = query.data[len(_CB_SET) :]
        await _save_tz(repo, update.effective_user.id, tz_name, update, via_callback=query)


async def _save_tz(repo, telegram_id: int, tz_name: str, update, via_callback=None) -> None:
    pref = UserPreference(telegram_id=telegram_id, timezone=tz_name)
    await repo.upsert_user_preference(pref)
    text = f"✅ Timezone set to *{tz_name}*\n\nRace times will now be shown in your local time."
    if via_callback:
        await via_callback.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("timezone", timezone_handler))
    app.add_handler(CallbackQueryHandler(timezone_callback, pattern=r"^tz:"))
