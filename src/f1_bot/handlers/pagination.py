"""Shared pagination utilities for inline keyboard navigation."""

import datetime

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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

    row.append(InlineKeyboardButton(position_label, callback_data=f"{prefix}:{current_round}"))

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

    row.append(
        InlineKeyboardButton(
            f"R{current_round}/{upcoming_rounds[-1]}", callback_data=f"{prefix}:{current_round}"
        )
    )

    if idx < total - 1:
        next_round = upcoming_rounds[idx + 1]
        row.append(InlineKeyboardButton("▶", callback_data=f"{prefix}:{next_round}"))

    return InlineKeyboardMarkup([row])


# ---------------------------------------------------------------------------
# Two-state keyboards for unified /next and /results
# ---------------------------------------------------------------------------


def next_overview_keyboard(current_round: int) -> InlineKeyboardMarkup:
    """State A keyboard for /next: session type filter buttons.

    Row 1: FP1 FP2 FP3 Q
    Row 2: SQ SPR Race All
    """
    def _btn(key: str, label: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(label, callback_data=f"next:filtered:{key}:{current_round}")

    practice_row = [_btn(key, label) for key, label in _PRACTICE_SESSIONS]
    competitive_row = [_btn(key, label) for key, label in _COMPETITIVE_SESSIONS]
    return InlineKeyboardMarkup([practice_row, competitive_row])


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
                InlineKeyboardButton("◀", callback_data=f"next:filtered:{session_filter}:{prev_round}")
            )
        nav_row.append(
            InlineKeyboardButton(
                f"R{current_round}/{navigable_rounds[-1]}",
                callback_data=f"next:filtered:{session_filter}:{current_round}",
            )
        )
        if idx < total - 1:
            next_round = navigable_rounds[idx + 1]
            nav_row.append(
                InlineKeyboardButton("▶", callback_data=f"next:filtered:{session_filter}:{next_round}")
            )

    back_row = [InlineKeyboardButton("🔙 Back", callback_data=f"next:back:_:{current_round}")]
    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append(back_row)
    return InlineKeyboardMarkup(rows)


def results_overview_keyboard(current_round: int, active_key: str | None = None) -> InlineKeyboardMarkup:
    """State A keyboard for /results: session type filter buttons.

    Row 1: FP1 FP2 FP3 Q
    Row 2: SQ SPR Race All
    Active session is highlighted with · markers.
    """
    def _btn(key: str, label: str) -> InlineKeyboardButton:
        display = f"·{label}·" if key == active_key else label
        return InlineKeyboardButton(display, callback_data=f"res:filtered:{key}:{current_round}")

    practice_row = [_btn(key, label) for key, label in _PRACTICE_SESSIONS]
    competitive_row = [_btn(key, label) for key, label in _COMPETITIVE_SESSIONS]
    return InlineKeyboardMarkup([practice_row, competitive_row])


def results_filtered_keyboard(
    current_round: int,
    navigable_rounds: list[int],
    session_key: str,
) -> InlineKeyboardMarkup:
    """State B keyboard for /results filtered view: session filter row + nav row + Back."""
    def _btn(key: str, label: str) -> InlineKeyboardButton:
        display = f"·{label}·" if key == session_key else label
        return InlineKeyboardButton(display, callback_data=f"res:filtered:{key}:{current_round}")

    practice_row = [_btn(key, label) for key, label in _PRACTICE_SESSIONS]
    competitive_row = [_btn(key, label) for key, label in _COMPETITIVE_SESSIONS]

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
        nav_row.append(
            InlineKeyboardButton(
                f"R{current_round}/{navigable_rounds[-1]}",
                callback_data=f"res:filtered:{session_key}:{current_round}",
            )
        )
        if idx < total - 1:
            next_round = navigable_rounds[idx + 1]
            nav_row.append(
                InlineKeyboardButton("▶", callback_data=f"res:filtered:{session_key}:{next_round}")
            )

    back_row = [InlineKeyboardButton("🔙 Back", callback_data=f"res:back:_:{current_round}")]
    rows = [practice_row, competitive_row]
    if nav_row:
        rows.append(nav_row)
    rows.append(back_row)
    return InlineKeyboardMarkup(rows)


# Also keep the old session_result_keyboard for backward compat handling
def session_result_keyboard(
    current_key: str,
    current_round: int,
    navigable_rounds: list[int],
) -> InlineKeyboardMarkup:
    """Legacy 3-row keyboard for /sessionresult — kept for backward compat."""
    _P = [("fp1", "FP1"), ("fp2", "FP2"), ("fp3", "FP3")]
    _C = [("sprint_qualifying", "SQ"), ("sprint", "SPR"), ("qualifying", "Q"), ("race", "Race")]

    def _btn(key: str, label: str) -> InlineKeyboardButton:
        display = f"·{label}·" if key == current_key else label
        return InlineKeyboardButton(display, callback_data=f"sr:{key}:{current_round}")

    practice_row = [_btn(key, label) for key, label in _P]
    competitive_row = [_btn(key, label) for key, label in _C]

    total = len(navigable_rounds)
    nav_row: list[InlineKeyboardButton] = []
    if total > 0:
        try:
            idx = navigable_rounds.index(current_round)
        except ValueError:
            idx = total - 1
        if idx > 0:
            prev_round = navigable_rounds[idx - 1]
            nav_row.append(InlineKeyboardButton("◀", callback_data=f"sr:{current_key}:{prev_round}"))
        nav_row.append(
            InlineKeyboardButton(
                f"R{current_round}/{navigable_rounds[-1]}",
                callback_data=f"sr:{current_key}:{current_round}",
            )
        )
        if idx < total - 1:
            next_round = navigable_rounds[idx + 1]
            nav_row.append(InlineKeyboardButton("▶", callback_data=f"sr:{current_key}:{next_round}"))

    rows = [practice_row, competitive_row]
    if nav_row:
        rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


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

    bounds = await repo.get_schedule_bounds(season)
    return races, bounds, season


def resolve_default_round(bounds: dict, sprint_only: bool = False) -> int | None:
    """Return the round to display by default (last completed, or last sprint)."""
    if sprint_only:
        rounds = bounds.get("completed_sprint_rounds", [])
        return rounds[-1] if rounds else None
    return bounds.get("last_completed_round")
