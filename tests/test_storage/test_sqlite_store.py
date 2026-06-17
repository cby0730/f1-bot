"""Tests for SQLiteStore — schema init, CRUD, user preferences."""

from f1_bot.models.user import UserPreference


async def test_init_creates_schema(sqlite_store):
    """After init(), all required tables must exist."""
    async with sqlite_store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) as cur:
        tables = {row["name"] async for row in cur}
    expected = {
        "races",
        "standings_drivers",
        "standings_constructors",
        "results",
        "user_preferences",
    }
    assert expected.issubset(tables)


async def test_save_and_get_races(sqlite_store, sample_race_dict):
    await sqlite_store.save_races(2024, [sample_race_dict])
    rows = await sqlite_store.get_races(2024)
    assert len(rows) == 1
    assert rows[0]["name"] == "Monaco Grand Prix"
    assert rows[0]["round"] == 5


async def test_get_races_empty_season(sqlite_store):
    rows = await sqlite_store.get_races(1999)
    assert rows == []


async def test_save_and_get_driver_standings(sqlite_store):
    data = [{"position": 1, "driver": {"driver_id": "max_verstappen"}, "points": 100.0}]
    await sqlite_store.save_driver_standings(2024, 5, data)
    result = await sqlite_store.get_driver_standings(2024)
    assert result is not None
    assert result[0]["position"] == 1


async def test_get_driver_standings_returns_latest_round(sqlite_store):
    """With multiple rounds saved, the highest round_after is returned."""
    await sqlite_store.save_driver_standings(2024, 3, [{"pos": 3}])
    await sqlite_store.save_driver_standings(2024, 7, [{"pos": 7}])
    result = await sqlite_store.get_driver_standings(2024)
    assert result[0]["pos"] == 7


async def test_save_and_get_results(sqlite_store):
    data = [{"position": 1, "driver_id": "hamilton"}]
    await sqlite_store.save_results(2024, 5, "race", data)
    result = await sqlite_store.get_results(2024, 5, "race")
    assert result is not None
    assert result[0]["driver_id"] == "hamilton"


async def test_get_results_wrong_type_returns_none(sqlite_store):
    data = [{"position": 1}]
    await sqlite_store.save_results(2024, 5, "race", data)
    assert await sqlite_store.get_results(2024, 5, "qualifying") is None


async def test_upsert_and_get_user_preference(sqlite_store):
    pref = UserPreference(telegram_id=12345, timezone="Asia/Taipei")
    await sqlite_store.upsert_user_preference(pref)
    result = await sqlite_store.get_user_preference(12345)
    assert result is not None
    assert result.timezone == "Asia/Taipei"


async def test_upsert_user_preference_updates_timezone(sqlite_store):
    """Second upsert changes timezone without creating a duplicate row."""
    pref1 = UserPreference(telegram_id=999, timezone="UTC")
    pref2 = UserPreference(telegram_id=999, timezone="Europe/London")
    await sqlite_store.upsert_user_preference(pref1)
    await sqlite_store.upsert_user_preference(pref2)
    result = await sqlite_store.get_user_preference(999)
    assert result.timezone == "Europe/London"


async def test_get_user_preference_missing_returns_none(sqlite_store):
    assert await sqlite_store.get_user_preference(0) is None
