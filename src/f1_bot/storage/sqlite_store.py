import json
from datetime import UTC, datetime

import aiosqlite
import structlog

from f1_bot.models.user import UserPreference

log = structlog.get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS races (
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    name TEXT NOT NULL,
    circuit_id TEXT NOT NULL,
    circuit_name TEXT,
    locality TEXT,
    country TEXT,
    race_date TEXT NOT NULL,
    race_time TEXT,
    gmt_offset TEXT,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round)
);

CREATE TABLE IF NOT EXISTS standings_drivers (
    season INTEGER NOT NULL,
    round_after INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round_after)
);

CREATE TABLE IF NOT EXISTS standings_constructors (
    season INTEGER NOT NULL,
    round_after INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round_after)
);

CREATE TABLE IF NOT EXISTS results (
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    type TEXT NOT NULL DEFAULT 'race',
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round, type)
);

CREATE TABLE IF NOT EXISTS drivers (
    driver_id TEXT PRIMARY KEY,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS circuits (
    circuit_id TEXT PRIMARY KEY,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_preferences (
    telegram_id INTEGER PRIMARY KEY,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lap_timings (
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round)
);

CREATE TABLE IF NOT EXISTS pit_stops (
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round)
);

CREATE TABLE IF NOT EXISTS schedule_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_metadata (
    entity TEXT PRIMARY KEY,
    last_synced_at TEXT NOT NULL
);
"""


class SQLiteStore:
    """Persistent store for historical data and user preferences."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

        # Database migration: remove old session result formats
        await self._conn.execute(
            "DELETE FROM results WHERE type LIKE 'session:%' AND type NOT LIKE 'session:%:%'"
        )
        await self._conn.commit()

        log.info("sqlite_initialized", path=self._db_path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    # --- Schedule ---

    async def save_races(self, season: int, races_json: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute("DELETE FROM races WHERE season=?", (season,))
        async with self._conn.executemany(
            """INSERT INTO races
               (season, round, name, circuit_id, circuit_name, locality, country,
                race_date, race_time, gmt_offset, data_json, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    r["season"],
                    r["round"],
                    r["name"],
                    r["circuit"]["circuit_id"],
                    r["circuit"]["name"],
                    r["circuit"]["locality"],
                    r["circuit"]["country"],
                    r["date"],
                    r.get("time"),
                    r.get("gmt_offset"),
                    json.dumps(r),
                    now,
                )
                for r in races_json
            ],
        ):
            pass
        await self._conn.commit()

    async def get_races(self, season: int) -> list[dict]:
        async with self._conn.execute(
            "SELECT data_json FROM races WHERE season=? ORDER BY round", (season,)
        ) as cur:
            rows = await cur.fetchall()
        return [json.loads(r["data_json"]) for r in rows]

    # --- Standings ---

    async def save_driver_standings(self, season: int, round_after: int, data: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute(
            "INSERT OR REPLACE INTO standings_drivers VALUES (?,?,?,?)",
            (season, round_after, json.dumps(data), now),
        )
        await self._conn.commit()

    async def get_driver_standings(self, season: int) -> list[dict] | None:
        async with self._conn.execute(
            "SELECT data_json FROM standings_drivers WHERE season=? ORDER BY round_after DESC LIMIT 1",
            (season,),
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    async def save_constructor_standings(
        self, season: int, round_after: int, data: list[dict]
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute(
            "INSERT OR REPLACE INTO standings_constructors VALUES (?,?,?,?)",
            (season, round_after, json.dumps(data), now),
        )
        await self._conn.commit()

    async def get_constructor_standings(self, season: int) -> list[dict] | None:
        async with self._conn.execute(
            "SELECT data_json FROM standings_constructors WHERE season=? ORDER BY round_after DESC LIMIT 1",
            (season,),
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    # --- Results ---

    async def save_results(
        self, season: int, round_num: int, result_type: str, data: list[dict]
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute(
            "INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)",
            (season, round_num, result_type, json.dumps(data), now),
        )
        await self._conn.commit()

    async def get_results(
        self, season: int, round_num: int, result_type: str = "race"
    ) -> list[dict] | None:
        async with self._conn.execute(
            "SELECT data_json FROM results WHERE season=? AND round=? AND type=?",
            (season, round_num, result_type),
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    async def get_last_race_round(self, season: int) -> int | None:
        async with self._conn.execute(
            "SELECT MAX(round) as r FROM results WHERE season=? AND type='race'",
            (season,),
        ) as cur:
            row = await cur.fetchone()
        return row["r"] if row and row["r"] is not None else None

    # --- User Preferences ---

    async def get_user_preference(self, telegram_id: int) -> UserPreference | None:
        async with self._conn.execute(
            "SELECT * FROM user_preferences WHERE telegram_id=?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        return UserPreference(
            telegram_id=row["telegram_id"],
            timezone=row["timezone"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def upsert_user_preference(self, pref: UserPreference) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute(
            """INSERT INTO user_preferences (telegram_id, timezone, created_at, updated_at)
               VALUES (?,?,?,?)
               ON CONFLICT(telegram_id) DO UPDATE SET timezone=excluded.timezone, updated_at=excluded.updated_at""",
            (pref.telegram_id, pref.timezone, now, now),
        )
        await self._conn.commit()

    # --- Lap Timings ---

    async def save_lap_timings(self, season: int, round_num: int, data: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute(
            "INSERT OR REPLACE INTO lap_timings VALUES (?,?,?,?)",
            (season, round_num, json.dumps(data), now),
        )
        await self._conn.commit()

    async def get_lap_timings(self, season: int, round_num: int) -> list[dict] | None:
        async with self._conn.execute(
            "SELECT data_json FROM lap_timings WHERE season=? AND round=?",
            (season, round_num),
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    # --- Pit Stops ---

    async def save_pit_stops(self, season: int, round_num: int, data: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute(
            "INSERT OR REPLACE INTO pit_stops VALUES (?,?,?,?)",
            (season, round_num, json.dumps(data), now),
        )
        await self._conn.commit()

    async def get_pit_stops(self, season: int, round_num: int) -> list[dict] | None:
        async with self._conn.execute(
            "SELECT data_json FROM pit_stops WHERE season=? AND round=?",
            (season, round_num),
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    # --- Schedule Audit Log ---

    async def log_schedule_change(
        self, season: int, round_num: int, field: str, old_value: str | None, new_value: str | None
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute(
            "INSERT INTO schedule_audit_log (season, round, field, old_value, new_value, changed_at) VALUES (?,?,?,?,?,?)",
            (season, round_num, field, old_value, new_value, now),
        )
        await self._conn.commit()

    # --- Sync Metadata ---

    async def get_sync_metadata(self, entity: str) -> str | None:
        async with self._conn.execute(
            "SELECT last_synced_at FROM sync_metadata WHERE entity=?", (entity,)
        ) as cur:
            row = await cur.fetchone()
        return row["last_synced_at"] if row else None

    async def set_sync_metadata(self, entity: str) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        await self._conn.execute(
            "INSERT OR REPLACE INTO sync_metadata (entity, last_synced_at) VALUES (?,?)",
            (entity, now),
        )
        await self._conn.commit()

    # --- Drivers / Circuits ---

    async def save_drivers(self, drivers_json: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        for d in drivers_json:
            await self._conn.execute(
                "INSERT OR REPLACE INTO drivers (driver_id, data_json, updated_at) VALUES (?,?,?)",
                (d["driver_id"], json.dumps(d), now),
            )
        await self._conn.commit()

    async def get_drivers(self) -> list[dict]:
        async with self._conn.execute("SELECT data_json FROM drivers") as cur:
            rows = await cur.fetchall()
        return [json.loads(r["data_json"]) for r in rows]

    async def save_circuits(self, circuits_json: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        for c in circuits_json:
            await self._conn.execute(
                "INSERT OR REPLACE INTO circuits (circuit_id, data_json, updated_at) VALUES (?,?,?)",
                (c["circuit_id"], json.dumps(c), now),
            )
        await self._conn.commit()

    async def get_all_result_types(self, season: int, round_num: int) -> list[str]:
        """Return all result types stored for a given season/round."""
        async with self._conn.execute(
            "SELECT type FROM results WHERE season=? AND round=?",
            (season, round_num),
        ) as cur:
            rows = await cur.fetchall()
        return [r["type"] for r in rows]

    async def get_last_result_round(self, season: int) -> int | None:
        """Return the highest round number that has any result data."""
        async with self._conn.execute(
            "SELECT MAX(round) as r FROM results WHERE season=?",
            (season,),
        ) as cur:
            row = await cur.fetchone()
        return row["r"] if row and row["r"] is not None else None

    async def get_all_results_by_type_prefix(self, type_prefix: str) -> list[dict]:
        """Return list of dicts with keys: season, round, type, data_json."""
        async with self._conn.execute(
            "SELECT season, round, type, data_json FROM results WHERE type LIKE ?",
            (f"{type_prefix}%",),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]
