"""Unit tests for the bot startup and command registration."""

from unittest.mock import AsyncMock, MagicMock, patch

from f1_bot.main import _post_init


async def test_post_init_sets_commands():
    """Verify that _post_init initializes DB, runs startup sync, and registers bot commands."""
    app = MagicMock()
    app.bot_data = {
        "settings": MagicMock(),
        "store": AsyncMock(),
        "jolpica": AsyncMock(),
        "openf1": AsyncMock(),
        "repo": AsyncMock(),
    }
    app.bot = AsyncMock()
    app.job_queue = MagicMock()

    with (
        patch("f1_bot.main.startup_sync", new_callable=AsyncMock) as mock_sync,
        patch(
            "f1_bot.scheduler.notification_sender.schedule_next_notification",
            new_callable=AsyncMock,
        ),
    ):
        await _post_init(app)
        mock_sync.assert_awaited_once()

    # Verify DB initialization is called
    app.bot_data["store"].init.assert_awaited_once()

    # Post-005 the menu is registered once as the default plus once per shipped
    # language: SHIPPED_LANGS == ("en", "zh-Hant"), so 1 + 2 == 3 awaits.
    from f1_bot.formatting.i18n import SHIPPED_LANGS

    assert app.bot.set_my_commands.await_count == 1 + len(SHIPPED_LANGS)

    calls = app.bot.set_my_commands.call_args_list

    # First call is the default menu (no language_code).
    default_args, default_kwargs = calls[0]
    default_menu = default_args[0]
    assert "language_code" not in default_kwargs

    # Every registered menu must carry all 9 visible commands. Telegram silently
    # *ignores* a set_my_commands list whose length mismatches, so a wrong count
    # would not fail loudly on its own — assert it here.
    assert len(default_menu) == 9

    cmd_names = {c.command for c in default_menu}
    expected_commands = {
        "start",
        "next",
        "schedule",
        "results",
        "standings",
        "driver",
        "circuit",
        "remind",
        "settings",
    }
    assert cmd_names == expected_commands

    # Collect the per-language registrations by their language_code kwarg.
    by_lang = {
        kwargs["language_code"]: args[0] for args, kwargs in calls if "language_code" in kwargs
    }
    assert set(by_lang) == {lang.split("-")[0] for lang in SHIPPED_LANGS}

    # The zh-Hant menu must be registered and localized: same 9 commands, but the
    # descriptions differ from the English default — proving translations were applied
    # and not silently falling back to English.
    # Telegram receives "zh" (ISO 639-1) even though catalog key is "zh-Hant".
    zh_menu = by_lang["zh"]
    assert len(zh_menu) == 9
    assert {c.command for c in zh_menu} == expected_commands
    default_descs = {c.command: c.description for c in default_menu}
    zh_descs = {c.command: c.description for c in zh_menu}
    assert zh_descs != default_descs


async def test_post_shutdown_closes_resources():
    """Verify that _post_shutdown closes PostgresStore, JolpicaClient, and OpenF1Client."""
    from f1_bot.main import _post_shutdown

    app = MagicMock()
    app.bot_data = {
        "store": AsyncMock(),
        "jolpica": AsyncMock(),
        "openf1": AsyncMock(),
    }
    await _post_shutdown(app)
    app.bot_data["jolpica"].close.assert_awaited_once()
    app.bot_data["openf1"].close.assert_awaited_once()
    app.bot_data["store"].close.assert_awaited_once()
