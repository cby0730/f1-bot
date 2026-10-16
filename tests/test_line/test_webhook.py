"""Webhook intake: signature gate, immediate ack, per-event isolation."""

import asyncio
import base64
import hashlib
import hmac
import json

from aiohttp.test_utils import TestClient, TestServer

from f1_bot.line.webhook import WEBHOOK_PATH, build_webhook_app, verify_signature

SECRET = "test-secret"


def _sign(body: bytes) -> str:
    return base64.b64encode(hmac.new(SECRET.encode(), body, hashlib.sha256).digest()).decode()


class _FakeBridge:
    def __init__(self, fail_on: str | None = None) -> None:
        self.seen: list[str] = []
        self.done = asyncio.Event()
        self._fail_on = fail_on

    async def handle_event(self, event: dict) -> None:
        self.seen.append(event["type"])
        if event["type"] == self._fail_on:
            raise RuntimeError("boom")
        if event["type"] == "last":
            self.done.set()


async def _post(bridge, body: bytes, signature: str):
    async with TestClient(TestServer(build_webhook_app(bridge, SECRET))) as client:
        resp = await client.post(WEBHOOK_PATH, data=body, headers={"X-Line-Signature": signature})
        if resp.status == 200:
            await asyncio.wait_for(bridge.done.wait(), timeout=2)
        return resp.status


def test_verify_signature():
    body = b'{"events":[]}'
    assert verify_signature(SECRET, body, _sign(body))
    assert not verify_signature(SECRET, body, _sign(b"tampered"))
    assert not verify_signature(SECRET, body, "")


async def test_bad_signature_rejected_and_nothing_processed():
    bridge = _FakeBridge()
    body = json.dumps({"events": [{"type": "last"}]}).encode()
    assert await _post(bridge, body, _sign(b"other")) == 400
    assert bridge.seen == []


async def test_valid_signature_processes_events_in_order_despite_failures():
    bridge = _FakeBridge(fail_on="message")
    body = json.dumps({"events": [{"type": "message"}, {"type": "last"}]}).encode()
    assert await _post(bridge, body, _sign(body)) == 200
    assert bridge.seen == ["message", "last"]


async def test_verify_button_payload_with_no_events_is_acked():
    """The console's "Verify" sends an empty event list and expects 200."""
    bridge = _FakeBridge()
    bridge.done.set()
    body = b'{"destination":"U0","events":[]}'
    assert await _post(bridge, body, _sign(body)) == 200
    assert bridge.seen == []
