from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from src.infrastructure.ai.openai_client import OpenAIClient


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeAsyncOpenAI:
    def __init__(self, response_content: str = '{"key": "value"}') -> None:
        self._response_content = response_content

    class _Chat:
        def __init__(self, response_content: str) -> None:
            self._response_content = response_content
            self.completions = _FakeAsyncOpenAI._Completions(response_content)

    class _Completions:
        def __init__(self, response_content: str) -> None:
            self._response_content = response_content

        async def create(self, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse(self._response_content)

    @property
    def chat(self) -> _FakeAsyncOpenAI._Chat:  # type: ignore[override]
        return self._Chat(self._response_content)


@pytest.mark.unit
class TestOpenAIClient:
    def test_chat_json_parses_response(self):
        payload = {"label": "positive", "confidence": 0.95}
        fake_client = _FakeAsyncOpenAI(json.dumps(payload))
        client = OpenAIClient(
            api_key="test-key",
            base_url="https://fake.api/v4",
            model="glm-4.5-flash",
            client=fake_client,  # type: ignore[arg-type]
        )
        result = _run(client.chat_json(system_prompt="sys", user_prompt="hello"))
        assert result == payload

    def test_chat_json_empty_content_returns_empty(self):
        fake_client = _FakeAsyncOpenAI("")
        client = OpenAIClient(
            api_key="test-key",
            base_url="https://fake.api/v4",
            model="glm-4.5-flash",
            client=fake_client,  # type: ignore[arg-type]
        )
        result = _run(client.chat_json(system_prompt="sys", user_prompt="hello"))
        assert result == {}

    def test_lazy_client_init(self):
        client = OpenAIClient(api_key="test-key")
        assert client._client is None

    def test_model_accessible(self):
        client = OpenAIClient(api_key="test-key", model="glm-4")
        assert client._model == "glm-4"
