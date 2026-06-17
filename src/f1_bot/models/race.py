from datetime import date as dt_date
from datetime import time as dt_time

from pydantic import BaseModel


class Circuit(BaseModel):
    circuit_id: str
    name: str
    locality: str
    country: str
    lat: float | None = None
    lng: float | None = None
    url: str | None = None


class RaceSession(BaseModel):
    """A single timed session within a race weekend (FP1, Qualifying, Race, etc.)."""

    name: str
    date: dt_date | None = None
    time: dt_time | None = None
    session_key: int | None = None


class Race(BaseModel):
    season: int
    round: int
    name: str
    url: str | None = None
    circuit: Circuit
    date: dt_date
    time: dt_time | None = None
    # Session times sourced from OpenF1 meetings endpoint
    fp1: RaceSession | None = None
    fp2: RaceSession | None = None
    fp3: RaceSession | None = None
    qualifying: RaceSession | None = None
    sprint_qualifying: RaceSession | None = None
    sprint: RaceSession | None = None
    # Timezone offset of the circuit location e.g. "+08:00" (from OpenF1)
    gmt_offset: str | None = None


class Meeting(BaseModel):
    """OpenF1 meeting record — used for timezone offsets and session metadata."""

    meeting_key: int
    meeting_name: str
    meeting_official_name: str | None = None
    location: str | None = None
    country_name: str | None = None
    circuit_short_name: str | None = None
    date_start: str | None = None
    gmt_offset: str | None = None
    year: int


class Session(BaseModel):
    """OpenF1 session record (FP1, Qualifying, Race, etc.)."""

    session_key: int
    session_name: str
    session_type: str
    meeting_key: int
    date_start: str | None = None
    date_end: str | None = None
    gmt_offset: str | None = None
    year: int
