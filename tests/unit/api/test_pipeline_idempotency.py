from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.api.app import (
    _DEDUP_TTL_SECONDS,
    PipelineStartRequest,
    _cleanup_expired_starts,
    _dedup_key,
    _recent_starts,
    app,
)


def _make_request(
    keyword: str = "test",
    platform: str = "twitter",
    start_date: str = "2025-01-01",
    end_date: str = "2025-01-31",
) -> PipelineStartRequest:
    return PipelineStartRequest(
        keyword=keyword,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )


@pytest.fixture(autouse=True)
def _clear_dedup() -> None:
    _recent_starts.clear()
    yield
    _recent_starts.clear()


class TestDedupKey:
    def test_dedup_key_format(self) -> None:
        req = _make_request()
        assert _dedup_key(req) == "test:twitter:2025-01-01:2025-01-31"

    def test_dedup_key_different_keyword(self) -> None:
        req_a = _make_request(keyword="python")
        req_b = _make_request(keyword="rust")
        assert _dedup_key(req_a) != _dedup_key(req_b)

    def test_dedup_key_different_platform(self) -> None:
        req_a = _make_request(platform="twitter")
        req_b = _make_request(platform="reddit")
        assert _dedup_key(req_a) != _dedup_key(req_b)

    def test_dedup_key_different_dates(self) -> None:
        req_a = _make_request(start_date="2025-01-01", end_date="2025-01-31")
        req_b = _make_request(start_date="2025-02-01", end_date="2025-02-28")
        assert _dedup_key(req_a) != _dedup_key(req_b)


class TestPipelineIdempotency:
    @pytest.mark.asyncio
    async def test_duplicate_request_returns_same_run_id(self) -> None:
        with patch("src.api.app._run_pipeline", new_callable=AsyncMock):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {
                    "keyword": "dedup-test",
                    "platform": "youtube",
                    "start_date": "2025-03-01",
                    "end_date": "2025-03-31",
                }
                response_a = await client.post("/api/pipeline/start", json=payload)
                assert response_a.status_code == 200

                response_b = await client.post("/api/pipeline/start", json=payload)
                assert response_b.status_code == 200

                assert response_a.json()["run_id"] == response_b.json()["run_id"]

    @pytest.mark.asyncio
    async def test_different_parameters_create_different_run_ids(self) -> None:
        with patch("src.api.app._run_pipeline", new_callable=AsyncMock):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response_a = await client.post(
                    "/api/pipeline/start",
                    json={
                        "keyword": "python",
                        "platform": "twitter",
                        "start_date": "2025-01-01",
                        "end_date": "2025-01-31",
                    },
                )
                assert response_a.status_code == 200

                response_b = await client.post(
                    "/api/pipeline/start",
                    json={
                        "keyword": "python",
                        "platform": "reddit",
                        "start_date": "2025-01-01",
                        "end_date": "2025-01-31",
                    },
                )
                assert response_b.status_code == 200

                assert response_a.json()["run_id"] != response_b.json()["run_id"]


class TestExpiredTTL:
    def test_expired_entry_allows_new_start(self) -> None:
        key = "test:twitter:2025-01-01:2025-01-31"
        fake_run_id = "fake-run-id"
        _recent_starts[key] = (fake_run_id, time.monotonic() - _DEDUP_TTL_SECONDS - 1)

        _cleanup_expired_starts()

        assert key not in _recent_starts
