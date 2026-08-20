import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import (
    format_constructor_standings,
    format_driver_standings,
    no_data_message,
)
from f1_bot.handlers.context import resolve_context
from f1_bot.utils.championship import remaining_events

_WDC = "standings:wdc"
_WCC = "standings:wcc"


def _toggle_keyboard(lang: str) -> InlineKeyboardMarkup:
    # callback_data stays a stable slug; only the button label is translated.
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("standings.btn_drivers", lang), callback_data=_WDC),
                InlineKeyboardButton(t("standings.btn_constructors", lang), callback_data=_WCC),
            ]
        ]
    )


async def _render_table(repo, season: int, table: str, ctx: RenderContext) -> str | None:
    """Standings table plus two-line clinch strip, aligned to this table's snapshot.

    Remaining events come from ``get_standings_round(season, table)`` — never
    ``now()`` / ``get_schedule_bounds()``. Empty standings return None so those
    reads are not made.
    """
    if table == "drivers":
        standings = await repo.get_driver_standings(season)
        fmt = format_driver_standings
    else:
        standings = await repo.get_constructor_standings(season)
        fmt = format_constructor_standings
    if not standings:
        return None
    n = await repo.get_standings_round(season, table)
    races = await repo.get_schedule(season)
    rem_races, rem_sprints = remaining_events(races or [], n or 0)
    return fmt(standings, season, rem_races, rem_sprints, ctx)


async def standings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    season = datetime.date.today().year
    text = await _render_table(repo, season, "drivers", ctx)
    if text is None:
        await update.effective_message.reply_text(no_data_message("common.noun_standings", ctx))
        return
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_toggle_keyboard(ctx.lang),
    )


async def render_standings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, table: str
) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    season = datetime.date.today().year
    text = await _render_table(repo, season, table, ctx)
    if text is None:
        text = no_data_message("common.noun_standings", ctx)
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_toggle_keyboard(ctx.lang)
        )
    except BadRequest:
        pass


async def standings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    table = "drivers" if query.data == _WDC else "constructors"
    await render_standings_callback(update, context, table)


def register(app: Application) -> None:
    app.add_handler(CommandHandler("standings", standings_handler))
    app.add_handler(CallbackQueryHandler(standings_callback, pattern=r"^standings:"))
