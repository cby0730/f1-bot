from pydantic import BaseModel

from f1_bot.models.constructor import Constructor
from f1_bot.models.driver import Driver


class RaceResult(BaseModel):
    position: int
    grid: int
    laps: int
    status: str
    points: float
    driver: Driver
    constructor: Constructor
    time: str | None = None  # race time or gap to leader
    fastest_lap_time: str | None = None
    fastest_lap_rank: int | None = None


class QualifyingResult(BaseModel):
    position: int
    driver: Driver
    constructor: Constructor
    q1: str | None = None
    q2: str | None = None
    q3: str | None = None


class SprintResult(BaseModel):
    position: int
    grid: int
    laps: int
    status: str
    points: float
    driver: Driver
    constructor: Constructor
    time: str | None = None


class SessionResult(BaseModel):
    position: int | None = None
    driver_number: int
    driver_id: str | None = None
    duration: str | float | list[str | float | None] | None = None
    gap_to_leader: str | float | list[str | float | None] | None = None
    number_of_laps: int | None = None
    dnf: bool = False
    dns: bool = False
    dsq: bool = False


class LapTime(BaseModel):
    lap_number: int
    driver_id: str
    position: int | None = None
    time: str | None = None
    date_start: str | None = None  # OpenF1 lap start timestamp
    # OpenF1 sector times
    duration_sector_1: float | None = None
    duration_sector_2: float | None = None
    duration_sector_3: float | None = None
    # OpenF1 speed traps (km/h)
    i1_speed: float | None = None
    i2_speed: float | None = None
    speed_trap: float | None = None
    lap_duration: float | None = None  # total lap time in seconds from OpenF1


class PitStop(BaseModel):
    driver_id: str
    lap: int
    stop_number: int
    duration: float | None = None  # total pit stop duration in seconds
    pit_out_time: str | None = None
    pit_in_time: str | None = None


def is_classified_finish(status: str) -> bool:
    """Whitelist finish classification: 'Finished' or lapped ('+N Lap(s)').

    Everything else — every failure string — is a DNF. Whitelisting keeps an unseen
    failure string from ever being misread as a finish.
    """
    return status == "Finished" or status.startswith("+")
