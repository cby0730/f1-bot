import structlog
from telegram.ext import Application
from telegram.request import HTTPXRequest

from f1_bot.api.jolpica import JolpicaClient
from f1_bot.api.openf1 import OpenF1Client
from f1_bot.config import Settings
from f1_bot.handlers import register_all_handlers
from f1_bot.scheduler.jobs import startup_sync
from f1_bot.scheduler.manager import register_jobs
from f1_bot.storage.postgres_store import PostgresStore
from f1_bot.storage.repository import Repository
from f1_bot.utils.logging import setup_logging
from f1_bot.utils.rate_limiter import RateLimiter

log = structlog.get_logger(__name__)


async def _post_init(app: Application) -> None:
    settings: Settings = app.bot_data["settings"]
    store: PostgresStore = app.bot_data["store"]
    await store.init()

    log.info("startup", database_url=settings.database_url.split("@")[-1])

    # Full-season sync before accepting Telegram updates
    jolpica = app.bot_data["jolpica"]
    openf1 = app.bot_data["openf1"]
    repo = app.bot_data["repo"]
    await startup_sync(jolpica, openf1, repo)

    # Restore notification schedule from DB
    from f1_bot.scheduler.notification_sender import schedule_next_notification

    await schedule_next_notification(app.job_queue, repo)

    try:
        from telegram import BotCommand

        commands = [
            BotCommand("start", "Welcome message and command overview"),
            BotCommand("help", "Show command list"),
            BotCommand("next", "Next race — session filter buttons"),
            BotCommand("schedule", "Full season race calendar"),
            BotCommand("countdown", "Time remaining until the next race"),
            BotCommand("timezone", "Set your timezone"),
            BotCommand("standings", "WDC + WCC standings"),
            BotCommand("results", "Results — session filter + round navigation"),
            BotCommand("pitstops", "Pit stop data with round navigation"),
            BotCommand("laps", "Lap times with sector data"),
            BotCommand("driver", "Driver profile"),
            BotCommand("circuit", "Circuit info"),
            BotCommand("remind", "Manage notification reminders"),
        ]
        await app.bot.set_my_commands(commands)
        log.info("bot_commands_registered")
    except Exception as e:
        log.warning("failed_to_set_bot_commands", error=str(e))


async def _post_shutdown(app: Application) -> None:
    await app.bot_data["jolpica"].close()
    await app.bot_data["openf1"].close()
    await app.bot_data["store"].close()
    log.info("shutdown_complete")


def build_app(settings: Settings) -> Application:
    store = PostgresStore(settings.database_url)
    repo = Repository(store)

    jolpica_limiter = RateLimiter(
        per_second=settings.jolpica_rate_per_second,
        per_period=settings.jolpica_rate_per_hour,
        period=3600,
    )
    openf1_limiter = RateLimiter(
        per_second=settings.openf1_rate_per_second,
        per_period=settings.openf1_rate_per_minute,
        period=60,
    )
    jolpica = JolpicaClient(
        settings.jolpica_base_url, jolpica_limiter, proxy=settings.telegram_proxy
    )
    openf1 = OpenF1Client(settings.openf1_base_url, openf1_limiter, proxy=settings.telegram_proxy)
    notification_limiter = RateLimiter(per_second=settings.notification_rate_per_second)

    request_kwargs = {
        "connect_timeout": settings.telegram_connect_timeout,
        "read_timeout": settings.telegram_read_timeout,
    }
    if settings.telegram_proxy:
        request_kwargs["proxy"] = settings.telegram_proxy

    request = HTTPXRequest(**request_kwargs)
    get_updates_request = HTTPXRequest(**request_kwargs)

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .request(request)
        .get_updates_request(get_updates_request)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    app.bot_data.update(
        {
            "settings": settings,
            "store": store,
            "repo": repo,
            "jolpica": jolpica,
            "openf1": openf1,
            "notification_limiter": notification_limiter,
        }
    )

    register_all_handlers(app)
    register_jobs(app)
    return app


def main() -> None:
    settings = Settings()
    setup_logging(settings.log_level, settings.log_format)
    log.info("f1_bot_starting", log_level=settings.log_level, log_format=settings.log_format)

    app = build_app(settings)
    app.run_polling(drop_pending_updates=True)
