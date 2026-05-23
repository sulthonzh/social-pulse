from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Protocol

import structlog

from src.shared.token_budget import TokenBudget, estimate_tokens

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


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.z.ai/api/coding/paas/v4",
        model: str = "glm-4.7",
        client: AsyncOpenAI | None = None,
        token_budget: TokenBudget | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client: AsyncOpenAI | None = client
        self._token_budget = token_budget

    @property
    def model_name(self) -> str:
        return self._model

    def _ensure_client(self) -> AsyncOpenAI:
        if self._client is None:
            from openai import AsyncOpenAI

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
        combined = system_prompt + user_prompt
        estimated = estimate_tokens(combined)

        if self._token_budget is not None and not self._token_budget.check_budget(estimated):
            logger.warning(
                "openai_token_budget_exceeded",
                estimated_tokens=estimated,
            )
            return {}

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
            "openai_chat_json",
            model=self._model,
            prompt_len=len(user_prompt),
            response_len=len(content) if content else 0,
        )
        if not content:
            return {}

        if self._token_budget is not None:
            self._token_budget.record_usage(estimated)

        result: dict[str, Any] = json.loads(content)
        return result
