import os  # noqa: I001

os.environ["PTB_TIMEDELTA"] = "1"

import structlog
from telegram.ext import Application
from telegram.request import HTTPXRequest

from f1_bot.api.jolpica import JolpicaClient
from f1_bot.api.openf1 import OpenF1Client
from f1_bot.config import Settings
from f1_bot.handlers import register_all_handlers
from f1_bot.line.client import LineClient
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

        from f1_bot.formatting.i18n import COMMAND_ORDER, DEFAULT_LANG, SHIPPED_LANGS, t

        def _menu(lang: str) -> list[BotCommand]:
            return [BotCommand(name, t(f"commands.{name}", lang)) for name in COMMAND_ORDER]

        # Default menu (clients whose locale we ship no translation for) plus one
        # explicit registration per shipped language.
        await app.bot.set_my_commands(_menu(DEFAULT_LANG))
        for lang in SHIPPED_LANGS:
            await app.bot.set_my_commands(_menu(lang), language_code=lang.split("-")[0])
        log.info("bot_commands_registered", languages=list(SHIPPED_LANGS))
    except Exception as e:
        log.warning("failed_to_set_bot_commands", error=str(e))

    if line := app.bot_data.get("line"):
        from f1_bot.line.bridge import LineBridge
        from f1_bot.line.webhook import start_webhook

        app.bot_data["line_runner"] = await start_webhook(
            LineBridge(app, line),
            settings.line_channel_secret,
            settings.line_webhook_host,
            settings.line_webhook_port,
        )


async def _post_stop(app: Application) -> None:
    # Stop LINE intake while the app is still initialized and the DB pool open, so
    # in-flight events can finish.
    if runner := app.bot_data.get("line_runner"):
        await runner.cleanup()


async def _post_shutdown(app: Application) -> None:
    if line := app.bot_data.get("line"):
        await line.close()
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
        .post_stop(_post_stop)
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
    if settings.line_enabled:
        app.bot_data["line"] = LineClient(
            settings.line_channel_access_token, proxy=settings.telegram_proxy
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
