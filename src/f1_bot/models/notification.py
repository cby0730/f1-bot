from datetime import datetime

from pydantic import BaseModel

from f1_bot.formatting.i18n import t

# Offered reminder lead times. The values are the *English* labels; they are kept
# so the preset set stays readable at a glance, but the display path goes through
# `timing_label` — never index this dict to build user-facing text.
TIMING_PRESETS: dict[int, str] = {
    15: "15min",
    30: "30min",
    60: "1hr",
    180: "3hr",
}


def timing_label(minutes: int, lang: str) -> str:
    """Localized label for a reminder lead time; unknown values render as `Nmin`."""
    try:
        return t(f"notifications.timing_{minutes}", lang)
    except KeyError:
        return f"{minutes}min"


class NotificationSubscription(BaseModel):
    id: int | None = None
    telegram_id: int
    season: int
    round: int
    session_key: str
    minutes_before: int
    notified: bool = False
    fire_at: datetime
    created_at: datetime | None = None
