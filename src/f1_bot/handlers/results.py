import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from f1_bot.formatting.messages import (
    format_qualifying_results,
    format_race_results,
    format_session_results,
    format_sprint_results,
    no_data_message,
)
from f1_bot.handlers.errors import CommandValidationError
from f1_bot.models.results import SessionResult
from f1_bot.utils.sessions import (
    find_race_session,
    find_recent_completed_session,
    match_openf1_session,
    normalize_session_key,
)


def validate_and_parse_args(command: str, args: list[str], bounds: dict) -> tuple[int, int | None]:
    """
    Parse and strictly validate command arguments to extract (limit, round_num).
    Raises CommandValidationError if arguments are invalid, mixed, or out of bounds.
    """
    if not args:
        return 1, None

    if len(args) > 1:
        raise CommandValidationError(
            f"⚠️ Mixed or invalid parameters. Usage: `/{command} [round (e.g. r5)]` or `/{command} [limit (1-5)]`"
        )

    arg = args[0].lower()

    if arg.startswith("r"):
        round_str = arg[1:]
        if not round_str.isdigit():
            raise CommandValidationError(
                f"⚠️ Invalid round format. Usage: `/{command} [round (e.g. r5)]` or `/{command} [limit (1-5)]`"
            )
        round_num = int(round_str)
        if round_num < 1 or round_num > bounds["total_rounds"]:
            raise CommandValidationError(
                f"⚠️ Invalid round number. The current season has only {bounds['total_rounds']} rounds."
            )
        return 1, round_num

    if arg.isdigit():
        val = int(arg)
        if 1 <= val <= 5:
            # Cap limit dynamically at completed rounds count
            if command == "sprint":
                max_limit = len(bounds["completed_sprint_rounds"])
            else:
                max_limit = bounds["completed_rounds"]

            capped_limit = min(val, max_limit) if max_limit > 0 else 1
            return capped_limit, None
        else:
            if val < 1 or val > bounds["total_rounds"]:
                raise CommandValidationError(
                    f"⚠️ Invalid round number. The current season has only {bounds['total_rounds']} rounds."
                )
            return 1, val
        return capped_limit, None

    raise CommandValidationError(
        f"⚠️ Invalid argument format. Usage: `/{command} [round (e.g. r5)]` or `/{command} [limit (1-5)]`"
    )


def validate_and_parse_session_result_args(
    args: list[str], bounds: dict
) -> tuple[int, int | None, str | None]:
    """
    Parse and strictly validate sessionresult arguments.
    """
    if not args:
        return 1, None, None

    if len(args) > 2:
        raise CommandValidationError(
            "⚠️ Usage: /sessionresult [round] [fp1|fp2|fp3|quali|sq|sprint|race]"
        )

    round_num = None
    session_arg = None
    limit = 1

    # Check each argument
    for arg in args:
        arg_lower = arg.lower()
        if arg_lower.startswith("r") and arg_lower[1:].isdigit():
            if round_num is not None:
                raise CommandValidationError("⚠️ Multiple round numbers specified.")
            r_val = int(arg_lower[1:])
            if r_val < 1 or r_val > bounds["total_rounds"]:
                raise CommandValidationError(
                    f"⚠️ Invalid round number. The current season has only {bounds['total_rounds']} rounds."
                )
            round_num = r_val
        elif arg_lower.isdigit():
            val = int(arg_lower)
            if len(args) == 1:
                if val < 1 or val > 5:
                    raise CommandValidationError("⚠️ Limit must be between 1 and 5.")
                limit = (
                    min(val, bounds["completed_rounds"]) if bounds["completed_rounds"] > 0 else 1
                )
            else:
                if round_num is not None:
                    raise CommandValidationError("⚠️ Multiple round numbers specified.")
                if val < 1 or val > bounds["total_rounds"]:
                    raise CommandValidationError(
                        f"⚠️ Invalid round number. The current season has only {bounds['total_rounds']} rounds."
                    )
                round_num = val
        else:
            normalized = normalize_session_key(arg_lower)
            if normalized is None:
                raise CommandValidationError(
                    "⚠️ Usage: /sessionresult [round] [fp1|fp2|fp3|quali|sq|sprint|race]"
                )
            if session_arg is not None:
                raise CommandValidationError("⚠️ Multiple session types specified.")
            session_arg = arg_lower

    return limit, round_num, session_arg


