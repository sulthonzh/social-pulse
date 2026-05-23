"""Lightweight HTTP health server for background workers.

Exposes a /health endpoint with JSON metrics so that Docker
healthchecks and orchestrators can monitor worker state beyond
simple process-alive checks.

Uses only stdlib (http.server) — no external dependencies.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not found"}).encode())
            return

        health_server = self.server
        assert isinstance(health_server, WorkerHealthServer)
        payload = health_server.snapshot()

        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        # Suppress default stderr logging
        pass


class WorkerHealthServer(HTTPServer):
    """Thread-safe HTTP health server for background workers.

    Runs in a daemon thread so it never prevents process exit.
    Usage::

        health = WorkerHealthServer(port=8081)
        health.start()
        # ... worker does work ...
        health.record_job_processed()
        health.stop()
    """

    def __init__(self, port: int = 8081) -> None:
        super().__init__(("0.0.0.0", port), _HealthHandler)  # noqa: S104
        self._start_time: float = time.monotonic()
        self._jobs_processed: int = 0
        self._errors_count: int = 0
        self._last_activity: str | None = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._port = port

    def record_job_processed(self) -> None:
        with self._lock:
            self._jobs_processed += 1
            self._last_activity = _iso_now()

    def record_error(self) -> None:
        with self._lock:
            self._errors_count += 1
            self._last_activity = _iso_now()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "status": "ok",
                "uptime_seconds": round(time.monotonic() - self._start_time, 2),
                "jobs_processed": self._jobs_processed,
                "errors_count": self._errors_count,
                "last_activity": self._last_activity,
            }

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self.serve_forever,
            daemon=True,
            name="worker-health-server",
        )
        self._thread.start()

    def stop(self) -> None:
        self.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def server_bind(self) -> None:
        """Set SO_REUSEADDR to avoid 'Address already in use' on restart."""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


def _iso_now() -> str:
    return datetime.now(tz=UTC).isoformat()
