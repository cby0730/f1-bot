from datetime import datetime

from pydantic import BaseModel


class UserPreference(BaseModel):
    telegram_id: int
    timezone: str = "UTC"
    language: str = "en"
    created_at: datetime | None = None
    updated_at: datetime | None = None
