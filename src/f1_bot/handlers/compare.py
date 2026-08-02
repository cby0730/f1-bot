"""Handler for /compare — current-season driver head-to-head.

Three-step stateless flow (state carried in callback_data, no server-side session):

    /compare  →  Step 1 pick driver A (cmp:a:{id})
              →  Step 2 pick driver B (cmp:b:{a_id}:{b_id})
              →  Step 3 result table  ([compare.restart] → cmp:list)

Reads exclusively from PostgreSQL via ``Repository`` (SQL-only handler pattern).
All six stats combine the main race and the sprint of each completed round.
"""

import asyncio
import datetime

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from f1_bot.formatting.context import RenderContext
from f1_bot.formatting.emoji import flag_icon
from f1_bot.formatting.i18n import t
from f1_bot.formatting.messages import format_driver_comparison, no_data_message
from f1_bot.handlers.context import resolve_context
from f1_bot.handlers.pagination import two_column_keyboard

log = structlog.get_logger(__name__)


def _finished(status: str) -> bool:
    """Whitelist finish classification: 'Finished' or lapped ('+N Lap(s)').

    Everything else — every failure string — is a DNF. Whitelisting keeps an unseen
    failure string from ever being misread as a finish.
    """
    return status == "Finished" or status.startswith("+")


async def _real_drivers(repo, season: int) -> list:
    """Current-season Driver objects, synthetic ``openf1_*`` ids filtered out.

    ``get_drivers_map`` is keyed by permanent number, but its *values* are the
    resolved Driver objects (jolpica overwrites openf1 for shared numbers). We
    dedupe on ``driver_id`` and drop any residual synthetic id.
    """
    drivers_map = await repo.get_drivers_map(season)
    seen: set[str] = set()
    drivers = []
    for d in sorted(drivers_map.values(), key=lambda d: d.family_name):
        if d.driver_id.startswith("openf1_") or d.driver_id in seen:
            continue
        seen.add(d.driver_id)
        drivers.append(d)
    return drivers


def _menu_keyboard(drivers: list, exclude_id: str | None, a_id: str | None) -> InlineKeyboardMarkup:
    """2-column driver grid.

    ``a_id`` None → Step 1 buttons (``cmp:a:{id}``). ``a_id`` set → Step 2 buttons
    (``cmp:b:{a_id}:{id}``) with driver A excluded so a driver can't face themselves.
    """
    buttons = []
    for d in drivers:
        if exclude_id is not None and d.driver_id == exclude_id:
            continue
        flag = flag_icon(d.nationality or "")
        label = f"{flag} {d.family_name}"
        if a_id is None:
            data = f"cmp:a:{d.driver_id}"
        else:
            data = f"cmp:b:{a_id}:{d.driver_id}"
            # Telegram hard-caps callback_data at 64 bytes; surface, don't truncate.
            if len(data.encode()) > 64:
                raise ValueError(f"callback_data exceeds 64 bytes: {data}")
        buttons.append(InlineKeyboardButton(label, callback_data=data))
    return two_column_keyboard(buttons)


async def _aggregate(repo, season: int, a_id: str, b_id: str) -> dict:
    """Aggregate the head-to-head over every completed round's race + sprint.

    Returns a stats dict consumed by ``format_driver_comparison``. ``has_data`` is
    False only when no comparable session and no standings points exist for the pair.
    """
    bounds = await repo.get_schedule_bounds(season)
    completed = bounds.get("last_completed_round") or 0

    wins = [0, 0]
    podiums = [0, 0]
    dnfs = [0, 0]
    race_h2h = [0, 0]
    quali_h2h = [0, 0]
    session_count = 0  # comparable (both-present) race/sprint/quali sessions

    def _by_id(results, did):
        for r in results or []:
            if r.get("driver", {}).get("driver_id") == did:
                return r
        return None

    def _tally_counts(r, idx):
        pos = r["position"]
        if _finished(r["status"]):
            if pos == 1:
                wins[idx] += 1
            if pos <= 3:
                podiums[idx] += 1
        else:
            dnfs[idx] += 1

    def _win_by_position(pos_a, pos_b, tally):
        """Award one comparable session; lower position wins (ties break to A)."""
        nonlocal session_count
        session_count += 1
        tally[0 if pos_a < pos_b else 1] += 1

    def _tally_h2h(ra, rb, tally):
        """Per-session H2H with DNF handling. Assumes both drivers present."""
        # both DNF — retirement order carries no competitive meaning
        if not _finished(ra["status"]) and not _finished(rb["status"]):
            return
        # finishing beats retiring; otherwise lower position wins
        _win_by_position(ra["position"], rb["position"], tally)

    # All per-round reads are independent — fetch every round's race/sprint/quali
    # results plus the standings concurrently (matches the asyncio.gather pattern
    # in scheduler/jobs.py), then tally serially over the resolved lists. This
    # collapses ~3×N sequential round-trips into a single latency window on the
    # callback hot path.
    race_reads = [repo.get_race_results(season, rnd) for rnd in range(1, completed + 1)]
    sprint_reads = [repo.get_sprint_results(season, rnd) for rnd in range(1, completed + 1)]
    quali_reads = [repo.get_qualifying_results(season, rnd) for rnd in range(1, completed + 1)]
    race_all, sprint_all, quali_all, standings = await asyncio.gather(
        asyncio.gather(*race_reads),
        asyncio.gather(*sprint_reads),
        asyncio.gather(*quali_reads),
        repo.get_driver_standings(season),
    )

    for results in (*race_all, *sprint_all):
        if not results:  # None (not synced / no sprint) or empty → skip
            continue
        ra, rb = _by_id(results, a_id), _by_id(results, b_id)
        if ra is not None:
            _tally_counts(ra, 0)
        if rb is not None:
            _tally_counts(rb, 1)
        if ra is not None and rb is not None:
            _tally_h2h(ra, rb, race_h2h)

    for quali in quali_all:
        qa, qb = _by_id(quali, a_id), _by_id(quali, b_id)
        if qa is not None and qb is not None:  # both must have a quali result
            _win_by_position(qa["position"], qb["position"], quali_h2h)

    pts = {s.driver.driver_id: s.points for s in standings}
    points = (pts.get(a_id), pts.get(b_id))

    has_data = session_count > 0 or any(p is not None for p in points)

    return {
        "has_data": has_data,
        "points": points,
        "quali": tuple(quali_h2h),
        "race": tuple(race_h2h),
        "wins": tuple(wins),
        "podiums": tuple(podiums),
        "dnfs": tuple(dnfs),
    }


