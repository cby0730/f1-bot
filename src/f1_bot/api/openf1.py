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

    def __init__(
        self, base_url: str, rate_limiter: RateLimiter, *, proxy: str | None = None
    ) -> None:
        super().__init__(base_url, rate_limiter, proxy=proxy)

    async def get_meetings(self, **filters) -> list[Meeting]:
        data = await self.get("/meetings", params=filters or None)
        meetings = []
        for m in data:
            if "meeting_key" not in m:
                log.warning("openf1_record_skipped", method="get_meetings", record=m)
                continue
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
            if "session_key" not in s:
                log.warning("openf1_record_skipped", method="get_sessions", record=s)
                continue
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
        positions = []
        for p in data:
            if not all(k in p for k in ("session_key", "driver_number", "position")):
                continue
            positions.append(
                LivePosition(
                    session_key=p["session_key"],
                    driver_number=p["driver_number"],
                    position=p["position"],
                    date=p.get("date"),
                )
            )
        return positions

    async def get_intervals(self, **filters) -> list[LiveInterval]:
        data = await self.get("/intervals", params=filters or None)
        intervals = []
        for i in data:
            if not all(k in i for k in ("session_key", "driver_number")):
                continue
            gap = i.get("gap_to_leader")
            ivl = i.get("interval")
            intervals.append(
                LiveInterval(
                    session_key=i["session_key"],
                    driver_number=i["driver_number"],
                    gap_to_leader=str(gap) if gap is not None else None,
                    interval=str(ivl) if ivl is not None else None,
                    date=i.get("date"),
                )
            )
        return intervals

    async def get_race_control(self, **filters) -> list[RaceControlMessage]:
        data = await self.get("/race_control", params=filters or None)
        messages = []
        for m in data:
            if "session_key" not in m:
                log.warning("openf1_record_skipped", method="get_race_control", record=m)
                continue
            messages.append(
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
            )
        return messages

    async def get_pit(self, **filters) -> list[PitStop]:
        data = await self.get("/pit", params=filters or None)
        stops = []
        for p in data:
            if "driver_number" not in p:
                log.warning("openf1_record_skipped", method="get_pit", record=p)
                continue
            stops.append(
                PitStop(
                    driver_id=str(p["driver_number"]),
                    lap=p.get("lap_number", 0),
                    stop_number=p.get("stop_number", 1),
                    duration=p.get("pit_duration"),
                    pit_out_time=p.get("date"),
                )
            )
        return stops

    async def get_laps(self, **filters) -> list[LapTime]:
        data = await self.get("/laps", params=filters or None)
        laps = []
        for lap in data:
            if "driver_number" not in lap:
                log.warning("openf1_record_skipped", method="get_laps", record=lap)
                continue
            laps.append(
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
            )
        return laps

    async def get_weather(self, **filters) -> list[WeatherData]:
        data = await self.get("/weather", params=filters or None)
        weather = []
        for w in data:
            if "session_key" not in w:
                log.warning("openf1_record_skipped", method="get_weather", record=w)
                continue
            weather.append(
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
            )
        return weather

    async def get_session_results(self, **filters) -> list[SessionResult]:
        data = await self.get("/session_result", params=filters or None)
        results = []
        for r in data:
            if "driver_number" not in r:
                continue
            results.append(
                SessionResult(
                    position=r.get("position"),
                    driver_number=r["driver_number"],
                    duration=r.get("duration"),
                    gap_to_leader=r.get("gap_to_leader"),
                    number_of_laps=r.get("number_of_laps"),
                    dnf=r.get("dnf", False),
                    dns=r.get("dns", False),
                    dsq=r.get("dsq", False),
                )
            )
        return results

    async def get_drivers(self, **filters) -> list[dict]:
        """Retrieve driver profiles from OpenF1."""
        return await self.get("/drivers", params=filters or None)
