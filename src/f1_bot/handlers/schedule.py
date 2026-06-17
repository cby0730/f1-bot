import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from f1_bot.formatting.messages import (
    format_countdown_msg,
    format_next_race,
    format_next_session,
    format_schedule,
    no_data_message,
)
from f1_bot.handlers.errors import CommandValidationError
from f1_bot.utils.sessions import find_next_sessions


def validate_and_parse_schedule_args(command: str, args: list[str], bounds: dict) -> int:
    if not args:
        return 1
    if len(args) > 1 or not args[0].isdigit():
        raise CommandValidationError(
            f"⚠️ Invalid argument format. Usage: `/{command} [limit (1-5)]`"
        )
    limit = int(args[0])
    if limit < 1 or limit > 5:
        raise CommandValidationError(
            f"⚠️ Limit must be between 1 and 5. Usage: `/{command} [limit (1-5)]`"
        )
    if command == "nextsprint":
        upcoming_sprints = len(bounds["sprint_rounds"]) - len(bounds["completed_sprint_rounds"])
        max_limit = upcoming_sprints
    else:
        max_limit = bounds["upcoming_rounds"]

    capped_limit = min(limit, max_limit) if max_limit > 0 else 1
    return capped_limit


async def _get_context(context: ContextTypes.DEFAULT_TYPE):
    repo = context.bot_data["repo"]
    season = datetime.date.today().year
    return repo, season


async def next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo, season = await _get_context(context)
    user_tz = await repo.get_user_timezone(update.effective_user.id)

    races = await repo.get_schedule(season)
    if not races:
        jolpica = context.bot_data["jolpica"]
        try:
            races = await jolpica.get_current_schedule()
            if races:
                await repo.save_schedule(season, races)
        except Exception:
            pass

    if not races:
        await update.effective_message.reply_text(no_data_message("upcoming race"))
        return

    try:
        from f1_bot.handlers.results import _get_bounds

        bounds = await _get_bounds(repo, season, races)
        limit = validate_and_parse_schedule_args("next", context.args or [], bounds)
    except CommandValidationError as e:
        await update.effective_message.reply_text(str(e), parse_mode=ParseMode.MARKDOWN)
        return

    import datetime as dt_module

    today = dt_module.date.today()
    upcoming = [r for r in races if r.date >= today]
    if not upcoming:
        await update.effective_message.reply_text(no_data_message("upcoming race"))
        return

    selected = upcoming[:limit]
    messages = [format_next_race(race, user_tz) for race in selected]

    from f1_bot.handlers.results import send_merged_messages

    await send_merged_messages(update, messages)


async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo, season = await _get_context(context)
    user_tz = await repo.get_user_timezone(update.effective_user.id)
    races = await repo.get_schedule(season)
    if not races:
        await update.effective_message.reply_text(no_data_message("schedule"))
        return
    await update.effective_message.reply_text(
        format_schedule(races, user_tz), parse_mode=ParseMode.MARKDOWN
    )


async def countdown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo, season = await _get_context(context)
    user_tz = await repo.get_user_timezone(update.effective_user.id)
    race = await repo.get_next_race(season)
    if not race:
        await update.effective_message.reply_text(no_data_message("upcoming race"))
        return
    await update.effective_message.reply_text(
        format_countdown_msg(race, user_tz), parse_mode=ParseMode.MARKDOWN
    )


async def _next_session_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    group: str,
    label: str,
    command: str,
) -> None:
    repo, season = await _get_context(context)
    user_tz = await repo.get_user_timezone(update.effective_user.id)

    races = await repo.get_schedule(season)
    if not races:
        jolpica = context.bot_data["jolpica"]
        try:
            races = await jolpica.get_current_schedule()
            if races:
                await repo.save_schedule(season, races)
        except Exception:
            pass

    if not races:
        await update.effective_message.reply_text(no_data_message(f"upcoming {label} session"))
        return

    try:
        from f1_bot.handlers.results import _get_bounds

        bounds = await _get_bounds(repo, season, races)
        limit = validate_and_parse_schedule_args(command, context.args or [], bounds)
    except CommandValidationError as e:
        await update.effective_message.reply_text(str(e), parse_mode=ParseMode.MARKDOWN)
        return

    entries = find_next_sessions(races, group, limit=limit)
    if not entries:
        await update.effective_message.reply_text(no_data_message(f"upcoming {label} session"))
        return

    messages = [format_next_session(entry, user_tz) for entry in entries]

    from f1_bot.handlers.results import send_merged_messages

    await send_merged_messages(update, messages)


async def next_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _next_session_handler(update, context, "all", "F1", "nextsession")


async def next_practice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _next_session_handler(update, context, "practice", "practice", "nextpractice")


async def next_qualifying_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _next_session_handler(update, context, "qualifying", "qualifying", "nextqualifying")


async def next_sprint_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _next_session_handler(update, context, "sprint", "sprint", "nextsprint")


def register(app: Application) -> None:
    app.add_handler(CommandHandler("next", next_handler))
    app.add_handler(CommandHandler("nextsession", next_session_handler))
    app.add_handler(CommandHandler("nextpractice", next_practice_handler))
    app.add_handler(CommandHandler("nextqualifying", next_qualifying_handler))
    app.add_handler(CommandHandler("nextsprint", next_sprint_handler))
    app.add_handler(CommandHandler("schedule", schedule_handler))
    app.add_handler(CommandHandler("countdown", countdown_handler))
