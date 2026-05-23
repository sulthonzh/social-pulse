# Load Testing

Load tests for the SocialPulse API using [Locust](https://locust.io/).

## Scenarios

| User class       | Weight | Endpoints                                          |
|------------------|--------|----------------------------------------------------|
| `HealthCheckUser` | 60    | `/healthz`, `/readyz`, `/v1/health`                |
| `MetricsUser`    | 30     | `/v1/metrics`, `/metrics`                          |
| `PipelineUser`   | 10     | `POST /v1/pipeline/start`                          |

## Prerequisites

```bash
uv sync --extra dev
```

## Quick Start

Start the API first:

```bash
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

Run Locust in another terminal:

```bash
uv run locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Open http://localhost:8089 for the Locust web UI.

## Headless Mode (CI)

```bash
uv run locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 60s
```

## Distributed Mode

```bash
# Master
uv run locust -f tests/load/locustfile.py --master

# Workers (run on each node)
uv run locust -f tests/load/locustfile.py --worker --master-host=<MASTER_IP>
```