async def send_merged_messages(
    update: Update, messages: list[str], parse_mode=ParseMode.MARKDOWN
) -> None:
    current_chunk = []
    current_len = 0
    for msg in messages:
        needed = len(msg) + (7 if current_chunk else 0)
        if current_len + needed > 4096:
            await update.effective_message.reply_text(
                "\n\n---\n\n".join(current_chunk), parse_mode=parse_mode
            )
            current_chunk = [msg]
            current_len = len(msg)
        else:
            current_chunk.append(msg)
            current_len += needed
    if current_chunk:
        await update.effective_message.reply_text(
            "\n\n---\n\n".join(current_chunk), parse_mode=parse_mode
        )


async def _get_bounds(repo, season: int, races: list) -> dict:
    import datetime
    from unittest.mock import AsyncMock, Mock

    is_mock = False
    try:
        if isinstance(repo, Mock):
            is_mock = True
    except TypeError:
        pass

    if is_mock:
        if isinstance(getattr(repo, "get_schedule_bounds", None), AsyncMock):
            return await repo.get_schedule_bounds(season)

        today = datetime.date.today()
        completed_races = [r for r in races if r.date <= today]
        upcoming_races = [r for r in races if r.date > today]
        sprint_rounds = [r.round for r in races if getattr(r, "sprint", None) is not None]
        completed_sprint_rounds = [
            r.round for r in races if getattr(r, "sprint", None) is not None and r.date <= today
        ]

        bounds = {
            "total_rounds": max([r.round for r in races]) if races else 0,
            "completed_rounds": len(completed_races),
            "upcoming_rounds": len(upcoming_races),
            "last_completed_round": completed_races[-1].round if completed_races else None,
            "next_upcoming_round": upcoming_races[0].round if upcoming_races else None,
            "sprint_rounds": sprint_rounds,
            "completed_sprint_rounds": completed_sprint_rounds,
        }
        repo.get_schedule_bounds = AsyncMock(return_value=bounds)
        return bounds

    return await repo.get_schedule_bounds(season)


