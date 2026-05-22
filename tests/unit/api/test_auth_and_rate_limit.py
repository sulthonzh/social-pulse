from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.api.app import app
from src.api.rate_limiter import RateLimiter
from src.shared.config import settings


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_rejects_missing_api_key(self, client: AsyncClient) -> None:
        with patch.object(settings, "api_key", "secret-key"):
            response = await client.get("/api/metrics")
        assert response.status_code == 401
        assert response.json() == {"error": "Unauthorized"}

    @pytest.mark.asyncio
    async def test_rejects_wrong_api_key(self, client: AsyncClient) -> None:
        with patch.object(settings, "api_key", "secret-key"):
            response = await client.get(
                "/api/metrics",
                headers={"X-API-Key": "wrong-key"},
            )
        assert response.status_code == 401
        assert response.json() == {"error": "Unauthorized"}

    @pytest.mark.asyncio
    async def test_allows_correct_api_key(self, client: AsyncClient) -> None:
        with patch.object(settings, "api_key", "secret-key"):
            response = await client.get(
                "/api/metrics",
                headers={"X-API-Key": "secret-key"},
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_endpoint_skips_auth(self, client: AsyncClient) -> None:
        with patch.object(settings, "api_key", "secret-key"):
            response = await client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skips_auth_when_api_key_empty(self, client: AsyncClient) -> None:
        with patch.object(settings, "api_key", ""):
            response = await client.get("/api/metrics")
        assert response.status_code == 200


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, client: AsyncClient) -> None:
        small_limiter = RateLimiter(max_requests=5)
        with patch("src.api.app._rate_limiter", small_limiter):
            response = await client.post(
                "/api/pipeline/start",
                json={
                    "keyword": "test",
                    "platform": "twitter",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                },
            )
        assert response.status_code in (200, 422)  # 422 from validation is fine

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, client: AsyncClient) -> None:
        small_limiter = RateLimiter(max_requests=2)
        with patch("src.api.app._rate_limiter", small_limiter):
            for _ in range(2):
                await client.post(
                    "/api/pipeline/start",
                    json={
                        "keyword": "test",
                        "platform": "twitter",
                        "start_date": "2025-01-01",
                        "end_date": "2025-01-31",
                    },
                )
            response = await client.post(
                "/api/pipeline/start",
                json={
                    "keyword": "test",
                    "platform": "twitter",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                },
            )
        assert response.status_code == 429
        assert response.json() == {"error": "Rate limit exceeded"}

    @pytest.mark.asyncio
    async def test_only_applies_to_pipeline_start(self, client: AsyncClient) -> None:
        small_limiter = RateLimiter(max_requests=1)
        with patch("src.api.app._rate_limiter", small_limiter):
            await client.post(
                "/api/pipeline/start",
                json={
                    "keyword": "test",
                    "platform": "twitter",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                },
            )
            response = await client.get("/api/health")
        assert response.status_code == 200
