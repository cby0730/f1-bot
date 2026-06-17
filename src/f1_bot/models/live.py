from pydantic import BaseModel


class LivePosition(BaseModel):
    session_key: int
    driver_number: int
    position: int
    date: str | None = None


class LiveInterval(BaseModel):
    session_key: int
    driver_number: int
    gap_to_leader: str | None = None  # e.g. "+5.234" or "1 LAP"
    interval: str | None = None  # gap to car directly ahead
    date: str | None = None


class RaceControlMessage(BaseModel):
    session_key: int
    category: str  # e.g. "Flag", "SafetyCar", "Drs", "Other"
    flag: str | None = None  # "GREEN", "YELLOW", "RED", "SC", "VSC"
    scope: str | None = None  # "Track", "Sector", "Driver"
    sector: int | None = None
    driver_number: int | None = None
    message: str
    date: str


class WeatherData(BaseModel):
    session_key: int
    air_temperature: float | None = None
    track_temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    wind_speed: float | None = None
    wind_direction: int | None = None
    rainfall: bool | None = None
    date: str | None = None
