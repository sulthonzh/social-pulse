from __future__ import annotations

import pytest
from src.shared.prompts import PromptEntry, PromptRegistry


class TestPromptRegistryGetPrompt:
    def setup_method(self) -> None:
        PromptRegistry._reset()

    def test_get_sentiment_prompt(self) -> None:
        prompt = PromptRegistry.get_prompt("sentiment")
        assert "sentiment classifier" in prompt
        assert "positive" in prompt

    def test_get_topic_prompt(self) -> None:
        prompt = PromptRegistry.get_prompt("topic")
        assert "topic extractor" in prompt
        assert "topic_label" in prompt

    def test_get_language_prompt(self) -> None:
        prompt = PromptRegistry.get_prompt("language")
        assert "language detector" in prompt
        assert "language_code" in prompt

    def test_get_unknown_key_raises(self) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            PromptRegistry.get_prompt("nonexistent")


class TestPromptRegistryGetVersion:
    def setup_method(self) -> None:
        PromptRegistry._reset()

    def test_sentiment_version_is_v1(self) -> None:
        assert PromptRegistry.get_prompt_version("sentiment") == "v1"

    def test_topic_version_is_v1(self) -> None:
        assert PromptRegistry.get_prompt_version("topic") == "v1"

    def test_language_version_is_v1(self) -> None:
        assert PromptRegistry.get_prompt_version("language") == "v1"

    def test_unknown_key_raises(self) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            PromptRegistry.get_prompt_version("nonexistent")


class TestPromptRegistryRegister:
    def setup_method(self) -> None:
        PromptRegistry._reset()

    def test_register_new_prompt(self) -> None:
        entry = PromptEntry(
            key="custom",
            version="v2",
            system_prompt="Custom prompt",
        )
        PromptRegistry.register(entry)
        assert PromptRegistry.get_prompt("custom") == "Custom prompt"
        assert PromptRegistry.get_prompt_version("custom") == "v2"

    def test_register_overwrites_existing(self) -> None:
        entry = PromptEntry(
            key="sentiment",
            version="v2",
            system_prompt="Updated sentiment prompt",
        )
        PromptRegistry.register(entry)
        assert PromptRegistry.get_prompt("sentiment") == "Updated sentiment prompt"
        assert PromptRegistry.get_prompt_version("sentiment") == "v2"


class TestPromptRegistryReset:
    def test_reset_then_get_reloads_defaults(self) -> None:
        entry = PromptEntry(
            key="sentiment",
            version="v99",
            system_prompt="Overridden",
        )
        PromptRegistry.register(entry)
        assert PromptRegistry.get_prompt("sentiment") == "Overridden"

        PromptRegistry._reset()
        prompt = PromptRegistry.get_prompt("sentiment")
        assert "sentiment classifier" in prompt
        assert PromptRegistry.get_prompt_version("sentiment") == "v1"
