from telegram.ext import Application

from f1_bot.handlers import (
    errors,
    extras,
    notifications,
    race_data,
    results,
    round_picker,
    schedule,
    standings,
    start,
    timezone,
)


def register_all_handlers(app: Application) -> None:
    start.register(app)
    schedule.register(app)
    standings.register(app)
    results.register(app)
    race_data.register(app)
    round_picker.register(app)
    extras.register(app)
    timezone.register(app)
    notifications.register(app)
    app.add_error_handler(errors.error_handler)
