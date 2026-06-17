from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

_HELP_TEXT = """
*F1 Bot Commands*

*Bot*
/start — Welcome message and command overview
/help — Show this command list

*Schedule*
/next [N] — Next N races (default 1) + countdown + session times
/nextsession [N] — Next N F1 sessions (default 1): practice, qualifying, sprint, or race
/nextpractice [N] — Next N practice sessions (default 1)
/nextqualifying [N] — Next N qualifying or sprint qualifying sessions (default 1)
/nextsprint [N] — Next N sprint-related sessions (default 1)
/schedule — Full season race calendar
/countdown — Time remaining until the next race
/timezone — Set your timezone (e.g. /timezone Asia/Taipei)

*Standings*
/standings — WDC + WCC standings

*Results*
/results [N or rN] — Race result(s) (N for last N, rN for specific round)
/qualifying [N or rN] — Qualifying result(s)
/sprint [N or rN] — Sprint result(s)
/sessionresult [N or rN] [session] — Result(s) for FP, qualifying, sprint, or race
/pitstops [N or rN] — Pit stop data
/laps [N or rN] — Lap time sample

*Info*
/driver [name] — Driver profile
/circuit [name] — Circuit info
""".strip()

_WELCOME = (
    "Welcome to *F1 Bot*! Get Formula 1 race info, standings, and session results.\n\n"
    "Times are shown in *UTC* by default. Use /timezone to set your local timezone.\n\n"
    + _HELP_TEXT
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(_WELCOME, parse_mode=ParseMode.MARKDOWN)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(_HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
