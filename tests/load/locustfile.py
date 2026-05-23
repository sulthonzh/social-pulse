"""Load testing scenarios for SocialPulse API using Locust."""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import ClassVar

from locust import HttpUser, between, task


class HealthCheckUser(HttpUser):
    """Simulates monitoring / health-check traffic.

    Weight 60 — the most common traffic pattern in production monitoring.
    """

    weight = 60
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    @task
    def healthz(self) -> None:
        self.client.get("/healthz")

    @task
    def readyz(self) -> None:
        self.client.get("/readyz")

    @task(3)
    def v1_health(self) -> None:
        self.client.get("/v1/health")


class MetricsUser(HttpUser):
    """Simulates metrics scraping (e.g. Prometheus or dashboard consumers).

    Weight 30 — second most common pattern.
    """

    weight = 30
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    @task(2)
    def v1_metrics(self) -> None:
        self.client.get("/v1/metrics")

    @task
    def prometheus_metrics(self) -> None:
        self.client.get("/metrics")


class PipelineUser(HttpUser):
    """Simulates pipeline start requests.

    Weight 10 — least frequent; pipeline starts are intentional user actions.
    """

    weight = 10
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    _PLATFORMS: ClassVar[list[str]] = ["twitter", "facebook", "instagram", "youtube", "reddit"]
    _KEYWORDS: ClassVar[list[str]] = [
        "AI",
        "climate",
        "election",
        "crypto",
        "python",
        "startup",
        "music",
        "sports",
    ]

    @task
    def start_pipeline(self) -> None:
        end = date.today() - timedelta(days=random.randint(0, 7))
        start = end - timedelta(days=random.randint(1, 14))
        payload = {
            "keyword": random.choice(self._KEYWORDS),
            "platform": random.choice(self._PLATFORMS),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        self.client.post("/v1/pipeline/start", json=payload)
