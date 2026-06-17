"""Handlers for /pitstops and /laps — deep race data from Jolpica."""

import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from f1_bot.formatting.messages import format_laps, format_pitstops, no_data_message
from f1_bot.handlers.errors import CommandValidationError
from f1_bot.handlers.results import _get_bounds, send_merged_messages, validate_and_parse_args


async def pitstops_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    jolpica = context.bot_data["jolpica"]
    season = datetime.date.today().year

    races = await repo.get_schedule(season)
    if not races:
        try:
            races = await jolpica.get_current_schedule()
            if races:
                await repo.save_schedule(season, races)
        except Exception:
            pass

    if not races:
        await update.effective_message.reply_text(no_data_message("schedule"))
        return

    try:
        bounds = await _get_bounds(repo, season, races)
        limit, round_num = validate_and_parse_args("pitstops", context.args or [], bounds)

        target_rounds = []

        if round_num is not None:
            race = next((r for r in races if r.round == round_num), None)
            if not race:
                raise CommandValidationError(
                    f"⚠️ Invalid round number. The current season has only {bounds['total_rounds']} rounds."
                )
            if bounds["last_completed_round"] is None or round_num > bounds["last_completed_round"]:
                raise CommandValidationError(
                    f"⚠️ Round {round_num} ({race.name}) has not occurred yet."
                )
            target_rounds = [(round_num, race)]
    except CommandValidationError as e:
        await update.effective_message.reply_text(str(e), parse_mode=ParseMode.MARKDOWN)
        return

    if round_num is None:
        completed = (
            [r for r in races if r.round in range(1, bounds["last_completed_round"] + 1)]
            if bounds["last_completed_round"]
            else []
        )
        completed.sort(key=lambda r: r.round, reverse=True)

        if not completed:
            await update.effective_message.reply_text(no_data_message("pit stop data"))
            return

        selected_races = completed[:limit]
        target_rounds = [(r.round, r) for r in selected_races]

    messages = []
    for r_num, race in target_rounds:
        stops = await jolpica.get_pit_stops(str(season), str(r_num))
        if stops:
            messages.append(format_pitstops(race, stops, r_num))

    if not messages:
        await update.effective_message.reply_text(no_data_message("pit stop data"))
        return

    await send_merged_messages(update, messages)


async def laps_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    jolpica = context.bot_data["jolpica"]
    season = datetime.date.today().year

    races = await repo.get_schedule(season)
    if not races:
        try:
            races = await jolpica.get_current_schedule()
            if races:
                await repo.save_schedule(season, races)
        except Exception:
            pass

    if not races:
        await update.effective_message.reply_text(no_data_message("schedule"))
        return

    try:
        bounds = await _get_bounds(repo, season, races)
        limit, round_num = validate_and_parse_args("laps", context.args or [], bounds)

        target_rounds = []

        if round_num is not None:
            race = next((r for r in races if r.round == round_num), None)
            if not race:
                raise CommandValidationError(
                    f"⚠️ Invalid round number. The current season has only {bounds['total_rounds']} rounds."
                )
            if bounds["last_completed_round"] is None or round_num > bounds["last_completed_round"]:
                raise CommandValidationError(
                    f"⚠️ Round {round_num} ({race.name}) has not occurred yet."
                )
            target_rounds = [(round_num, race)]
    except CommandValidationError as e:
        await update.effective_message.reply_text(str(e), parse_mode=ParseMode.MARKDOWN)
        return

    if round_num is None:
        completed = (
            [r for r in races if r.round in range(1, bounds["last_completed_round"] + 1)]
            if bounds["last_completed_round"]
            else []
        )
        completed.sort(key=lambda r: r.round, reverse=True)

        if not completed:
            await update.effective_message.reply_text(no_data_message("lap data"))
            return

        selected_races = completed[:limit]
        target_rounds = [(r.round, r) for r in selected_races]

    messages = []
    for r_num, race in target_rounds:
        laps = await jolpica.get_fastest_laps(str(season), str(r_num))
        if laps:
            messages.append(format_laps(race, laps, r_num))

    if not messages:
        await update.effective_message.reply_text(no_data_message("lap data"))
        return

    await send_merged_messages(update, messages)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("pitstops", pitstops_handler))
    app.add_handler(CommandHandler("laps", laps_handler))
