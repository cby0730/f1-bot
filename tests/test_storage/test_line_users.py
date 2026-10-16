"""line_users: LINE user id ↔ negative internal id."""


async def test_new_user_gets_negative_id_and_lookup_round_trips(repo):
    user_id, created = await repo.get_or_create_line_user("U1")
    assert created
    assert user_id == -1
    assert await repo.get_line_user_id(user_id) == "U1"


async def test_repeat_contact_returns_same_id_without_burning_identity(repo):
    first, _ = await repo.get_or_create_line_user("U1")
    for _ in range(3):
        again, created = await repo.get_or_create_line_user("U1")
        assert (again, created) == (first, False)
    second, created = await repo.get_or_create_line_user("U2")
    assert created
    assert second == first - 1


async def test_unknown_internal_id_has_no_line_user(repo):
    assert await repo.get_line_user_id(-99) is None


async def test_line_id_shares_preferences_table_with_telegram_ids(repo):
    line_id, _ = await repo.get_or_create_line_user("U1")
    await repo.set_user_language(line_id, "zh-Hant")
    await repo.set_user_language(1, "en")
    assert await repo.get_user_language(line_id) == "zh-Hant"
    assert await repo.get_user_language(1) == "en"
