from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime

import structlog

from f1_bot.models.constructor import ConstructorStanding
from f1_bot.models.driver import DriverStanding
from f1_bot.models.notification import NotificationSubscription
from f1_bot.models.race import Race
from f1_bot.models.user import UserPreference
from f1_bot.storage.postgres_store import PostgresStore

log = structlog.get_logger(__name__)

_MAX_LAPS_CACHE = 30


class Repository:
    """Unified data access: PostgreSQL store."""

    def __init__(self, store: PostgresStore) -> None:
        self._store = store
        self._laps_cache: OrderedDict = OrderedDict()

    # --- Schedule ---

    async def get_schedule(self, season: int) -> list[Race]:
        rows = await self._store.get_races(season)
        if rows:
            return [Race.model_validate(r) for r in rows]
        return []

    async def get_circuits_for_season(self, season: int) -> list:
        """Extract ordered, unique circuits from the current season schedule."""
        races = await self.get_schedule(season)
        seen = set()
        circuits = []
        for r in races:
            if r.circuit.circuit_id not in seen:
                seen.add(r.circuit.circuit_id)
                circuits.append((r.round, r.circuit))
        return circuits  # list of (round_num, Circuit) tuples, ordered by round

    async def save_schedule(self, season: int, races: list[Race]) -> None:
        races_json = [r.model_dump(mode="json") for r in races]
        await self._store.save_races(season, races_json)

    async def get_next_race(self, season: int) -> Race | None:
        races = await self.get_schedule(season)
        today = datetime.now(UTC).date()
        upcoming = [r for r in races if r.date >= today]
        return upcoming[0] if upcoming else None

    async def get_schedule_bounds(
        self,
        season: int,
        reference_dt: datetime | None = None,
        races: list[Race] | None = None,
    ) -> dict:
        from f1_bot.formatting.timezone import combine_race_dt

        if reference_dt is None:
            reference_dt = datetime.now(UTC)
        elif reference_dt.tzinfo is None:
            reference_dt = reference_dt.replace(tzinfo=UTC)

        if races is None:
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
        rows = await self._store.get_driver_standings(season)
        if rows:
            return [DriverStanding.model_validate(s) for s in rows]
        return []

    async def save_driver_standings(
        self, season: int, standings: list[DriverStanding], round_after: int = 0
    ) -> None:
        data = [s.model_dump(mode="json") for s in standings]
        await self._store.save_driver_standings(season, round_after, data)

    async def get_constructor_standings(self, season: int) -> list[ConstructorStanding]:
        rows = await self._store.get_constructor_standings(season)
        if rows:
            return [ConstructorStanding.model_validate(s) for s in rows]
        return []

    async def save_constructor_standings(
        self,
        season: int,
        standings: list[ConstructorStanding],
        round_after: int = 0,
    ) -> None:
        data = [s.model_dump(mode="json") for s in standings]
        await self._store.save_constructor_standings(season, round_after, data)

    # --- Results ---

    async def get_race_results(self, season: int, round_num: int) -> list | None:
        return await self._store.get_results(season, round_num, "race")

    async def save_race_results(self, season: int, round_num: int, results: list) -> None:
        data = [r.model_dump(mode="json") for r in results]
        await self._store.save_results(season, round_num, "race", data)

    async def get_qualifying_results(self, season: int, round_num: int) -> list | None:
        return await self._store.get_results(season, round_num, "qualifying")

    async def save_qualifying_results(self, season: int, round_num: int, results: list) -> None:
        data = [r.model_dump(mode="json") for r in results]
        await self._store.save_results(season, round_num, "qualifying", data)

    async def get_sprint_results(self, season: int, round_num: int) -> list | None:
        return await self._store.get_results(season, round_num, "sprint")

    async def save_sprint_results(self, season: int, round_num: int, results: list) -> None:
        data = [r.model_dump(mode="json") for r in results]
        await self._store.save_results(season, round_num, "sprint", data)

    async def get_session_results(
        self, season: int, round_num: int, session_key: str | int
    ) -> list | None:
        return await self._store.get_results(season, round_num, f"session:{session_key}")

    async def save_session_results(
        self,
        season: int,
        round_num: int,
        session_key: str | int,
        results: list,
    ) -> None:
        data = [r.model_dump(mode="json") for r in results]
        await self._store.save_results(season, round_num, f"session:{session_key}", data)

    # --- Lap Timings ---

    async def get_lap_timings(self, season: int, round_num: int) -> list:
        key = (season, round_num)
        if key in self._laps_cache:
            self._laps_cache.move_to_end(key)
            return self._laps_cache[key]
        from f1_bot.models.results import LapTime

        rows = await self._store.get_lap_timings(season, round_num)
        if rows:
            result = [LapTime.model_validate(r) for r in rows]
            self._laps_cache[key] = result
            if len(self._laps_cache) > _MAX_LAPS_CACHE:
                self._laps_cache.popitem(last=False)
            return result
        return []

    async def save_lap_timings(self, season: int, round_num: int, timings: list) -> None:
        data = [t.model_dump(mode="json") for t in timings]
        await self._store.save_lap_timings(season, round_num, data)
        key = (season, round_num)
        if key in self._laps_cache:
            del self._laps_cache[key]

    # --- Pit Stops ---

    async def get_pit_stops(self, season: int, round_num: int) -> list[dict] | None:
        return await self._store.get_pit_stops(season, round_num)

    async def save_pit_stops(self, season: int, round_num: int, stops: list) -> None:
        data = [s.model_dump(mode="json") for s in stops]
        await self._store.save_pit_stops(season, round_num, data)

    # --- User Preferences ---

    async def get_user_preference(self, telegram_id: int) -> UserPreference | None:
        return await self._store.get_user_preference(telegram_id)

    async def upsert_user_preference(self, pref: UserPreference) -> None:
        await self._store.upsert_user_preference(pref)

    async def get_user_timezone(self, telegram_id: int) -> str:
        pref = await self.get_user_preference(telegram_id)
        return pref.timezone if pref else "UTC"

    # --- Drivers / Circuits ---

    async def save_drivers(self, season: int, drivers: list) -> None:
        data = [d.model_dump(mode="json") for d in drivers]
        await self._store.save_drivers(data)

    async def get_drivers_map(self, season: int) -> dict:
        """Return {permanent_number(int): Driver} map from cached drivers."""
        from f1_bot.models.driver import Driver

        rows = await self._store.get_drivers()
        drivers = [Driver.model_validate(r) for r in rows]
        # Sort so that openf1 drivers come first, then jolpica drivers,
        # ensuring jolpica drivers overwrite openf1 drivers for the same permanent_number key.
        drivers.sort(key=lambda d: 1 if d.driver_id.startswith("openf1_") else 2)

        result = {}
        for d in drivers:
            if d.permanent_number and d.permanent_number.isdigit():
                result[int(d.permanent_number)] = d
        return result

    async def get_drivers_by_id_map(self, season: int) -> dict:
        """Return {driver_id(str): Driver} map from cached drivers."""
        from f1_bot.models.driver import Driver

        rows = await self._store.get_drivers()
        drivers = [Driver.model_validate(r) for r in rows]

        # Build lookup for jolpica drivers by number
        jolpica_by_number = {
            int(d.permanent_number): d
            for d in drivers
            if not d.driver_id.startswith("openf1_")
            and d.permanent_number
            and d.permanent_number.isdigit()
        }

        # Sort: openf1 first, jolpica last (so jolpica overwrites number keys)
        drivers.sort(key=lambda d: 1 if d.driver_id.startswith("openf1_") else 2)

        result = {}
        for d in drivers:
            # Map openf1 driver_id to jolpica Driver if same permanent number exists
            if (
                d.driver_id.startswith("openf1_")
                and d.permanent_number
                and d.permanent_number.isdigit()
            ):
                mapped = jolpica_by_number.get(int(d.permanent_number))
                if mapped:
                    result[d.driver_id] = mapped
                    continue

            result[d.driver_id] = d
            if d.permanent_number:
                result[d.permanent_number] = d
                if d.permanent_number.isdigit():
                    result[int(d.permanent_number)] = d
        return result

    async def save_circuits(self, season: int, circuits: list) -> None:
        data = [c.model_dump(mode="json") for c in circuits]
        await self._store.save_circuits(data)

    # --- Sync Metadata ---

    async def get_sync_metadata(self, entity: str) -> str | None:
        return await self._store.get_sync_metadata(entity)

    async def set_sync_metadata(self, entity: str) -> None:
        await self._store.set_sync_metadata(entity)

    # --- Schedule Audit ---

    async def log_schedule_change(
        self, season: int, round_num: int, field: str, old_value: str | None, new_value: str | None
    ) -> None:
        await self._store.log_schedule_change(season, round_num, field, old_value, new_value)

    # --- Results queries for unified /results ---

    async def get_all_result_types(self, season: int, round_num: int) -> list[str]:
        """Return all result types stored for a given season/round."""
        return await self._store.get_all_result_types(season, round_num)

    async def get_last_result_round(self, season: int) -> int | None:
        """Return the highest round with any result data."""
        return await self._store.get_last_result_round(season)

    async def get_all_results_by_type_prefix(self, type_prefix: str) -> list[dict]:
        """Return list of dicts with keys: season, round, type, data_json."""
        return await self._store.get_all_results_by_type_prefix(type_prefix)

    async def get_results_by_type(
        self, season: int, round_num: int, result_type: str
    ) -> list[dict] | None:
        """Return raw results for any type key (e.g. 'session:fp1:12345')."""
        return await self._store.get_results(season, round_num, result_type)

    # --- Notifications ---

    async def subscribe_notification(self, sub: NotificationSubscription) -> int:
        return await self._store.save_notification(sub)

    async def unsubscribe_notification(
        self, telegram_id: int, season: int, round_num: int, session_key: str, minutes_before: int
    ) -> bool:
        return await self._store.delete_notification(
            telegram_id, season, round_num, session_key, minutes_before
        )

    async def unsubscribe_notification_by_id(self, notification_id: int, telegram_id: int) -> bool:
        return await self._store.delete_notification_by_id(notification_id, telegram_id)

    async def get_user_notifications(
        self, telegram_id: int, season: int
    ) -> list[NotificationSubscription]:
        return await self._store.get_user_notifications(telegram_id, season)

    async def get_pending_notifications(self, now: datetime) -> list[NotificationSubscription]:
        return await self._store.get_pending_notifications(now)

    async def mark_notifications_sent(self, ids: list[int]) -> None:
        await self._store.mark_notifications_sent(ids)

    async def has_notification(
        self, telegram_id: int, season: int, round_num: int, session_key: str, minutes_before: int
    ) -> bool:
        return await self._store.has_notification(
            telegram_id, season, round_num, session_key, minutes_before
        )

    async def remove_dead_user(self, telegram_id: int) -> None:
        await self._store.delete_notifications_for_user(telegram_id)

    async def get_next_fire_at(self) -> datetime | None:
        return await self._store.get_next_fire_at()

    async def delete_all_user_notifications(self, telegram_id: int) -> int:
        return await self._store.delete_notifications_for_user(telegram_id)
