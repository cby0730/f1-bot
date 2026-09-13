"""The registered command/callback surface is exactly the public 9 + live patterns.

This is the one test that cannot be bypassed by deleting a unit test for a hidden
alias: it inspects ``register_all_handlers()`` on a real PTB Application.
"""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from f1_bot.formatting.i18n import COMMAND_ORDER
from f1_bot.handlers import register_all_handlers

_HIDDEN_COMMANDS = frozenset(
    {"countdown", "title", "compare", "pitstops", "laps", "timezone", "language", "help"}
)

_FORBIDDEN_PATTERN_FRAGMENTS = (
    "title:",
    "lang:picker",
    "cmp:list",
    "nsess:",
    "nprac:",
    "nqual:",
    "nspr:",
    "qual:",
    "spr:",
    "sr:",
)

_EXPECTED_PATTERNS = frozenset(
    {
        "^start:",
        "^next:",
        "^standings:",
        "^res:",
        "^pit:",
        "^lap:",
        "^rpk:",
        "^(drv|circ):",
        "^cmp:",
        "^set:",
        "^tz:",
        "^lang:",
        "^notify:pick:",
        "^notify:sess:",
        "^notify:set:",
        "^notify:list:",
        "^notify:del:",
        "^notify:back",
        "^notify:clearall:",
    }
)


def _pattern_str(handler) -> str:
    pattern = handler.pattern
    if pattern is None:
        return ""
    return pattern.pattern if hasattr(pattern, "pattern") else str(pattern)


def _registered_app() -> Application:
    app = Application.builder().token("123456:ABC-DEF").build()
    register_all_handlers(app)
    return app


def _all_handlers(app: Application) -> list:
    handlers = []
    for group_handlers in app.handlers.values():
        handlers.extend(group_handlers)
    return handlers


def test_command_handlers_are_exactly_the_nine_visible_commands():
    app = _registered_app()
    commands: set[str] = set()
    for handler in _all_handlers(app):
        if isinstance(handler, CommandHandler):
            commands |= set(handler.commands)
    assert commands == set(COMMAND_ORDER)
    assert commands.isdisjoint(_HIDDEN_COMMANDS)


def test_callback_patterns_match_the_live_set_and_exclude_deleted_ones():
    app = _registered_app()
    patterns = [
        _pattern_str(handler)
        for handler in _all_handlers(app)
        if isinstance(handler, CallbackQueryHandler)
    ]
    assert frozenset(patterns) == _EXPECTED_PATTERNS
    joined = " ".join(patterns)
    for fragment in _FORBIDDEN_PATTERN_FRAGMENTS:
        assert fragment not in joined, f"deleted callback {fragment!r} is still registered"
