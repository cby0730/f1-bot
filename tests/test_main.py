"""Unit tests for the bot startup and command registration."""

from unittest.mock import AsyncMock, MagicMock, patch

from f1_bot.main import _post_init


async def test_post_init_sets_commands():
    """Verify that _post_init initializes DB, runs startup sync, and registers bot commands."""
    app = MagicMock()
    app.bot_data = {
        "settings": MagicMock(),
        "sqlite": AsyncMock(),
        "jolpica": AsyncMock(),
        "openf1": AsyncMock(),
        "repo": AsyncMock(),
    }
    app.bot = AsyncMock()

    with patch("f1_bot.main.startup_sync", new_callable=AsyncMock) as mock_sync:
        await _post_init(app)
        mock_sync.assert_awaited_once()

    # Verify SQLite DB initialization is called
    app.bot_data["sqlite"].init.assert_awaited_once()

    # Verify set_my_commands is called to register autocomplete commands
    app.bot.set_my_commands.assert_awaited_once()

    # Retrieve and verify the list of registered commands
    args, _ = app.bot.set_my_commands.call_args
    commands = args[0]

    assert len(commands) == 12

    # Assert specific commands exist in the list
    cmd_names = {c.command for c in commands}
    expected_commands = {
        "start",
        "help",
        "next",
        "schedule",
        "countdown",
        "timezone",
        "standings",
        "results",
        "pitstops",
        "laps",
        "driver",
        "circuit",
    }
    assert cmd_names == expected_commands
