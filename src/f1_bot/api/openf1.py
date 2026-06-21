import structlog

from f1_bot.api.base import BaseAPIClient
from f1_bot.models.live import (
    LiveInterval,
    LivePosition,
    RaceControlMessage,
    WeatherData,
)
from f1_bot.models.race import Meeting, Session
from f1_bot.models.results import LapTime, PitStop, SessionResult
from f1_bot.utils.rate_limiter import RateLimiter

log = structlog.get_logger(__name__)


class OpenF1Client(BaseAPIClient):
    """Client for the OpenF1 API — live timing, sessions, and timezone offsets."""

    def __init__(self, base_url: str, rate_limiter: RateLimiter) -> None:
        super().__init__(base_url, rate_limiter)

    async def get_meetings(self, **filters) -> list[Meeting]:
        data = await self.get("/meetings", params=filters or None)
        meetings = []
        for m in data:
            meetings.append(
                Meeting(
                    meeting_key=m["meeting_key"],
                    meeting_name=m.get("meeting_name", ""),
                    meeting_official_name=m.get("meeting_official_name"),
                    location=m.get("location"),
                    country_name=m.get("country_name"),
                    circuit_short_name=m.get("circuit_short_name"),
                    date_start=m.get("date_start"),
                    gmt_offset=m.get("gmt_offset"),
                    year=m.get("year", 0),
                )
            )
        return meetings

    async def get_sessions(self, **filters) -> list[Session]:
        data = await self.get("/sessions", params=filters or None)
        sessions = []
        for s in data:
            sessions.append(
                Session(
                    session_key=s["session_key"],
                    session_name=s.get("session_name", ""),
                    session_type=s.get("session_type", ""),
                    meeting_key=s.get("meeting_key", 0),
                    date_start=s.get("date_start"),
                    date_end=s.get("date_end"),
                    gmt_offset=s.get("gmt_offset"),
                    year=s.get("year", 0),
                )
            )
        return sessions

    async def get_positions(self, **filters) -> list[LivePosition]:
        data = await self.get("/position", params=filters or None)
        return [
            LivePosition(
                session_key=p["session_key"],
                driver_number=p["driver_number"],
                position=p["position"],
                date=p.get("date"),
            )
            for p in data
        ]

    async def get_intervals(self, **filters) -> list[LiveInterval]:
        data = await self.get("/intervals", params=filters or None)
        return [
            LiveInterval(
                session_key=i["session_key"],
                driver_number=i["driver_number"],
                gap_to_leader=str(i["gap_to_leader"])
                if i.get("gap_to_leader") is not None
                else None,
                interval=str(i["interval"]) if i.get("interval") is not None else None,
                date=i.get("date"),
            )
            for i in data
        ]

    async def get_race_control(self, **filters) -> list[RaceControlMessage]:
        data = await self.get("/race_control", params=filters or None)
        return [
            RaceControlMessage(
                session_key=m["session_key"],
                category=m.get("category", "Other"),
                flag=m.get("flag"),
                scope=m.get("scope"),
                sector=m.get("sector"),
                driver_number=m.get("driver_number"),
                message=m.get("message", ""),
                date=m.get("date", ""),
            )
            for m in data
        ]

    async def get_pit(self, **filters) -> list[PitStop]:
        data = await self.get("/pit", params=filters or None)
        return [
            PitStop(
                driver_id=str(p["driver_number"]),
                lap=p.get("lap_number", 0),
                stop_number=p.get("stop_number", 1),
                duration=p.get("pit_duration"),
                pit_out_time=p.get("date"),
            )
            for p in data
        ]

    async def get_laps(self, **filters) -> list[LapTime]:
        data = await self.get("/laps", params=filters or None)
        return [
            LapTime(
                lap_number=lap.get("lap_number", 0),
                driver_id=str(lap["driver_number"]),
                date_start=lap.get("date_start"),
                duration_sector_1=lap.get("duration_sector_1"),
                duration_sector_2=lap.get("duration_sector_2"),
                duration_sector_3=lap.get("duration_sector_3"),
                i1_speed=lap.get("i1_speed"),
                i2_speed=lap.get("i2_speed"),
                speed_trap=lap.get("st_speed"),
                lap_duration=lap.get("lap_duration"),
            )
            for lap in data
        ]

    async def get_weather(self, **filters) -> list[WeatherData]:
        data = await self.get("/weather", params=filters or None)
        return [
            WeatherData(
                session_key=w["session_key"],
                air_temperature=w.get("air_temperature"),
                track_temperature=w.get("track_temperature"),
                humidity=w.get("humidity"),
                pressure=w.get("pressure"),
                wind_speed=w.get("wind_speed"),
                wind_direction=w.get("wind_direction"),
                rainfall=w.get("rainfall"),
                date=w.get("date"),
            )
            for w in data
        ]

    async def get_session_results(self, **filters) -> list[SessionResult]:
        data = await self.get("/session_result", params=filters or None)
        return [
            SessionResult(
                position=r.get("position"),
                driver_number=r["driver_number"],
                duration=r.get("duration"),
                gap_to_leader=r.get("gap_to_leader"),
                number_of_laps=r.get("number_of_laps"),
                dnf=bool(r.get("dnf", False)),
                dns=bool(r.get("dns", False)),
                dsq=bool(r.get("dsq", False)),
            )
            for r in data
        ]

    async def get_drivers(self, **filters) -> list[dict]:
        """Retrieve driver profiles from OpenF1."""
        return await self.get("/drivers", params=filters or None)
