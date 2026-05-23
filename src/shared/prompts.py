from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class PromptEntry:
    key: str
    version: str
    system_prompt: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


_DEFAULT_PROMPTS: dict[str, PromptEntry] = {
    "sentiment": PromptEntry(
        key="sentiment",
        version="v1",
        system_prompt=(
            "You are a sentiment classifier. "
            'Classify the sentiment of the user text as one of: "positive", "negative", "neutral". '
            "Respond with a JSON object with exactly two keys: "
            '"label" (one of "positive", "negative", "neutral") '
            'and "confidence" (a float between 0.0 and 1.0).'
        ),
    ),
    "topic": PromptEntry(
        key="topic",
        version="v1",
        system_prompt=(
            "You are a topic extractor. "
            "Given the user text, extract the primary topic as a short label (1-4 words) "
            "and a confidence score between 0.0 and 1.0. "
            "Respond with a JSON object with exactly two keys: "
            '"topic_label" (string) and "confidence" (float).'
        ),
    ),
    "language": PromptEntry(
        key="language",
        version="v1",
        system_prompt=(
            "You are a language detector. "
            "Given the user text, detect the language and respond with a JSON object "
            "with exactly two keys: "
            '"language_code" (ISO 639-1 two-letter code, e.g. "en", "id", "fr") '
            'and "confidence" (float between 0.0 and 1.0).'
        ),
    ),
}


class PromptRegistry:
    _prompts: dict[str, PromptEntry]

    @classmethod
    def _ensure_loaded(cls) -> None:
        if not hasattr(cls, "_prompts") or not cls._prompts:
            cls._prompts = dict(_DEFAULT_PROMPTS)

    @classmethod
    def get_prompt(cls, key: str) -> str:
        cls._ensure_loaded()
        entry = cls._prompts.get(key)
        if entry is None:
            raise KeyError(f"No prompt registered for key: {key}")
        return entry.system_prompt

    @classmethod
    def get_prompt_version(cls, key: str) -> str:
        cls._ensure_loaded()
        entry = cls._prompts.get(key)
        if entry is None:
            raise KeyError(f"No prompt registered for key: {key}")
        return entry.version

    @classmethod
    def register(cls, entry: PromptEntry) -> None:
        cls._ensure_loaded()
        cls._prompts[entry.key] = entry

    @classmethod
    def _reset(cls) -> None:
        if hasattr(cls, "_prompts"):
            cls._prompts = {}