def _back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("compare.restart", lang), callback_data="cmp:list")]]
    )


async def compare_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/compare entry point — render the Step 1 driver grid."""
    repo = context.bot_data.get("repo")
    ctx = await resolve_context(update, repo) if repo else RenderContext()
    season = datetime.date.today().year

    if not repo:
        await update.effective_message.reply_text(no_data_message("common.noun_driver_list", ctx))
        return

    try:
        drivers = await _real_drivers(repo, season)
    except Exception:
        drivers = []

    if not drivers:
        await update.effective_message.reply_text(no_data_message("common.noun_driver_list", ctx))
        return

    await update.effective_message.reply_text(
        t("compare.pick_a", ctx.lang),
        reply_markup=_menu_keyboard(drivers, exclude_id=None, a_id=None),
        parse_mode=ParseMode.MARKDOWN,
    )


async def _compare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    repo = context.bot_data.get("repo")
    ctx = await resolve_context(update, repo) if repo else RenderContext()

    try:
        parts = query.data.split(":")
        action = parts[1]
        if action == "a":
            a_id = parts[2]
        elif action == "b":
            a_id, b_id = parts[2], parts[3]
    except (ValueError, IndexError):
        await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
        return

    if not repo:
        await query.answer(text=t("common.database_unavailable", ctx.lang), show_alert=True)
        return

    season = datetime.date.today().year

    try:
        drivers = await _real_drivers(repo, season)  # every branch needs the current lineup

        if action == "list":
            if not drivers:
                await query.answer()
                await query.edit_message_text(text=no_data_message("common.noun_driver_list", ctx))
                return
            await query.answer()
            await _safe_edit(
                query,
                t("compare.pick_a", ctx.lang),
                _menu_keyboard(drivers, exclude_id=None, a_id=None),
            )

        elif action == "a":
            await query.answer()
            await _safe_edit(
                query,
                t("compare.pick_b", ctx.lang),
                _menu_keyboard(drivers, exclude_id=a_id, a_id=a_id),
            )

        elif action == "b":
            by_id = {d.driver_id: d for d in drivers}
            a, b = by_id.get(a_id), by_id.get(b_id)
            if a is None or b is None:
                # A driver vanished from the lineup between render and click.
                await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
                return
            stats = await _aggregate(repo, season, a_id, b_id)
            await query.answer()
            await _safe_edit(
                query, format_driver_comparison(a, b, stats, ctx), _back_keyboard(ctx.lang)
            )
        else:
            await query.answer(text=t("common.invalid_selection", ctx.lang), show_alert=True)
    except Exception:
        log.exception("compare_callback_failed")
        try:
            await query.answer(text=t("common.error_occurred", ctx.lang), show_alert=True)
        except Exception:  # noqa: S110
            pass


async def _safe_edit(query, text: str, keyboard: InlineKeyboardMarkup) -> None:
    """edit_message_text swallowing the 'message not modified' BadRequest."""
    try:
        await query.edit_message_text(
            text=text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN
        )
    except BadRequest:
        pass


def register(app: Application) -> None:
    app.add_handler(CommandHandler("compare", compare_handler))
    app.add_handler(CallbackQueryHandler(_compare_callback, pattern=r"^cmp:"))
