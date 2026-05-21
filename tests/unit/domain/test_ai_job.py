from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.ai_job import AIJob
from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType


@pytest.mark.unit
class TestAIJobDefaults:
    def _make_job(self, **overrides: Any) -> AIJob:
        defaults: dict[str, Any] = {
            "silver_post_id": uuid4(),
            "job_type": AIJobType.SENTIMENT,
        }
        defaults.update(overrides)
        return AIJob(**defaults)

    def test_id_auto_generated(self) -> None:
        job = self._make_job()
        assert job.id is not None
        assert isinstance(job.id, UUID)
        UUID(str(job.id))

    def test_status_defaults_to_pending(self) -> None:
        job = self._make_job()
        assert job.status == AIJobStatus.PENDING

    def test_ai_version_defaults_to_one(self) -> None:
        job = self._make_job()
        assert job.ai_version == 1

    def test_attempts_defaults_to_zero(self) -> None:
        job = self._make_job()
        assert job.attempts == 0

    def test_max_attempts_defaults_to_three(self) -> None:
        job = self._make_job()
        assert job.max_attempts == 3

    def test_error_message_defaults_to_none(self) -> None:
        job = self._make_job()
        assert job.error_message is None

    def test_started_at_defaults_to_none(self) -> None:
        job = self._make_job()
        assert job.started_at is None

    def test_completed_at_defaults_to_none(self) -> None:
        job = self._make_job()
        assert job.completed_at is None

    def test_created_at_auto_populated(self) -> None:
        job = self._make_job()
        assert job.created_at is not None
        assert isinstance(job.created_at, datetime)


@pytest.mark.unit
class TestAIJobExplicitValues:
    def _make_job(self, **overrides: Any) -> AIJob:
        defaults: dict[str, Any] = {
            "silver_post_id": uuid4(),
            "job_type": AIJobType.SENTIMENT,
        }
        defaults.update(overrides)
        return AIJob(**defaults)

    def test_explicit_status_running(self) -> None:
        job = self._make_job(status=AIJobStatus.RUNNING)
        assert job.status == AIJobStatus.RUNNING

    def test_explicit_status_completed(self) -> None:
        job = self._make_job(status=AIJobStatus.COMPLETED)
        assert job.status == AIJobStatus.COMPLETED

    def test_explicit_status_failed(self) -> None:
        job = self._make_job(status=AIJobStatus.FAILED)
        assert job.status == AIJobStatus.FAILED

    def test_explicit_error_message(self) -> None:
        job = self._make_job(error_message="API timeout")
        assert job.error_message == "API timeout"

    def test_explicit_attempts(self) -> None:
        job = self._make_job(attempts=2)
        assert job.attempts == 2

    def test_explicit_max_attempts(self) -> None:
        job = self._make_job(max_attempts=5)
        assert job.max_attempts == 5

    def test_explicit_id_override(self) -> None:
        explicit_id = uuid4()
        job = self._make_job(id=explicit_id)
        assert job.id == explicit_id

    def test_explicit_ai_version(self) -> None:
        job = self._make_job(ai_version=2)
        assert job.ai_version == 2

    def test_explicit_started_at(self) -> None:
        now = datetime.now()
        job = self._make_job(started_at=now)
        assert job.started_at == now

    def test_explicit_completed_at(self) -> None:
        now = datetime.now()
        job = self._make_job(completed_at=now)
        assert job.completed_at == now


@pytest.mark.unit
class TestAIJobAllTypes:
    def test_sentiment_type(self) -> None:
        job = AIJob(silver_post_id=uuid4(), job_type=AIJobType.SENTIMENT)
        assert job.job_type == AIJobType.SENTIMENT

    def test_topic_type(self) -> None:
        job = AIJob(silver_post_id=uuid4(), job_type=AIJobType.TOPIC)
        assert job.job_type == AIJobType.TOPIC

    def test_language_type(self) -> None:
        job = AIJob(silver_post_id=uuid4(), job_type=AIJobType.LANGUAGE)
        assert job.job_type == AIJobType.LANGUAGE

    def test_full_enrichment_type(self) -> None:
        job = AIJob(silver_post_id=uuid4(), job_type=AIJobType.FULL_ENRICHMENT)
        assert job.job_type == AIJobType.FULL_ENRICHMENT


@pytest.mark.unit
class TestAIJobRequiredFields:
    def test_silver_post_id_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            AIJob(job_type=AIJobType.SENTIMENT)  # type: ignore[call-arg]

    def test_job_type_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            AIJob(silver_post_id=uuid4())  # type: ignore[call-arg]
