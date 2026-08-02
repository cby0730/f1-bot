from datetime import date
from datetime import time as dt_time

import structlog

from f1_bot.api.base import BaseAPIClient
from f1_bot.models.constructor import Constructor, ConstructorStanding
from f1_bot.models.driver import Driver, DriverStanding
from f1_bot.models.race import Circuit, Race, RaceSession
from f1_bot.models.results import (
    LapTime,
    PitStop,
    QualifyingResult,
    RaceResult,
    SprintResult,
)
from f1_bot.utils.rate_limiter import RateLimiter

log = structlog.get_logger(__name__)


def _parse_circuit(raw: dict) -> Circuit:
    loc = raw.get("Location", {})
    return Circuit(
        circuit_id=raw.get("circuitId", "unknown"),
        name=raw.get("circuitName", ""),
        locality=loc.get("locality", ""),
        country=loc.get("country", ""),
        lat=float(loc["lat"]) if "lat" in loc else None,
        lng=float(loc["long"]) if "long" in loc else None,
        url=raw.get("url"),
    )


def _parse_driver(raw: dict) -> Driver:
    return Driver(
        driver_id=raw.get("driverId", "unknown"),
        permanent_number=raw.get("permanentNumber"),
        code=raw.get("code"),
        given_name=raw.get("givenName", ""),
        family_name=raw.get("familyName", ""),
        date_of_birth=raw.get("dateOfBirth"),
        nationality=raw.get("nationality"),
        url=raw.get("url"),
    )


def _parse_constructor(raw: dict) -> Constructor:
    return Constructor(
        constructor_id=raw.get("constructorId", "unknown"),
        name=raw.get("name", ""),
        nationality=raw.get("nationality"),
        url=raw.get("url"),
    )


def _parse_session(raw: dict | None, name: str) -> RaceSession | None:
    if not raw:
        return None
    session_date = date.fromisoformat(raw["date"]) if raw.get("date") else None
    session_time = dt_time.fromisoformat(raw["time"].rstrip("Z")) if raw.get("time") else None
    return RaceSession(name=name, date=session_date, time=session_time)


def _parse_race(r: dict) -> Race:
    return Race(
        season=int(r["season"]),
        round=int(r["round"]),
        name=r["raceName"],
        circuit=_parse_circuit(r["Circuit"]),
        date=date.fromisoformat(r["date"]),
        time=dt_time.fromisoformat(r["time"].rstrip("Z")) if r.get("time") else None,
    )


