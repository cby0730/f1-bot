"""Handler for /title — WDC + WCC championship clinch analysis.

Near-clone of ``handlers/standings.py``: the same two-view toggle pattern, distinct
``title:`` callback namespace. Reads exclusively from PostgreSQL (SQL-only handler).

Remaining events are aligned to each standings table's OWN ``round_after`` snapshot
(not live ``now()``), so points and remaining-count come from the same round — see
spec 004 "Remaining events MUST align to the standings snapshot".
"""

import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import (
    format_title_wcc,
    format_title_wdc,
    no_data_message,
)
from f1_bot.handlers.context import resolve_context
from f1_bot.utils.championship import remaining_events

_WDC = "title:wdc"
_WCC = "title:wcc"


def _toggle_keyboard(lang: str) -> InlineKeyboardMarkup:
    # Shares the /standings button labels; callback_data keeps the title: namespace.
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("standings.btn_drivers", lang), callback_data=_WDC),
                InlineKeyboardButton(t("standings.btn_constructors", lang), callback_data=_WCC),
            ]
        ]
    )


async def _render_view(repo, season: int, table: str, ctx: RenderContext) -> str:
    """Build the title text for one championship, aligning remaining events to that
    table's own standings snapshot (round_after). Returns no_data text if empty."""
    if table == "drivers":
        standings = await repo.get_driver_standings(season)
        fmt = format_title_wdc
    else:
        standings = await repo.get_constructor_standings(season)
        fmt = format_title_wcc
    if not standings:
        return no_data_message("common.noun_standings", ctx)
    n = await repo.get_standings_round(season, table)  # same snapshot as `standings`
    races = await repo.get_schedule(season)
    rem_races, rem_sprints = remaining_events(races, n or 0)
    return fmt(standings, rem_races, rem_sprints, season, ctx)


async def title_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    season = datetime.date.today().year
    text = await _render_view(repo, season, "drivers", ctx)
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=_toggle_keyboard(ctx.lang)
    )


async def title_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    repo = context.bot_data["repo"]
    ctx = await resolve_context(update, repo)
    season = datetime.date.today().year
    table = "drivers" if query.data == _WDC else "constructors"
    text = await _render_view(repo, season, table, ctx)
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=_toggle_keyboard(ctx.lang)
        )
    except BadRequest:
        pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("title", title_handler))
    app.add_handler(CallbackQueryHandler(title_callback, pattern=r"^title:"))
