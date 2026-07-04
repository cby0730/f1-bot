"""Shared pagination utilities for inline keyboard navigation."""

import datetime
from datetime import UTC
from datetime import datetime as dt_datetime

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from f1_bot.formatting.emoji import circuit_flag_icon
from f1_bot.formatting.messages import _esc
from f1_bot.utils.sessions import find_next_sessions, find_race_session, session_entries

log = structlog.get_logger(__name__)

# Session type rows for filter keyboards
_PRACTICE_SESSIONS = [
    ("fp1", "FP1"),
    ("fp2", "FP2"),
    ("fp3", "FP3"),
    ("qualifying", "Q"),
]
_COMPETITIVE_SESSIONS = [
    ("sprint_qualifying", "SQ"),
    ("sprint", "SPR"),
    ("race", "Race"),
    ("all", "All"),
]


def round_keyboard(
    prefix: str,
    current_round: int,
    navigable_rounds: list[int],
) -> InlineKeyboardMarkup:
    """Build [◀ Prev] [Round X/Y] [Next ▶] keyboard for completed-round navigation.

    navigable_rounds: sorted list of round numbers the user can browse (e.g. [1,2,...,10]
    or the non-contiguous sprint rounds [4,7,12]). Prev/Next are hidden at boundaries.
    """
    total = len(navigable_rounds)
    if total == 0:
        return InlineKeyboardMarkup([[]])

    try:
        idx = navigable_rounds.index(current_round)
    except ValueError:
        idx = total - 1

    position_label = f"R{current_round}/{navigable_rounds[-1]}"
    row: list[InlineKeyboardButton] = []

    if idx > 0:
        prev_round = navigable_rounds[idx - 1]
        row.append(InlineKeyboardButton("◀", callback_data=f"{prefix}:{prev_round}"))

    center_cb = f"rpk:{prefix}:{current_round}" if total > 1 else f"{prefix}:{current_round}"
    row.append(InlineKeyboardButton(position_label, callback_data=center_cb))

    if idx < total - 1:
        next_round = navigable_rounds[idx + 1]
        row.append(InlineKeyboardButton("▶", callback_data=f"{prefix}:{next_round}"))

    return InlineKeyboardMarkup([row])


def schedule_keyboard(
    prefix: str,
    current_round: int,
    upcoming_rounds: list[int],
) -> InlineKeyboardMarkup:
    """Build prev/next keyboard for forward-navigation in schedule commands."""
    total = len(upcoming_rounds)
    if total == 0:
        return InlineKeyboardMarkup([[]])

    try:
        idx = upcoming_rounds.index(current_round)
    except ValueError:
        idx = 0

    row: list[InlineKeyboardButton] = []

    if idx > 0:
        prev_round = upcoming_rounds[idx - 1]
        row.append(InlineKeyboardButton("◀", callback_data=f"{prefix}:{prev_round}"))

    center_cb = f"rpk:{prefix}:{current_round}" if total > 1 else f"{prefix}:{current_round}"
    row.append(
        InlineKeyboardButton(f"R{current_round}/{upcoming_rounds[-1]}", callback_data=center_cb)
    )

    if idx < total - 1:
        next_round = upcoming_rounds[idx + 1]
        row.append(InlineKeyboardButton("▶", callback_data=f"{prefix}:{next_round}"))

    return InlineKeyboardMarkup([row])


# ---------------------------------------------------------------------------
# Two-state keyboards for unified /next and /results
# ---------------------------------------------------------------------------


