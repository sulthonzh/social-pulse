"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import structlog
from structlog.stdlib import ProcessorFormatter

from src.shared.config import settings


def _add_service_name(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    event_dict["service"] = "socialpulse"
    return event_dict


def _add_caller_info(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    record: logging.LogRecord | None = event_dict.get("_record")
    if record is not None:
        event_dict["caller"] = {
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
    return event_dict


def _format_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


def _add_log_level(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    event_dict["level"] = method_name
    return event_dict


def _build_processors() -> list[structlog.types.Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _format_timestamp,
        _add_log_level,
        _add_service_name,
        _add_caller_info,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]


def configure_logging() -> None:
    """Configure structlog and stdlib logging based on settings."""
    shared_processors = _build_processors()

    if settings.env == "production":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
