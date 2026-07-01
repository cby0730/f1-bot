from telegram import LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

_HELP_TEXT = """
*F1 Bot Commands*

*Bot*
/start — Welcome message and command overview
/help — Show this command list

*Schedule*
/next — Next race overview + session filter buttons (FP1–Race)
/schedule — Full season race calendar
/countdown — Time remaining until the next race
/timezone — Set your timezone (e.g. /timezone Asia/Taipei)

*Standings*
/standings — WDC + WCC standings

*Results*
/results — Results overview + session filter (FP1–Race, round navigation)
/pitstops — Pit stop data (use ◀ ▶ buttons to navigate rounds)
/laps — Lap times with sector data (By-Lap / By-Driver view)

*Info*
/driver [name] — Driver profile
/circuit [name] — Circuit info

*Notifications*
/remind — Manage your session reminders
""".strip()

_WELCOME = (
    "Welcome to *F1 Bot*! Get Formula 1 race info, standings, and session results.\n\n"
    "Times are shown in *UTC* by default. Use /timezone to set your local timezone.\n\n"
    + _HELP_TEXT
    + "\n\n"
    "📊 *Data Sources*:\n"
    "• [Jolpica F1 API](https://github.com/jolpica/jolpica-f1) (Ergast)\n"
    "• [OpenF1 API](https://github.com/br-g/openf1)\n\n"
    "⭐ *Support this project*:\n"
    "If you like this bot, please give it a star on [GitHub](https://github.com/cby0730/f1-telegram-bot)!"
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        _WELCOME,
        parse_mode=ParseMode.MARKDOWN,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(_HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
