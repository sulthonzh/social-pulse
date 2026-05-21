from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Protocol

import structlog

if TYPE_CHECKING:
    from openai import AsyncOpenAI

logger = structlog.get_logger()


class _AsyncOpenAIClient(Protocol):
    async def chat_completions_create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0,
    ) -> Any: ...


class ZAIClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.z.ai/api/coding/paas/v4",
        model: str = "glm-4.7",
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client: AsyncOpenAI | None = client

    def _ensure_client(self) -> AsyncOpenAI:
        if self._client is None:
            from openai import AsyncOpenAI  # noqa: PLC0415

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    async def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        client = self._ensure_client()
        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = response.choices[0].message.content
        logger.debug(
            "zai_chat_json",
            model=self._model,
            prompt_len=len(user_prompt),
            response_len=len(content) if content else 0,
        )
        if not content:
            return {}
        return json.loads(content)