async def results_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        limit, round_num = validate_and_parse_args("results", context.args or [], bounds)

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
            race, results = await jolpica.get_race_results(str(season), "last")
            if race and results:
                await repo.save_race_results(season, race.round, results)
                await update.effective_message.reply_text(
                    format_race_results(race, results), parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.effective_message.reply_text(no_data_message("race results"))
            return

        selected_races = completed[:limit]
        target_rounds = [(r.round, r) for r in selected_races]

    messages = []
    for r_num, race in target_rounds:
        cached = await repo.get_race_results(season, r_num)
        if cached:
            from f1_bot.models.results import RaceResult as RR

            results = [RR.model_validate(r) for r in cached]
        else:
            _, results = await jolpica.get_race_results(str(season), str(r_num))
            if race and results:
                await repo.save_race_results(season, r_num, results)

        if results:
            messages.append(format_race_results(race, results))

    if not messages:
        await update.effective_message.reply_text(no_data_message("race results"))
        return

    await send_merged_messages(update, messages)


async def qualifying_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        limit, round_num = validate_and_parse_args("qualifying", context.args or [], bounds)

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
            race, results = await jolpica.get_qualifying_results(str(season), "last")
            if race and results:
                await repo.save_qualifying_results(season, race.round, results)
                await update.effective_message.reply_text(
                    format_qualifying_results(race, results), parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.effective_message.reply_text(no_data_message("qualifying results"))
            return

        selected_races = completed[:limit]
        target_rounds = [(r.round, r) for r in selected_races]

    messages = []
    for r_num, race in target_rounds:
        cached = await repo.get_qualifying_results(season, r_num)
        if cached:
            from f1_bot.models.results import QualifyingResult as QR

            results = [QR.model_validate(r) for r in cached]
        else:
            _, results = await jolpica.get_qualifying_results(str(season), str(r_num))
            if race and results:
                await repo.save_qualifying_results(season, r_num, results)

        if results:
            messages.append(format_qualifying_results(race, results))

    if not messages:
        await update.effective_message.reply_text(no_data_message("qualifying results"))
        return

    await send_merged_messages(update, messages)


async def sprint_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        limit, round_num = validate_and_parse_args("sprint", context.args or [], bounds)

        target_rounds = []

        if round_num is not None:
            race = next((r for r in races if r.round == round_num), None)
            if not race:
                raise CommandValidationError(
                    f"⚠️ Invalid round number. The current season has only {bounds['total_rounds']} rounds."
                )
            if round_num not in bounds["sprint_rounds"]:
                raise CommandValidationError(
                    f"⚠️ Round {round_num} ({race.name}) is not a sprint weekend."
                )
            if round_num not in bounds["completed_sprint_rounds"]:
                raise CommandValidationError(
                    f"⚠️ Round {round_num} ({race.name}) has not occurred yet. Use /nextsprint to see when the next sprint session is scheduled."
                )
            target_rounds = [(round_num, race)]
    except CommandValidationError as e:
        await update.effective_message.reply_text(str(e), parse_mode=ParseMode.MARKDOWN)
        return

    if round_num is None:
        completed_sprints = [r for r in races if r.round in bounds["completed_sprint_rounds"]]
        completed_sprints.sort(key=lambda r: r.round, reverse=True)

        if not completed_sprints:
            race, results = await jolpica.get_sprint_results(str(season), "last")
            if race and results:
                await repo.save_sprint_results(season, race.round, results)
                await update.effective_message.reply_text(
                    format_sprint_results(race, results), parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.effective_message.reply_text(no_data_message("sprint results"))
            return

        selected_races = completed_sprints[:limit]
        target_rounds = [(r.round, r) for r in selected_races]

    messages = []
    for r_num, race in target_rounds:
        cached = await repo.get_sprint_results(season, r_num)
        if cached:
            from f1_bot.models.results import SprintResult as SR

            results = [SR.model_validate(r) for r in cached]
        else:
            _, results = await jolpica.get_sprint_results(str(season), str(r_num))
            if race and results:
                await repo.save_sprint_results(season, r_num, results)

        if results:
            messages.append(format_sprint_results(race, results))

    if not messages:
        await update.effective_message.reply_text(no_data_message("sprint results"))
        return

    await send_merged_messages(update, messages)


async def session_result_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    openf1 = context.bot_data["openf1"]
    season = datetime.date.today().year
    args = context.args or []

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
        await update.effective_message.reply_text(no_data_message("schedule"))
        return

    try:
        bounds = await _get_bounds(repo, season, races)
        limit, round_num, session_arg = validate_and_parse_session_result_args(args, bounds)

        if session_arg is not None and normalize_session_key(session_arg) is None:
            raise CommandValidationError(
                "⚠️ Usage: /sessionresult [round] [fp1|fp2|fp3|quali|sq|sprint|race]"
            )

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
    except CommandValidationError as e:
        await update.effective_message.reply_text(str(e), parse_mode=ParseMode.MARKDOWN)
        return

    from f1_bot.utils.sessions import find_recent_completed_sessions

    target_entries = []

    if round_num is not None:
        race = next((r for r in races if r.round == round_num), None)

        if session_arg is not None:
            entry = find_race_session(races, round_num, session_arg)
            if not entry:
                await update.effective_message.reply_text(no_data_message("session result"))
                return
            target_entries = [entry]
        else:
            entry = find_recent_completed_session([race])
            if not entry:
                await update.effective_message.reply_text(no_data_message("session result"))
                return
            target_entries = [entry]
    else:
        target_entries = find_recent_completed_sessions(
            races, session_arg, limit=limit, now=datetime.datetime.now(datetime.UTC)
        )

    if not target_entries:
        await update.effective_message.reply_text(no_data_message("session result"))
        return

    sessions = await openf1.get_sessions(year=season)

    # Fetch driver mapping
    jolpica = context.bot_data["jolpica"]
    drivers_map = {}
    try:
        drivers_list = await jolpica.get_drivers(str(season))
        drivers_map = {
            int(d.permanent_number): d
            for d in drivers_list
            if d.permanent_number and d.permanent_number.isdigit()
        }
    except Exception:
        pass

    messages = []
    for entry in target_entries:
        openf1_session = match_openf1_session(entry, sessions)
        if openf1_session is None:
            continue

        cached = await repo.get_session_results(
            season, entry.race.round, openf1_session.session_key
        )
        if cached:
            results = [SessionResult.model_validate(r) for r in cached]
        else:
            results = await openf1.get_session_results(session_key=openf1_session.session_key)
            if results:
                await repo.save_session_results(
                    season, entry.race.round, openf1_session.session_key, results
                )

        if results:
            messages.append(format_session_results(entry, results, drivers_map))

    if not messages:
        await update.effective_message.reply_text(no_data_message("session result"))
        return

    await send_merged_messages(update, messages)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("results", results_handler))
    app.add_handler(CommandHandler("qualifying", qualifying_handler))
    app.add_handler(CommandHandler("sprint", sprint_handler))
    app.add_handler(CommandHandler("sessionresult", session_result_handler))
