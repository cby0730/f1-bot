from f1_bot.formatting.i18n import COMMAND_ORDER, t
from f1_bot.handlers import start

_HELP_TEXT = t("start.help", "en")
_WELCOME_INTRO = t("start.welcome_intro", "en")


def test_help_text_lists_visible_menu_commands():
    """Welcome lists COMMAND_ORDER names, not unregistered commands like /help."""
    for command in COMMAND_ORDER:
        assert f"/{command}" in _HELP_TEXT


def test_help_text_does_not_list_hidden_aliases():
    hidden = ("help", "countdown", "title", "timezone", "language", "compare", "pitstops", "laps")
    for command in hidden:
        assert f"/{command}" not in _HELP_TEXT


def test_welcome_intro_points_at_settings():
    assert "/settings" in _WELCOME_INTRO
    assert "/timezone" not in _WELCOME_INTRO


def test_start_register_does_not_install_help():
    """/help is not a command — typing it must not produce a welcome message."""
    registered = set()
    app = type("App", (), {"add_handler": lambda self, h: registered.update(h.commands)})()
    start.register(app)
    assert registered == {"start"}
