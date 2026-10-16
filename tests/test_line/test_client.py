"""LineClient request shapes and error surfacing."""

import json

import pytest

from f1_bot.line.client import LineAPIError, LineClient


async def test_reply_posts_token_and_messages_with_bearer_auth(httpx_mock):
    httpx_mock.add_response(url="https://api.line.me/v2/bot/message/reply", json={})
    client = LineClient("tok")
    await client.reply("rt", [{"type": "text", "text": "hi"}])
    await client.close()

    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer tok"
    assert json.loads(request.content) == {
        "replyToken": "rt",
        "messages": [{"type": "text", "text": "hi"}],
    }


async def test_push_posts_recipient(httpx_mock):
    httpx_mock.add_response(url="https://api.line.me/v2/bot/message/push", json={})
    client = LineClient("tok")
    await client.push("U123", [{"type": "text", "text": "hi"}])
    await client.close()

    assert json.loads(httpx_mock.get_request().content)["to"] == "U123"


async def test_error_response_raises_with_body(httpx_mock):
    httpx_mock.add_response(status_code=400, json={"message": "Invalid reply token"})
    client = LineClient("tok")
    with pytest.raises(LineAPIError) as exc:
        await client.reply("bad", [{"type": "text", "text": "hi"}])
    await client.close()

    assert exc.value.status_code == 400
    assert "Invalid reply token" in exc.value.body
