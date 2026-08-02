from f1_bot.formatting.i18n import t
from f1_bot.handlers import start

# The command list is no longer a module constant; it lives in the i18n catalog and
# is rendered per-language. Assert against the English rendering — the same text the
# /help handler emits for a default-language user.
_HELP_TEXT = t("start.help", "en")


def test_help_text_lists_registered_commands_from_start_module():
    registered = set()
    app = type("App", (), {"add_handler": lambda self, h: registered.update(h.commands)})()

    start.register(app)

    for command in registered:
        assert f"/{command}" in _HELP_TEXT


def test_help_text_lists_all_public_registered_commands():
    commands = {
        "start",
        "help",
        "next",
        "schedule",
        "countdown",
        "timezone",
        "language",
        "standings",
        "title",
        "results",
        "pitstops",
        "laps",
        "driver",
        "circuit",
    }

    for command in commands:
        assert f"/{command}" in _HELP_TEXT
