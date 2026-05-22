from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.api.app import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (1,)

        with patch("duckdb.connect", return_value=mock_conn):
            response = await client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "db_path" in data
            assert "env" in data

    @pytest.mark.asyncio
    async def test_health_returns_degraded_when_db_unavailable(
        self, client: AsyncClient
    ) -> None:
        with patch("duckdb.connect", side_effect=Exception("no db")):
            response = await client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"


class TestStartPipeline:
    @pytest.mark.asyncio
    async def test_start_pipeline_validation_empty_keyword(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/pipeline/start",
            json={
                "keyword": "",
                "platform": "twitter",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_start_pipeline_validation_invalid_platform(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/pipeline/start",
            json={
                "keyword": "test",
                "platform": "tiktok",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_start_pipeline_validation_invalid_date_format(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/pipeline/start",
            json={
                "keyword": "test",
                "platform": "twitter",
                "start_date": "not-a-date",
                "end_date": "2025-01-31",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_start_pipeline_validation_keyword_too_long(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/pipeline/start",
            json={
                "keyword": "x" * 201,
                "platform": "twitter",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
            },
        )
        assert response.status_code == 422


class TestStreamPipeline:
    @pytest.mark.asyncio
    async def test_stream_nonexistent_run(self, client: AsyncClient) -> None:
        response = await client.get("/api/pipeline/nonexistent-run/stream")
        assert response.status_code == 404
