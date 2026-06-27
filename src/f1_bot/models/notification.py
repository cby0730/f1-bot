from datetime import datetime

from pydantic import BaseModel

TIMING_PRESETS: dict[int, str] = {
    15: "15min",
    30: "30min",
    60: "1hr",
    180: "3hr",
}


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
