"""FastAPI SSE server for pipeline progress streaming."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import date
from typing import TYPE_CHECKING, Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.api.events import EventBus, PipelineEvent, PipelineStage, event_bus
from src.shared.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = structlog.get_logger(__name__)


class PipelineStartRequest(BaseModel):
    keyword: str
    platform: str
    start_date: str  # ISO format YYYY-MM-DD
    end_date: str  # ISO format YYYY-MM-DD


class PipelineStartResponse(BaseModel):
    run_id: str
    message: str


class HealthResponse(BaseModel):
    status: str


async def _run_pipeline(
    run_id: str,
    keyword: str,
    platform: str,
    start_date: date,
    end_date: date,
    bus: EventBus,
) -> None:
    import duckdb  # noqa: PLC0415

    from src.application.use_cases.ingest_pipeline import (  # noqa: PLC0415
        IngestPipeline,
    )
    from src.domain.value_objects.platform import Platform  # noqa: PLC0415

    def on_progress(stage: str, current: int, total: int) -> None:
        stage_enum = (
            PipelineStage(stage)
            if stage in ("crawling", "enriching", "gold")
            else PipelineStage.CRAWLING
        )
        message_map: dict[str, str] = {
            "crawling": (
                f"Crawling {platform} for '{keyword}'..."
                if current == 0
                else f"Crawled {current} posts"
            ),
            "enriching": f"Enriching post {current}/{total} (AI analysis)...",
            "gold": "Building analytics tables...",
        }
        bus.publish(
            PipelineEvent(
                run_id=run_id,
                stage=stage_enum,
                current=current,
                total=total,
                message=message_map.get(stage, stage),
            )
        )

    conn: duckdb.DuckDBPyConnection | None = None
    try:
        conn = duckdb.connect(settings.db_path)
        pipeline = IngestPipeline(conn, progress_callback=on_progress)
        result = await pipeline.execute(
            keyword=keyword,
            platform=Platform(platform),
            start_date=start_date,
            end_date=end_date,
        )

        bus.publish(
            PipelineEvent(
                run_id=run_id,
                stage=PipelineStage.COMPLETE,
                current=0,
                total=0,
                message="Pipeline complete!",
                data={
                    "posts_crawled": result.posts_crawled,
                    "posts_enriched": result.posts_enriched,
                    "gold_built": result.gold_built,
                    "search_request_id": result.search_request_id,
                },
            )
        )
        logger.info("pipeline_run_complete", run_id=run_id, result=repr(result))

    except Exception as exc:
        logger.exception("pipeline_run_failed", run_id=run_id, error=str(exc))
        bus.publish(
            PipelineEvent(
                run_id=run_id,
                stage=PipelineStage.ERROR,
                current=0,
                total=0,
                message=f"Pipeline failed: {exc}",
                data={"error": str(exc)},
            )
        )
    finally:
        bus.complete(run_id)
        if conn is not None:
            conn.close()


async def _event_generator(run_id: str, bus: EventBus) -> AsyncGenerator[dict[str, Any], None]:
    queue = bus.subscribe(run_id)
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=300.0)  # 5 min timeout
            if event is None:
                yield {"event": "done", "data": ""}
                break
            yield {
                "event": "message",
                "data": json.dumps(event.to_dict()),
                "retry": 5000,
            }
    except TimeoutError:
        yield {"event": "timeout", "data": ""}
    except asyncio.CancelledError:
        pass
    finally:
        bus.remove(run_id)


def _handle_task_result(task: asyncio.Task[None]) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.exception("pipeline_task_failed", error=str(exc))


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("api_server_started", port=8000)
    yield
    logger.info("api_server_stopped")


app = FastAPI(
    title="SocialPulse Pipeline API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/pipeline/start", response_model=PipelineStartResponse)
async def start_pipeline(request: PipelineStartRequest) -> PipelineStartResponse:
    """Start a new pipeline run. Returns a run_id for SSE subscription."""
    run_id = str(uuid.uuid4())
    event_bus.create_run(run_id)

    start_date = date.fromisoformat(request.start_date)
    end_date = date.fromisoformat(request.end_date)

    # Store ref to prevent GC of the fire-and-forget task
    background_task = asyncio.create_task(
        _run_pipeline(
            run_id=run_id,
            keyword=request.keyword,
            platform=request.platform,
            start_date=start_date,
            end_date=end_date,
            bus=event_bus,
        )
    )
    background_task.add_done_callback(_handle_task_result)

    logger.info("pipeline_started", run_id=run_id, keyword=request.keyword)
    return PipelineStartResponse(run_id=run_id, message="Pipeline started")


@app.get("/api/pipeline/{run_id}/stream")
async def stream_pipeline(run_id: str) -> EventSourceResponse:
    """SSE endpoint — streams pipeline progress events."""
    if not event_bus.has_run(run_id):
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return EventSourceResponse(_event_generator(run_id, event_bus))


def main() -> None:
    """Run the API server."""
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
