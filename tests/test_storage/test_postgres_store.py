"""Tests for PostgresStore — schema init, CRUD, user preferences."""

import json

from f1_bot.models.user import UserPreference


async def test_init_creates_schema(pg_store):
    """After init(), all required tables must exist."""
    async with pg_store._pool.acquire() as conn:
        rows = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = {r["tablename"] for r in rows}
    expected = {
        "races",
        "standings_drivers",
        "standings_constructors",
        "results",
        "user_preferences",
    }
    assert expected.issubset(tables)


async def test_save_and_get_races(pg_store, sample_race_dict):
    await pg_store.save_races(2024, [sample_race_dict])
    rows = await pg_store.get_races(2024)
    assert len(rows) == 1
    assert rows[0]["name"] == "Monaco Grand Prix"
    assert rows[0]["round"] == 5


async def test_get_races_empty_season(pg_store):
    rows = await pg_store.get_races(1999)
    assert rows == []


async def test_save_and_get_driver_standings(pg_store):
    data = [{"position": 1, "driver": {"driver_id": "max_verstappen"}, "points": 100.0}]
    await pg_store.save_driver_standings(2024, 5, data)
    result = await pg_store.get_driver_standings(2024)
    assert result is not None
    assert result[0]["position"] == 1


async def test_get_driver_standings_returns_latest_round(pg_store):
    """With multiple rounds saved, the highest round_after is returned."""
    await pg_store.save_driver_standings(2024, 3, [{"pos": 3}])
    await pg_store.save_driver_standings(2024, 7, [{"pos": 7}])
    result = await pg_store.get_driver_standings(2024)
    assert result[0]["pos"] == 7


async def test_save_and_get_results(pg_store):
    data = [{"position": 1, "driver_id": "hamilton"}]
    await pg_store.save_results(2024, 5, "race", data)
    result = await pg_store.get_results(2024, 5, "race")
    assert result is not None
    assert result[0]["driver_id"] == "hamilton"


async def test_get_results_wrong_type_returns_none(pg_store):
    data = [{"position": 1}]
    await pg_store.save_results(2024, 5, "race", data)
    assert await pg_store.get_results(2024, 5, "qualifying") is None


async def test_upsert_and_get_user_preference(pg_store):
    pref = UserPreference(telegram_id=12345, timezone="Asia/Taipei")
    await pg_store.upsert_user_preference(pref)
    result = await pg_store.get_user_preference(12345)
    assert result is not None
    assert result.timezone == "Asia/Taipei"


async def test_upsert_user_preference_updates_timezone(pg_store):
    """Second upsert changes timezone without creating a duplicate row."""
    pref1 = UserPreference(telegram_id=999, timezone="UTC")
    pref2 = UserPreference(telegram_id=999, timezone="Europe/London")
    await pg_store.upsert_user_preference(pref1)
    await pg_store.upsert_user_preference(pref2)
    result = await pg_store.get_user_preference(999)
    assert result.timezone == "Europe/London"


async def test_get_user_preference_missing_returns_none(pg_store):
    assert await pg_store.get_user_preference(0) is None


async def test_migration_clears_old_session_keys(pg_store):
    """It deletes rows matching 'session:%' without secondary colons, but keeps two-colon types."""
    await pg_store.save_results(2026, 2, "session:11235", [])
    await pg_store.save_results(2026, 2, "session:fp1:11235", [])
    await pg_store.save_results(2026, 2, "race", [])

    # Re-run init to trigger migration
    await pg_store.init()

    rows = await pg_store.get_all_result_types(2026, 2)
    assert "session:fp1:11235" in rows
    assert "race" in rows
    assert "session:11235" not in rows


async def test_save_races_transaction_rollback(pg_store, sample_race_dict):
    """Ensure save_races rolls back the DELETE operation if writing new races fails."""
    # 1. Save valid race
    await pg_store.save_races(2024, [sample_race_dict])
    rows = await pg_store.get_races(2024)
    assert len(rows) == 1

    # 2. Try to save invalid race that triggers KeyError (missing "round" key)
    invalid_race = sample_race_dict.copy()
    del invalid_race["round"]

    import pytest

    with pytest.raises(KeyError):
        await pg_store.save_races(2024, [invalid_race])

    # 3. Verify that the DELETE operation was rolled back and previous race remains
    rows_after = await pg_store.get_races(2024)
    assert len(rows_after) == 1
    assert rows_after[0]["name"] == "Monaco Grand Prix"


async def test_save_and_get_drivers(pg_store):
    """Verify save_drivers inserts successfully."""
    drivers = [
        {"driver_id": "verstappen", "name": "Max Verstappen"},
        {"driver_id": "hamilton", "name": "Lewis Hamilton"},
    ]
    await pg_store.save_drivers(drivers)
    rows = await pg_store.get_drivers()
    assert len(rows) == 2
    ids = {d["driver_id"] for d in rows}
    assert ids == {"verstappen", "hamilton"}


async def test_save_circuits(pg_store):
    """Verify save_circuits inserts successfully."""
    circuits = [
        {"circuit_id": "monza", "name": "Monza"},
        {"circuit_id": "spa", "name": "Spa"},
    ]
    await pg_store.save_circuits(circuits)
    async with pg_store._pool.acquire() as conn:
        rows = await conn.fetch("SELECT data_json FROM circuits")
    assert len(rows) == 2
    ids = {json.loads(r["data_json"])["circuit_id"] for r in rows}
    assert ids == {"monza", "spa"}
