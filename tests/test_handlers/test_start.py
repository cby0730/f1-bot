from f1_bot.handlers import start


def test_help_text_lists_registered_commands_from_start_module():
    registered = set()
    app = type("App", (), {"add_handler": lambda self, h: registered.update(h.commands)})()

    start.register(app)

    for command in registered:
        assert f"/{command}" in start._HELP_TEXT


def test_help_text_lists_all_public_registered_commands():
    commands = {
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

    for command in commands:
        assert f"/{command}" in start._HELP_TEXT
