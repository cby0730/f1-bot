"""Minimal LINE Messaging API client — only the two calls the bot makes."""

import httpx


class LineAPIError(Exception):
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"LINE API {status_code}: {body}")


class LineClient:
    def __init__(
        self,
        access_token: str,
        base_url: str = "https://api.line.me",
        proxy: str | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {access_token}"},
            proxy=proxy,
            timeout=10.0,
        )

    async def reply(self, reply_token: str, messages: list[dict]) -> None:
        await self._post("/v2/bot/message/reply", {"replyToken": reply_token, "messages": messages})

    async def push(self, to: str, messages: list[dict]) -> None:
        await self._post("/v2/bot/message/push", {"to": to, "messages": messages})

    async def _post(self, path: str, payload: dict) -> None:
        response = await self._client.post(path, json=payload)
        if response.is_error:
            raise LineAPIError(response.status_code, response.text)

    async def close(self) -> None:
        await self._client.aclose()
