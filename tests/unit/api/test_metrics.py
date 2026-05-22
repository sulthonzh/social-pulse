from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from src.api.app import app
from src.api.metrics import MetricsCollector, MetricsResponse, metrics


class TestMetricsCollectorSingleton:
    @pytest.mark.asyncio
    async def test_returns_same_instance(self) -> None:
        a = MetricsCollector()
        b = MetricsCollector()
        assert a is b


class TestIncrementCounter:
    def test_increment_single(self) -> None:
        collector = MetricsCollector()
        collector.reset()
        collector.increment("crawls_started")
        snapshot = collector.get_snapshot()
        assert snapshot["counters"]["crawls_started"] == 1

    def test_increment_by_value(self) -> None:
        collector = MetricsCollector()
        collector.reset()
        collector.increment("posts_fetched", 42)
        snapshot = collector.get_snapshot()
        assert snapshot["counters"]["posts_fetched"] == 42

    def test_increment_accumulates(self) -> None:
        collector = MetricsCollector()
        collector.reset()
        collector.increment("crawls_completed")
        collector.increment("crawls_completed")
        collector.increment("crawls_completed")
        snapshot = collector.get_snapshot()
        assert snapshot["counters"]["crawls_completed"] == 3


class TestRecordError:
    def test_record_single_error(self) -> None:
        collector = MetricsCollector()
        collector.reset()
        collector.record_error("ValueError")
        snapshot = collector.get_snapshot()
        assert snapshot["errors_by_type"]["ValueError"] == 1

    def test_record_multiple_error_types(self) -> None:
        collector = MetricsCollector()
        collector.reset()
        collector.record_error("ValueError")
        collector.record_error("RuntimeError")
        collector.record_error("ValueError")
        snapshot = collector.get_snapshot()
        assert snapshot["errors_by_type"]["ValueError"] == 2
        assert snapshot["errors_by_type"]["RuntimeError"] == 1


class TestResetClearsAll:
    def test_reset_zeros_counters_and_errors(self) -> None:
        collector = MetricsCollector()
        collector.reset()
        collector.increment("crawls_started")
        collector.increment("posts_fetched", 10)
        collector.record_error("TimeoutError")
        collector.reset()
        snapshot = collector.get_snapshot()
        assert all(v == 0 for v in snapshot["counters"].values())
        assert snapshot["errors_by_type"] == {}


class TestGetSnapshot:
    def test_snapshot_has_uptime(self) -> None:
        collector = MetricsCollector()
        collector.reset()
        snapshot = collector.get_snapshot()
        assert snapshot["uptime_seconds"] >= 0.0

    def test_snapshot_has_all_counter_keys(self) -> None:
        collector = MetricsCollector()
        collector.reset()
        snapshot = collector.get_snapshot()
        expected_keys = {
            "crawls_started",
            "crawls_completed",
            "crawls_failed",
            "posts_fetched",
            "enrichments_started",
            "enrichments_completed",
            "enrichments_failed",
            "gold_builds_started",
            "gold_builds_completed",
            "gold_builds_failed",
            "api_requests_total",
            "api_requests_errors",
        }
        assert set(snapshot["counters"].keys()) == expected_keys


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_snapshot(self) -> None:
        metrics.reset()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/metrics")
            assert response.status_code == 200
            data = response.json()
            assert "uptime_seconds" in data
            assert "counters" in data
            assert "errors_by_type" in data

    @pytest.mark.asyncio
    async def test_metrics_response_model_validates(self) -> None:
        metrics.reset()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/metrics")
            model = MetricsResponse(**response.json())
            assert model.uptime_seconds >= 0.0
            assert isinstance(model.counters, dict)
            assert isinstance(model.errors_by_type, dict)


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_endpoint_with_db_check(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ("ok", "degraded")
            assert "db_path" in data
            assert "env" in data


class TestMiddlewareCounters:
    @pytest.mark.asyncio
    async def test_api_requests_incremented(self) -> None:
        metrics.reset()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/health")
            snapshot = metrics.get_snapshot()
            assert snapshot["counters"]["api_requests_total"] >= 1
