"""LINE webhook intake: verify the signature, ack immediately, process in background."""

import asyncio
import base64
import hashlib
import hmac
import json

import structlog
from aiohttp import web

from f1_bot.line.bridge import LineBridge

log = structlog.get_logger(__name__)

WEBHOOK_PATH = "/line/webhook"


def verify_signature(channel_secret: str, body: bytes, signature: str) -> bool:
    digest = hmac.new(channel_secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature)


def build_webhook_app(bridge: LineBridge, channel_secret: str) -> web.Application:
    # Handling an event means a DB read plus a reply call, which can outlast LINE's
    # webhook timeout; ack first and keep a reference so the task isn't collected.
    tasks: set[asyncio.Task] = set()

    async def process(events: list[dict]) -> None:
        for event in events:
            try:
                await bridge.handle_event(event)
            except Exception:
                log.exception("line_event_failed", event_type=event.get("type"))

    async def handle(request: web.Request) -> web.Response:
        body = await request.read()
        if not verify_signature(channel_secret, body, request.headers.get("X-Line-Signature", "")):
            log.warning("line_bad_signature")
            return web.Response(status=400)
        events = json.loads(body).get("events", [])
        task = asyncio.create_task(process(events))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return web.Response(text="OK")

    async def drain(_app: web.Application) -> None:
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.on_shutdown.append(drain)
    return app


async def start_webhook(bridge: LineBridge, channel_secret: str, host: str, port: int):
    runner = web.AppRunner(build_webhook_app(bridge, channel_secret))
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    log.info("line_webhook_listening", host=host, port=port, path=WEBHOOK_PATH)
    return runner