def next_overview_keyboard(current_round: int, upcoming_rounds: list[int]) -> InlineKeyboardMarkup:
    """State A keyboard for /next: session type filter buttons.

    Row 1: Pager (◀ R8/24 ▶) - optional, only if len(upcoming_rounds) > 1
    Row 2: FP1 FP2 FP3 Q
    Row 3: SQ SPR Race
    """
    rows = []

    # 1. Pager row (only if more than 1 upcoming round)
    total = len(upcoming_rounds)
    if total > 1:
        try:
            idx = upcoming_rounds.index(current_round)
        except ValueError:
            idx = 0

        nav_row: list[InlineKeyboardButton] = []
        if idx > 0:
            prev_round = upcoming_rounds[idx - 1]
            nav_row.append(InlineKeyboardButton("◀", callback_data=f"next:back:_:{prev_round}"))

        nav_row.append(
            InlineKeyboardButton(
                f"R{current_round}/{upcoming_rounds[-1]}",
                callback_data=f"rpk:nb:{current_round}",
            )
        )

        if idx < total - 1:
            next_round = upcoming_rounds[idx + 1]
            nav_row.append(InlineKeyboardButton("▶", callback_data=f"next:back:_:{next_round}"))

        rows.append(nav_row)

    # 2. Session filters (All is excluded)
    def _btn(key: str, label: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(label, callback_data=f"next:filtered:{key}:{current_round}")

    practice_row = [_btn(key, label) for key, label in _PRACTICE_SESSIONS]
    competitive_row = [_btn(key, label) for key, label in _COMPETITIVE_SESSIONS if key != "all"]

    rows.append(practice_row)
    rows.append(competitive_row)

    # 🔔 Remind Me button
    rows.append(
        [InlineKeyboardButton("🔔 Remind Me", callback_data=f"notify:pick:{current_round}")]
    )

    return InlineKeyboardMarkup(rows)


def next_filtered_keyboard(
    current_round: int,
    navigable_rounds: list[int],
    session_filter: str,
) -> InlineKeyboardMarkup:
    """State B keyboard for /next filtered view: nav row + Back button."""
    total = len(navigable_rounds)
    nav_row: list[InlineKeyboardButton] = []

    if total > 0:
        try:
            idx = navigable_rounds.index(current_round)
        except ValueError:
            idx = 0

        if idx > 0:
            prev_round = navigable_rounds[idx - 1]
            nav_row.append(
                InlineKeyboardButton(
                    "◀", callback_data=f"next:filtered:{session_filter}:{prev_round}"
                )
            )
        center_cb = (
            f"rpk:nf:{session_filter}:{current_round}"
            if total > 1
            else f"next:filtered:{session_filter}:{current_round}"
        )
        nav_row.append(
            InlineKeyboardButton(
                f"R{current_round}/{navigable_rounds[-1]}",
                callback_data=center_cb,
            )
        )
        if idx < total - 1:
            next_round = navigable_rounds[idx + 1]
            nav_row.append(
                InlineKeyboardButton(
                    "▶", callback_data=f"next:filtered:{session_filter}:{next_round}"
                )
            )

    back_row = [InlineKeyboardButton("🔙 Back", callback_data=f"next:back:_:{current_round}")]
    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append(back_row)
    return InlineKeyboardMarkup(rows)


def results_overview_keyboard(
    current_round: int,
    completed_rounds: list[int] | None = None,
    active_key: str | None = None,
) -> InlineKeyboardMarkup:
    """State A keyboard for /results: session type filter buttons.

    Row 1: Pager (◀ R10/24 ▶) - optional, only if len(completed_rounds) > 1
    Row 2: FP1 FP2 FP3 Q
    Row 3: SQ SPR Race All
    Active session is highlighted with · markers.
    """
    rows = []

    # 1. Pager row (only if more than 1 completed round)
    if completed_rounds and len(completed_rounds) > 1:
        try:
            idx = completed_rounds.index(current_round)
        except ValueError:
            idx = len(completed_rounds) - 1

        nav_row: list[InlineKeyboardButton] = []
        if idx > 0:
            prev_round = completed_rounds[idx - 1]
            nav_row.append(InlineKeyboardButton("◀", callback_data=f"res:back:_:{prev_round}"))

        nav_row.append(
            InlineKeyboardButton(
                f"R{current_round}/{completed_rounds[-1]}",
                callback_data=f"rpk:rb:{current_round}",
            )
        )

        if idx < len(completed_rounds) - 1:
            next_round = completed_rounds[idx + 1]
            nav_row.append(InlineKeyboardButton("▶", callback_data=f"res:back:_:{next_round}"))

        rows.append(nav_row)

    def _btn(key: str, label: str) -> InlineKeyboardButton:
        display = f"·{label}·" if key == active_key else label
        return InlineKeyboardButton(display, callback_data=f"res:filtered:{key}:{current_round}")

    practice_row = [_btn(key, label) for key, label in _PRACTICE_SESSIONS]
    competitive_row = [_btn(key, label) for key, label in _COMPETITIVE_SESSIONS]

    rows.append(practice_row)
    rows.append(competitive_row)
    return InlineKeyboardMarkup(rows)


def results_filtered_keyboard(
    current_round: int,
    navigable_rounds: list[int],
    session_key: str,
    last_completed_round: int | None = None,
) -> InlineKeyboardMarkup:
    """State B keyboard for /results filtered view: nav row + Back."""

    # Nav row
    total = len(navigable_rounds)
    nav_row: list[InlineKeyboardButton] = []
    if total > 0:
        try:
            idx = navigable_rounds.index(current_round)
        except ValueError:
            idx = total - 1

        if idx > 0:
            prev_round = navigable_rounds[idx - 1]
            nav_row.append(
                InlineKeyboardButton("◀", callback_data=f"res:filtered:{session_key}:{prev_round}")
            )
        denom = last_completed_round if last_completed_round is not None else navigable_rounds[-1]
        center_cb = (
            f"rpk:rf:{session_key}:{current_round}"
            if total > 1
            else f"res:filtered:{session_key}:{current_round}"
        )
        nav_row.append(
            InlineKeyboardButton(
                f"R{current_round}/{denom}",
                callback_data=center_cb,
            )
        )
        if idx < total - 1:
            next_round = navigable_rounds[idx + 1]
            nav_row.append(
                InlineKeyboardButton("▶", callback_data=f"res:filtered:{session_key}:{next_round}")
            )

    back_row = [InlineKeyboardButton("🔙 Back", callback_data=f"res:back:_:{current_round}")]
    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append(back_row)
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Round picker — grid UI for jumping to any navigable round
# ---------------------------------------------------------------------------

_PICKER_COLS = 4


def _origin_to_callback(origin: str, round_num: int) -> str:
    """Map a picker origin back to the callback that the original handler expects."""
    if origin == "nb":
        return f"next:back:_:{round_num}"
    if origin.startswith("nf:"):
        session_filter = origin[3:]
        return f"next:filtered:{session_filter}:{round_num}"
    if origin == "rb":
        return f"res:back:_:{round_num}"
    if origin.startswith("rf:"):
        session_key = origin[3:]
        return f"res:filtered:{session_key}:{round_num}"
    if origin == "lap":
        return f"lap:{round_num}:s"
    return f"{origin}:{round_num}"


def round_picker_keyboard(
    origin: str,
    current_round: int,
    navigable_rounds: list[int],
    races: list,
) -> InlineKeyboardMarkup:
    """Build a grid of round buttons for the picker overlay."""
    race_map = {r.round: r for r in races}
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for rnd in navigable_rounds:
        race = race_map.get(rnd)
        flag = circuit_flag_icon(race.circuit.country) if race else "🏴"
        label = f"·{flag}{rnd}·" if rnd == current_round else f"{flag}{rnd}"
        callback = _origin_to_callback(origin, rnd)
        row.append(InlineKeyboardButton(label, callback_data=callback))
        if len(row) == _PICKER_COLS:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    back_callback = _origin_to_callback(origin, current_round)
    rows.append([InlineKeyboardButton("🔙 Back", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def round_picker_text(current_round: int, races: list) -> str:
    """Build the picker message text in legacy Markdown."""
    race = next((r for r in races if r.round == current_round), None)
    name = _esc(race.name) if race else "Unknown"
    return f"🏁 *Select Round*\nCurrently viewing: R{current_round} — {name}"


def upcoming_rounds(races: list, group: str = "all") -> list[int]:
    """Return sorted list of round numbers that have at least one upcoming session in the group."""
    now = dt_datetime.now(tz=datetime.UTC)
    entries = find_next_sessions(races, group, limit=len(races) * 7, now=now)
    seen: set[int] = set()
    result: list[int] = []
    for entry in entries:
        if entry.race.round not in seen:
            seen.add(entry.race.round)
            result.append(entry.race.round)
    return sorted(result)


def get_completed_rounds_for_session(races: list, session_key: str) -> list[int]:
    """Get list of round numbers that have at least one completed session of the given type."""
    now = dt_datetime.now(tz=UTC)
    if session_key == "all":
        return sorted(
            r.round
            for r in races
            if any(e.starts_at and e.starts_at <= now for e in session_entries([r]))
        )
    rounds = []
    for r in races:
        entry = find_race_session([r], r.round, session_key)
        if entry and entry.starts_at and entry.starts_at <= now:
            rounds.append(r.round)
    return sorted(rounds)


async def load_schedule_and_bounds(context) -> tuple[list, dict, int]:
    """Load schedule from cache and compute season bounds.

    Returns (races, bounds, season). Raises RuntimeError if schedule unavailable.
    SQL-only: no API fallback.
    """
    repo = context.bot_data["repo"]
    season = datetime.date.today().year

    races = await repo.get_schedule(season)
    if not races:
        raise RuntimeError("schedule_unavailable")

    bounds = await repo.get_schedule_bounds(season, races=races)
    return races, bounds, season


def resolve_default_round(bounds: dict, sprint_only: bool = False) -> int | None:
    """Return the round to display by default (last completed, or last sprint)."""
    if sprint_only:
        rounds = bounds.get("completed_sprint_rounds", [])
        return rounds[-1] if rounds else None
    return bounds.get("last_completed_round")
