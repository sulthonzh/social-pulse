from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from src.shared.worker_health import WorkerHealthServer

if TYPE_CHECKING:
    from collections.abc import Generator


class TestWorkerHealthServerCounters:
    def test_initial_counters_zero(self) -> None:
        server = WorkerHealthServer(port=0)
        assert server._jobs_processed == 0
        assert server._errors_count == 0
        assert server._last_activity is None

    def test_record_job_processed_increments(self) -> None:
        server = WorkerHealthServer(port=0)
        server.record_job_processed()
        server.record_job_processed()
        server.record_job_processed()
        assert server._jobs_processed == 3
        assert server._errors_count == 0

    def test_record_error_increments(self) -> None:
        server = WorkerHealthServer(port=0)
        server.record_error()
        server.record_error()
        assert server._errors_count == 2
        assert server._jobs_processed == 0

    def test_record_job_updates_last_activity(self) -> None:
        server = WorkerHealthServer(port=0)
        assert server._last_activity is None
        server.record_job_processed()
        assert server._last_activity is not None

    def test_record_error_updates_last_activity(self) -> None:
        server = WorkerHealthServer(port=0)
        server.record_error()
        assert server._last_activity is not None

    def test_mixed_counters(self) -> None:
        server = WorkerHealthServer(port=0)
        server.record_job_processed()
        server.record_error()
        server.record_job_processed()
        assert server._jobs_processed == 2
        assert server._errors_count == 1


class TestWorkerHealthServerHTTP:
    @pytest.fixture
    def health_server(self) -> Generator[WorkerHealthServer, None, None]:
        server = WorkerHealthServer(port=0)
        server.start()
        time.sleep(0.1)
        yield server
        server.stop()

    def _base_url(self, server: WorkerHealthServer) -> str:
        addr = server.server_address
        host = addr[0] if isinstance(addr[0], str) else str(addr[0], encoding="utf-8")
        port = addr[1]
        return f"http://{host}:{port}"

    def test_health_endpoint_returns_200(self, health_server: WorkerHealthServer) -> None:
        url = f"{self._base_url(health_server)}/health"
        resp = urlopen(url)  # noqa: S310
        assert resp.status == 200

    def test_health_response_format(self, health_server: WorkerHealthServer) -> None:
        url = f"{self._base_url(health_server)}/health"
        resp = urlopen(url)  # noqa: S310
        data = json.loads(resp.read())
        assert data["status"] == "ok"
        assert "uptime_seconds" in data
        assert data["jobs_processed"] == 0
        assert data["errors_count"] == 0
        assert data["last_activity"] is None

    def test_health_reflects_counters(self, health_server: WorkerHealthServer) -> None:
        health_server.record_job_processed()
        health_server.record_job_processed()
        health_server.record_error()

        url = f"{self._base_url(health_server)}/health"
        resp = urlopen(url)  # noqa: S310
        data = json.loads(resp.read())
        assert data["jobs_processed"] == 2
        assert data["errors_count"] == 1
        assert data["last_activity"] is not None

    def test_uptime_increases(self, health_server: WorkerHealthServer) -> None:
        url = f"{self._base_url(health_server)}/health"
        data1 = json.loads(urlopen(url).read())  # noqa: S310
        time.sleep(0.2)
        data2 = json.loads(urlopen(url).read())  # noqa: S310
        assert data2["uptime_seconds"] > data1["uptime_seconds"]

    def test_unknown_path_returns_404(self, health_server: WorkerHealthServer) -> None:
        url = f"{self._base_url(health_server)}/unknown"
        req = Request(url)  # noqa: S310
        with pytest.raises(HTTPError):
            urlopen(req)  # noqa: S310


class TestWorkerHealthServerLifecycle:
    def test_start_and_stop(self) -> None:
        server = WorkerHealthServer(port=0)
        server.start()
        assert server._thread is not None
        assert server._thread.is_alive()
        server.stop()
        assert server._thread is None

    def test_stop_is_idempotent(self) -> None:
        server = WorkerHealthServer(port=0)
        server.start()
        server.stop()
        server.stop()
