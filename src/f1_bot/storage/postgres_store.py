from __future__ import annotations

import json
from datetime import UTC, datetime

import asyncpg
import structlog

from f1_bot.models.notification import NotificationSubscription
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
    data_json JSONB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round)
);

CREATE TABLE IF NOT EXISTS standings_drivers (
    season INTEGER NOT NULL,
    round_after INTEGER NOT NULL,
    data_json JSONB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round_after)
);

CREATE TABLE IF NOT EXISTS standings_constructors (
    season INTEGER NOT NULL,
    round_after INTEGER NOT NULL,
    data_json JSONB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round_after)
);

CREATE TABLE IF NOT EXISTS results (
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    type TEXT NOT NULL DEFAULT 'race',
    data_json JSONB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round, type)
);

CREATE TABLE IF NOT EXISTS drivers (
    driver_id TEXT PRIMARY KEY,
    data_json JSONB NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS circuits (
    circuit_id TEXT PRIMARY KEY,
    data_json JSONB NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_preferences (
    telegram_id BIGINT PRIMARY KEY,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lap_timings (
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    data_json JSONB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round)
);

CREATE TABLE IF NOT EXISTS pit_stops (
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    data_json JSONB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (season, round)
);

CREATE TABLE IF NOT EXISTS schedule_audit_log (
    id SERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS notification_subscriptions (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    session_key TEXT NOT NULL,
    minutes_before INTEGER NOT NULL,
    notified BOOLEAN NOT NULL DEFAULT FALSE,
    fire_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(telegram_id, season, round, session_key, minutes_before)
);

CREATE INDEX IF NOT EXISTS idx_results_type ON results(type);
CREATE INDEX IF NOT EXISTS idx_notif_fire ON notification_subscriptions(notified, fire_at);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notification_subscriptions(telegram_id, season);
"""


class PostgresStore:
    """Persistent store backed by PostgreSQL via asyncpg."""

    def __init__(self, database_url: str, min_pool: int = 5, max_pool: int = 20) -> None:
        self._database_url = database_url
        self._min_pool = min_pool
        self._max_pool = max_pool
        self._pool: asyncpg.Pool | None = None

    async def init(self) -> None:
        self._pool = await asyncpg.create_pool(
            self._database_url, min_size=self._min_pool, max_size=self._max_pool
        )
        # Execute schema DDL
        async with self._pool.acquire() as conn:
            await conn.execute(SCHEMA)

            # Database migration: remove old session result formats
            await conn.execute(
                "DELETE FROM results WHERE type LIKE 'session:%' AND type NOT LIKE 'session:%:%'"
            )

        log.info("postgres_initialized", url=self._database_url.split("@")[-1])

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    # --- Schedule ---

    async def save_races(self, season: int, races_json: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM races WHERE season=$1", season)
                for r in races_json:
                    await conn.execute(
                        """INSERT INTO races
                           (season, round, name, circuit_id, circuit_name, locality, country,
                            race_date, race_time, gmt_offset, data_json, updated_at)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)""",
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

    async def get_races(self, season: int) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT data_json FROM races WHERE season=$1 ORDER BY round", season
            )
        return [json.loads(r["data_json"]) for r in rows]

    # --- Standings ---

    async def save_driver_standings(self, season: int, round_after: int, data: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO standings_drivers (season, round_after, data_json, updated_at)
                   VALUES ($1,$2,$3,$4)
                   ON CONFLICT (season, round_after)
                   DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at""",
                season,
                round_after,
                json.dumps(data),
                now,
            )

    async def get_driver_standings(self, season: int) -> list[dict] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data_json FROM standings_drivers WHERE season=$1 ORDER BY round_after DESC LIMIT 1",
                season,
            )
        return json.loads(row["data_json"]) if row else None

    async def save_constructor_standings(
        self, season: int, round_after: int, data: list[dict]
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO standings_constructors (season, round_after, data_json, updated_at)
                   VALUES ($1,$2,$3,$4)
                   ON CONFLICT (season, round_after)
                   DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at""",
                season,
                round_after,
                json.dumps(data),
                now,
            )

    async def get_constructor_standings(self, season: int) -> list[dict] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data_json FROM standings_constructors WHERE season=$1 ORDER BY round_after DESC LIMIT 1",
                season,
            )
        return json.loads(row["data_json"]) if row else None

    # --- Results ---

    async def save_results(
        self, season: int, round_num: int, result_type: str, data: list[dict]
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO results (season, round, type, data_json, updated_at)
                   VALUES ($1,$2,$3,$4,$5)
                   ON CONFLICT (season, round, type)
                   DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at""",
                season,
                round_num,
                result_type,
                json.dumps(data),
                now,
            )

    async def get_results(
        self, season: int, round_num: int, result_type: str = "race"
    ) -> list[dict] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data_json FROM results WHERE season=$1 AND round=$2 AND type=$3",
                season,
                round_num,
                result_type,
            )
        return json.loads(row["data_json"]) if row else None

    async def get_last_race_round(self, season: int) -> int | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MAX(round) as r FROM results WHERE season=$1 AND type='race'",
                season,
            )
        return row["r"] if row and row["r"] is not None else None

    # --- User Preferences ---

    async def get_user_preference(self, telegram_id: int) -> UserPreference | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT telegram_id, timezone, created_at, updated_at FROM user_preferences WHERE telegram_id=$1",
                telegram_id,
            )
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
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO user_preferences (telegram_id, timezone, created_at, updated_at)
                   VALUES ($1,$2,$3,$4)
                   ON CONFLICT(telegram_id)
                   DO UPDATE SET timezone=EXCLUDED.timezone, updated_at=EXCLUDED.updated_at""",
                pref.telegram_id,
                pref.timezone,
                now,
                now,
            )

    # --- Lap Timings ---

    async def save_lap_timings(self, season: int, round_num: int, data: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO lap_timings (season, round, data_json, updated_at)
                   VALUES ($1,$2,$3,$4)
                   ON CONFLICT (season, round)
                   DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at""",
                season,
                round_num,
                json.dumps(data),
                now,
            )

    async def get_lap_timings(self, season: int, round_num: int) -> list[dict] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data_json FROM lap_timings WHERE season=$1 AND round=$2",
                season,
                round_num,
            )
        return json.loads(row["data_json"]) if row else None

    # --- Pit Stops ---

    async def save_pit_stops(self, season: int, round_num: int, data: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO pit_stops (season, round, data_json, updated_at)
                   VALUES ($1,$2,$3,$4)
                   ON CONFLICT (season, round)
                   DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at""",
                season,
                round_num,
                json.dumps(data),
                now,
            )

    async def get_pit_stops(self, season: int, round_num: int) -> list[dict] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data_json FROM pit_stops WHERE season=$1 AND round=$2",
                season,
                round_num,
            )
        return json.loads(row["data_json"]) if row else None

    # --- Schedule Audit Log ---

    async def log_schedule_change(
        self, season: int, round_num: int, field: str, old_value: str | None, new_value: str | None
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO schedule_audit_log
                   (season, round, field, old_value, new_value, changed_at)
                   VALUES ($1,$2,$3,$4,$5,$6)""",
                season,
                round_num,
                field,
                old_value,
                new_value,
                now,
            )

    # --- Sync Metadata ---

    async def get_sync_metadata(self, entity: str) -> str | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT last_synced_at FROM sync_metadata WHERE entity=$1", entity
            )
        return row["last_synced_at"] if row else None

    async def set_sync_metadata(self, entity: str) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO sync_metadata (entity, last_synced_at)
                   VALUES ($1,$2)
                   ON CONFLICT (entity)
                   DO UPDATE SET last_synced_at=EXCLUDED.last_synced_at""",
                entity,
                now,
            )

    async def save_drivers(self, drivers_json: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for d in drivers_json:
                    await conn.execute(
                        """INSERT INTO drivers (driver_id, data_json, updated_at)
                           VALUES ($1,$2,$3)
                           ON CONFLICT (driver_id)
                           DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at""",
                        d["driver_id"],
                        json.dumps(d),
                        now,
                    )

    async def get_drivers(self) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT data_json FROM drivers")
        return [json.loads(r["data_json"]) for r in rows]

    async def save_circuits(self, circuits_json: list[dict]) -> None:
        now = datetime.now(UTC).replace(tzinfo=None).isoformat()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for c in circuits_json:
                    await conn.execute(
                        """INSERT INTO circuits (circuit_id, data_json, updated_at)
                           VALUES ($1,$2,$3)
                           ON CONFLICT (circuit_id)
                           DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at""",
                        c["circuit_id"],
                        json.dumps(c),
                        now,
                    )

    async def get_all_result_types(self, season: int, round_num: int) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT type FROM results WHERE season=$1 AND round=$2",
                season,
                round_num,
            )
        return [r["type"] for r in rows]

    async def get_last_result_round(self, season: int) -> int | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MAX(round) as r FROM results WHERE season=$1",
                season,
            )
        return row["r"] if row and row["r"] is not None else None

    async def get_all_results_by_type_prefix(self, type_prefix: str) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT season, round, type, data_json FROM results WHERE type LIKE $1",
                f"{type_prefix}%",
            )
        return [dict(r) for r in rows]

    # --- Notification Subscriptions ---

    async def save_notification(self, sub: NotificationSubscription) -> int:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO notification_subscriptions
                   (telegram_id, season, round, session_key, minutes_before, notified, fire_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT (telegram_id, season, round, session_key, minutes_before)
                   DO UPDATE SET notified=FALSE, fire_at=EXCLUDED.fire_at
                   RETURNING id""",
                sub.telegram_id,
                sub.season,
                sub.round,
                sub.session_key,
                sub.minutes_before,
                sub.notified,
                sub.fire_at,
            )
        return row["id"] if row else 0

    async def delete_notification(
        self, telegram_id: int, season: int, round_num: int, session_key: str, minutes_before: int
    ) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """DELETE FROM notification_subscriptions
                   WHERE telegram_id=$1 AND season=$2 AND round=$3
                   AND session_key=$4 AND minutes_before=$5""",
                telegram_id,
                season,
                round_num,
                session_key,
                minutes_before,
            )
        return result.split()[-1] != "0"

    async def get_user_notifications(
        self, telegram_id: int, season: int
    ) -> list[NotificationSubscription]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, telegram_id, season, round, session_key, minutes_before,
                          notified, fire_at, created_at
                   FROM notification_subscriptions
                   WHERE telegram_id=$1 AND season=$2 AND notified=FALSE
                   ORDER BY fire_at""",
                telegram_id,
                season,
            )
        return [
            NotificationSubscription(
                id=r["id"],
                telegram_id=r["telegram_id"],
                season=r["season"],
                round=r["round"],
                session_key=r["session_key"],
                minutes_before=r["minutes_before"],
                notified=r["notified"],
                fire_at=r["fire_at"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def get_pending_notifications(
        self,
        now: datetime,
    ) -> list[NotificationSubscription]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, telegram_id, season, round, session_key, minutes_before,
                          notified, fire_at, created_at
                   FROM notification_subscriptions
                   WHERE notified=FALSE AND fire_at <= $1
                   ORDER BY fire_at""",
                now,
            )
        return [
            NotificationSubscription(
                id=r["id"],
                telegram_id=r["telegram_id"],
                season=r["season"],
                round=r["round"],
                session_key=r["session_key"],
                minutes_before=r["minutes_before"],
                notified=r["notified"],
                fire_at=r["fire_at"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def mark_notifications_sent(self, ids: list[int]) -> None:
        # DELETE (not UPDATE SET notified=TRUE) to prevent row accumulation.
        # Changing this to UPDATE would break re-subscription unless
        # save_notification's ON CONFLICT is also DO UPDATE (not DO NOTHING).
        if not ids:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM notification_subscriptions WHERE id = ANY($1::int[])",
                ids,
            )

    async def has_notification(
        self, telegram_id: int, season: int, round_num: int, session_key: str, minutes_before: int
    ) -> bool:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT 1 FROM notification_subscriptions
                   WHERE telegram_id=$1 AND season=$2 AND round=$3
                   AND session_key=$4 AND minutes_before=$5 AND notified=FALSE""",
                telegram_id,
                season,
                round_num,
                session_key,
                minutes_before,
            )
        return row is not None

    async def delete_notifications_for_user(self, telegram_id: int) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM notification_subscriptions WHERE telegram_id=$1",
                telegram_id,
            )
        return int(result.split()[-1])

    async def get_next_fire_at(self) -> datetime | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MIN(fire_at) as next_fire FROM notification_subscriptions WHERE notified=FALSE"
            )
        return row["next_fire"] if row and row["next_fire"] is not None else None

    async def recompute_fire_times(
        self, season: int, round_num: int, session_times: dict[str, datetime]
    ) -> None:
        """Recompute fire_at for all non-notified subscriptions in a round based on updated session times."""
        from datetime import timedelta

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """SELECT id, session_key, minutes_before
                       FROM notification_subscriptions
                       WHERE season=$1 AND round=$2 AND notified=FALSE""",
                    season,
                    round_num,
                )
                for r in rows:
                    session_dt = session_times.get(r["session_key"])
                    if session_dt:
                        new_fire = session_dt - timedelta(minutes=r["minutes_before"])
                        await conn.execute(
                            "UPDATE notification_subscriptions SET fire_at=$1 WHERE id=$2",
                            new_fire,
                            r["id"],
                        )
