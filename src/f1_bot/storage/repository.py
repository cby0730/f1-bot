from datetime import UTC, date, datetime

import structlog

from f1_bot.models.constructor import ConstructorStanding
from f1_bot.models.driver import DriverStanding
from f1_bot.models.race import Race
from f1_bot.models.user import UserPreference
from f1_bot.storage.sqlite_store import SQLiteStore

log = structlog.get_logger(__name__)


class Repository:
    """Unified data access: pure SQLite store (Redis removed)."""

    def __init__(self, sqlite: SQLiteStore) -> None:
        self.sqlite = sqlite

    # --- Schedule ---

    async def get_schedule(self, season: int) -> list[Race]:
        rows = await self.sqlite.get_races(season)
        if rows:
            return [Race.model_validate(r) for r in rows]
        return []

    async def save_schedule(self, season: int, races: list[Race]) -> None:
        races_json = [r.model_dump(mode="json") for r in races]
        await self.sqlite.save_races(season, races_json)

    async def get_next_race(self, season: int) -> Race | None:
        races = await self.get_schedule(season)
        today = date.today()
        upcoming = [r for r in races if r.date >= today]
        return upcoming[0] if upcoming else None

    async def get_schedule_bounds(self, season: int, reference_dt: datetime | None = None) -> dict:
        from datetime import datetime

        from f1_bot.formatting.timezone import combine_race_dt

        if reference_dt is None:
            reference_dt = datetime.now(UTC)
        elif reference_dt.tzinfo is None:
            reference_dt = reference_dt.replace(tzinfo=UTC)

        races = await self.get_schedule(season)
        races = sorted(races, key=lambda r: r.round)

        total_rounds = max([r.round for r in races]) if races else 0
        completed_races = []
        upcoming_races = []
        sprint_rounds = []
        completed_sprint_rounds = []

        for r in races:
            race_dt = combine_race_dt(r.date, r.time)
            if race_dt <= reference_dt:
                completed_races.append(r)
                if r.sprint is not None:
                    completed_sprint_rounds.append(r.round)
            else:
                upcoming_races.append(r)

            if r.sprint is not None:
                sprint_rounds.append(r.round)

        completed_rounds = len(completed_races)
        upcoming_rounds = len(upcoming_races)

        last_completed_round = completed_races[-1].round if completed_races else None
        next_upcoming_round = upcoming_races[0].round if upcoming_races else None

        return {
            "total_rounds": total_rounds,
            "completed_rounds": completed_rounds,
            "upcoming_rounds": upcoming_rounds,
            "last_completed_round": last_completed_round,
            "next_upcoming_round": next_upcoming_round,
            "sprint_rounds": sprint_rounds,
            "completed_sprint_rounds": completed_sprint_rounds,
        }

    # --- Standings ---

    async def get_driver_standings(self, season: int) -> list[DriverStanding]:
        rows = await self.sqlite.get_driver_standings(season)
        if rows:
            return [DriverStanding.model_validate(s) for s in rows]
        return []

    async def save_driver_standings(
        self, season: int, standings: list[DriverStanding], round_after: int = 0, ttl: int = 21600
    ) -> None:
        data = [s.model_dump(mode="json") for s in standings]
        await self.sqlite.save_driver_standings(season, round_after, data)

    async def get_constructor_standings(self, season: int) -> list[ConstructorStanding]:
        rows = await self.sqlite.get_constructor_standings(season)
        if rows:
            return [ConstructorStanding.model_validate(s) for s in rows]
        return []

    async def save_constructor_standings(
        self,
        season: int,
        standings: list[ConstructorStanding],
        round_after: int = 0,
        ttl: int = 21600,
    ) -> None:
        data = [s.model_dump(mode="json") for s in standings]
        await self.sqlite.save_constructor_standings(season, round_after, data)

    # --- Results ---

    async def get_race_results(self, season: int, round_num: int) -> list | None:
        return await self.sqlite.get_results(season, round_num, "race")

    async def save_race_results(
        self, season: int, round_num: int, results: list, ttl: int = 86400
    ) -> None:
        data = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in results]
        await self.sqlite.save_results(season, round_num, "race", data)

    async def get_qualifying_results(self, season: int, round_num: int) -> list | None:
        return await self.sqlite.get_results(season, round_num, "qualifying")

    async def save_qualifying_results(
        self, season: int, round_num: int, results: list, ttl: int = 86400
    ) -> None:
        data = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in results]
        await self.sqlite.save_results(season, round_num, "qualifying", data)

    async def get_sprint_results(self, season: int, round_num: int) -> list | None:
        return await self.sqlite.get_results(season, round_num, "sprint")

    async def save_sprint_results(
        self, season: int, round_num: int, results: list, ttl: int = 86400
    ) -> None:
        data = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in results]
        await self.sqlite.save_results(season, round_num, "sprint", data)

    async def get_session_results(
        self, season: int, round_num: int, session_key: int
    ) -> list | None:
        return await self.sqlite.get_results(season, round_num, f"session:{session_key}")

    async def save_session_results(
        self,
        season: int,
        round_num: int,
        session_key: int,
        results: list,
        ttl: int = 86400,
    ) -> None:
        data = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in results]
        await self.sqlite.save_results(season, round_num, f"session:{session_key}", data)

    # --- Lap Timings ---

    async def get_lap_timings(self, season: int, round_num: int) -> list[dict] | None:
        return await self.sqlite.get_lap_timings(season, round_num)

    async def save_lap_timings(self, season: int, round_num: int, timings: list) -> None:
        data = [t.model_dump(mode="json") if hasattr(t, "model_dump") else t for t in timings]
        await self.sqlite.save_lap_timings(season, round_num, data)

    # --- Pit Stops ---

    async def get_pit_stops(self, season: int, round_num: int) -> list[dict] | None:
        return await self.sqlite.get_pit_stops(season, round_num)

    async def save_pit_stops(self, season: int, round_num: int, stops: list) -> None:
        data = [s.model_dump(mode="json") if hasattr(s, "model_dump") else s for s in stops]
        await self.sqlite.save_pit_stops(season, round_num, data)

    # --- User Preferences ---

    async def get_user_preference(self, telegram_id: int) -> UserPreference | None:
        return await self.sqlite.get_user_preference(telegram_id)

    async def upsert_user_preference(self, pref: UserPreference) -> None:
        await self.sqlite.upsert_user_preference(pref)

    async def get_user_timezone(self, telegram_id: int) -> str:
        pref = await self.get_user_preference(telegram_id)
        return pref.timezone if pref else "UTC"

    # --- Drivers / Circuits ---

    async def save_drivers(self, season: int, drivers: list) -> None:
        data = [d.model_dump(mode="json") if hasattr(d, "model_dump") else d for d in drivers]
        await self.sqlite.save_drivers(data)

    async def get_drivers_map(self, season: int) -> dict:
        """Return {permanent_number(int): Driver} map from cached drivers."""
        from f1_bot.models.driver import Driver

        rows = await self.sqlite.get_drivers()
        result = {}
        for r in rows:
            d = Driver.model_validate(r)
            if d.permanent_number and d.permanent_number.isdigit():
                result[int(d.permanent_number)] = d
        return result

    async def save_circuits(self, season: int, circuits: list) -> None:
        data = [c.model_dump(mode="json") if hasattr(c, "model_dump") else c for c in circuits]
        await self.sqlite.save_circuits(data)

    # --- Sync Metadata ---

    async def get_sync_metadata(self, entity: str) -> str | None:
        return await self.sqlite.get_sync_metadata(entity)

    async def set_sync_metadata(self, entity: str) -> None:
        await self.sqlite.set_sync_metadata(entity)

    # --- Schedule Audit ---

    async def log_schedule_change(
        self, season: int, round_num: int, field: str, old_value: str | None, new_value: str | None
    ) -> None:
        await self.sqlite.log_schedule_change(season, round_num, field, old_value, new_value)

    # --- Results queries for unified /results ---

    async def get_all_result_types(self, season: int, round_num: int) -> list[str]:
        """Return all result types stored for a given season/round."""
        return await self.sqlite.get_all_result_types(season, round_num)

    async def get_last_result_round(self, season: int) -> int | None:
        """Return the highest round with any result data."""
        return await self.sqlite.get_last_result_round(season)