class JolpicaClient(BaseAPIClient):
    """Client for the Jolpica-F1 API (Ergast successor)."""

    def __init__(
        self, base_url: str, rate_limiter: RateLimiter, *, proxy: str | None = None
    ) -> None:
        super().__init__(base_url, rate_limiter, proxy=proxy)

    async def get_current_schedule(self) -> list[Race]:
        data = await self.get("/current.json")
        try:
            races_raw = data["MRData"]["RaceTable"]["Races"]
        except (KeyError, TypeError) as e:
            log.warning("jolpica_malformed_response", method="get_current_schedule", error=str(e))
            return []
        races = []
        for r in races_raw:
            race_date = date.fromisoformat(r["date"])
            race_time = dt_time.fromisoformat(r["time"].rstrip("Z")) if r.get("time") else None
            races.append(
                Race(
                    season=int(r["season"]),
                    round=int(r["round"]),
                    name=r["raceName"],
                    url=r.get("url"),
                    circuit=_parse_circuit(r["Circuit"]),
                    date=race_date,
                    time=race_time,
                    fp1=_parse_session(r.get("FirstPractice"), "FP1"),
                    fp2=_parse_session(r.get("SecondPractice"), "FP2"),
                    fp3=_parse_session(r.get("ThirdPractice"), "FP3"),
                    qualifying=_parse_session(r.get("Qualifying"), "Qualifying"),
                    sprint_qualifying=_parse_session(
                        r.get("SprintQualifying"), "Sprint Qualifying"
                    ),
                    sprint=_parse_session(r.get("Sprint"), "Sprint"),
                )
            )
        log.debug("jolpica_schedule_fetched", count=len(races))
        return races

    async def get_driver_standings(self, season: str = "current") -> list[DriverStanding]:
        data = await self.get(f"/{season}/driverstandings.json")
        try:
            standings_lists = data["MRData"]["StandingsTable"]["StandingsLists"]
            if not standings_lists:
                return []
            standings = []
            for s in standings_lists[0]["DriverStandings"]:
                standings.append(
                    DriverStanding(
                        position=int(s["position"]),
                        points=float(s["points"]),
                        wins=int(s["wins"]),
                        driver=_parse_driver(s["Driver"]),
                        constructor_name=(
                            s["Constructors"][0]["name"] if s.get("Constructors") else ""
                        ),
                    )
                )
        except (KeyError, TypeError) as e:
            log.warning("jolpica_malformed_response", method="get_driver_standings", error=str(e))
            return []
        return standings

    async def get_constructor_standings(self, season: str = "current") -> list[ConstructorStanding]:
        data = await self.get(f"/{season}/constructorstandings.json")
        try:
            standings_lists = data["MRData"]["StandingsTable"]["StandingsLists"]
            if not standings_lists:
                return []
            standings = []
            for s in standings_lists[0]["ConstructorStandings"]:
                standings.append(
                    ConstructorStanding(
                        position=int(s["position"]),
                        points=float(s["points"]),
                        wins=int(s["wins"]),
                        constructor=_parse_constructor(s["Constructor"]),
                    )
                )
        except (KeyError, TypeError) as e:
            log.warning(
                "jolpica_malformed_response", method="get_constructor_standings", error=str(e)
            )
            return []
        return standings

    async def get_race_results(
        self, season: str = "current", round_num: str = "last"
    ) -> tuple[Race | None, list[RaceResult]]:
        data = await self.get(f"/{season}/{round_num}/results.json")
        try:
            races_raw = data["MRData"]["RaceTable"]["Races"]
        except (KeyError, TypeError) as e:
            log.warning("jolpica_malformed_response", method="get_race_results", error=str(e))
            return None, []
        if not races_raw:
            return None, []
        r = races_raw[0]
        race = _parse_race(r)
        results = []
        for res in r.get("Results", []):
            fl = res.get("FastestLap", {})
            results.append(
                RaceResult(
                    position=int(res["position"]),
                    grid=int(res.get("grid", 0)),
                    laps=int(res.get("laps", 0)),
                    status=res.get("status", ""),
                    points=float(res.get("points", 0)),
                    driver=_parse_driver(res["Driver"]),
                    constructor=_parse_constructor(res["Constructor"]),
                    time=res.get("Time", {}).get("time") or res.get("status"),
                    fastest_lap_time=fl.get("Time", {}).get("time"),
                    fastest_lap_rank=int(fl["rank"]) if fl.get("rank") else None,
                )
            )
        return race, results

    async def get_qualifying_results(
        self, season: str = "current", round_num: str = "last"
    ) -> tuple[Race | None, list[QualifyingResult]]:
        data = await self.get(f"/{season}/{round_num}/qualifying.json")
        try:
            races_raw = data["MRData"]["RaceTable"]["Races"]
        except (KeyError, TypeError) as e:
            log.warning("jolpica_malformed_response", method="get_qualifying_results", error=str(e))
            return None, []
        if not races_raw:
            return None, []
        r = races_raw[0]
        race = _parse_race(r)
        results = []
        for res in r.get("QualifyingResults", []):
            results.append(
                QualifyingResult(
                    position=int(res["position"]),
                    driver=_parse_driver(res["Driver"]),
                    constructor=_parse_constructor(res["Constructor"]),
                    q1=res.get("Q1"),
                    q2=res.get("Q2"),
                    q3=res.get("Q3"),
                )
            )
        return race, results

    async def get_sprint_results(
        self, season: str = "current", round_num: str = "last"
    ) -> tuple[Race | None, list[SprintResult]]:
        data = await self.get(f"/{season}/{round_num}/sprint.json")
        try:
            races_raw = data["MRData"]["RaceTable"]["Races"]
        except (KeyError, TypeError) as e:
            log.warning("jolpica_malformed_response", method="get_sprint_results", error=str(e))
            return None, []
        if not races_raw:
            return None, []
        r = races_raw[0]
        race = _parse_race(r)
        results = []
        for res in r.get("SprintResults", []):
            results.append(
                SprintResult(
                    position=int(res["position"]),
                    grid=int(res.get("grid", 0)),
                    laps=int(res.get("laps", 0)),
                    status=res.get("status", ""),
                    points=float(res.get("points", 0)),
                    driver=_parse_driver(res["Driver"]),
                    constructor=_parse_constructor(res["Constructor"]),
                    time=res.get("Time", {}).get("time") or res.get("status"),
                )
            )
        return race, results

    async def get_pit_stops(
        self, season: str = "current", round_num: str = "last"
    ) -> list[PitStop]:
        data = await self.get(f"/{season}/{round_num}/pitstops.json")
        try:
            races_raw = data["MRData"]["RaceTable"]["Races"]
        except (KeyError, TypeError) as e:
            log.warning("jolpica_malformed_response", method="get_pit_stops", error=str(e))
            return []
        if not races_raw:
            return []
        stops = []
        for stop in races_raw[0].get("PitStops", []):
            duration_raw = stop.get("duration")
            try:
                duration = float(duration_raw) if duration_raw else None
            except ValueError:
                duration = None
            stops.append(
                PitStop(
                    driver_id=stop["driverId"],
                    lap=int(stop["lap"]),
                    stop_number=int(stop["stop"]),
                    duration=duration,
                )
            )
        return stops

    async def get_lap_timings(
        self, season: str = "current", round_num: str = "last"
    ) -> list[LapTime]:
        # Jolpica hard-caps at 100 entries per request regardless of limit parameter.
        # A typical race has ~1346 entries (20 drivers × ~67 laps), requiring ~14 pages.
        all_laps: list[LapTime] = []
        offset = 0
        total = 0
        while True:
            data = await self.get(
                f"/{season}/{round_num}/laps.json",
                params={"limit": 100, "offset": offset},
            )
            try:
                total = int(data["MRData"]["total"])
                races_raw = data["MRData"]["RaceTable"]["Races"]
            except (KeyError, TypeError) as e:
                log.warning("jolpica_malformed_response", method="get_lap_timings", error=str(e))
                break
            if not races_raw:
                break
            for lap_raw in races_raw[0].get("Laps", []):
                for timing in lap_raw.get("Timings", []):
                    all_laps.append(
                        LapTime(
                            lap_number=int(lap_raw["number"]),
                            driver_id=timing["driverId"],
                            position=int(timing.get("position", 0)) or None,
                            time=timing.get("time"),
                        )
                    )
            offset += 100
            if offset >= total:
                break
        if total > 5000:
            log.warning(
                "lap_timings_unexpectedly_large", season=season, round=round_num, total=total
            )
        return all_laps

    async def get_drivers(self, season: str = "current") -> list[Driver]:
        data = await self.get(f"/{season}/drivers.json")
        try:
            drivers_raw = data["MRData"]["DriverTable"]["Drivers"]
        except (KeyError, TypeError) as e:
            log.warning("jolpica_malformed_response", method="get_drivers", error=str(e))
            return []
        return [_parse_driver(d) for d in drivers_raw]

    async def get_circuits(self, season: str = "current") -> list[Circuit]:
        data = await self.get(f"/{season}/circuits.json")
        try:
            circuits_raw = data["MRData"]["CircuitTable"]["Circuits"]
        except (KeyError, TypeError) as e:
            log.warning("jolpica_malformed_response", method="get_circuits", error=str(e))
            return []
        return [_parse_circuit(c) for c in circuits_raw]
