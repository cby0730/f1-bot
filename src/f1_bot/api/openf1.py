import structlog

from f1_bot.api.base import BaseAPIClient
from f1_bot.models.race import Meeting, Session
from f1_bot.models.results import LapTime, PitStop, SessionResult
from f1_bot.utils.rate_limiter import RateLimiter

log = structlog.get_logger(__name__)


class OpenF1Client(BaseAPIClient):
    """Client for the OpenF1 API — sessions, results, laps, pit stops, and timezone offsets."""

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
