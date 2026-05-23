from __future__ import annotations

import logging
from unittest.mock import patch

import structlog
from src.shared.logging_config import (
    _add_caller_info,
    _add_log_level,
    _add_service_name,
    _format_timestamp,
    configure_logging,
)


class TestConfigureLogging:
    def test_development_mode_uses_console_renderer(self) -> None:
        with patch("src.shared.logging_config.settings") as mock_settings:
            mock_settings.env = "development"
            mock_settings.log_level = "INFO"
            configure_logging()

            assert structlog.is_configured()

    def test_production_mode_uses_json_renderer(self) -> None:
        with patch("src.shared.logging_config.settings") as mock_settings:
            mock_settings.env = "production"
            mock_settings.log_level = "INFO"
            configure_logging()

            assert structlog.is_configured()

    def test_sets_root_logger_level(self) -> None:
        with patch("src.shared.logging_config.settings") as mock_settings:
            mock_settings.env = "development"
            mock_settings.log_level = "DEBUG"
            configure_logging()

            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_defaults_to_info_on_invalid_level(self) -> None:
        with patch("src.shared.logging_config.settings") as mock_settings:
            mock_settings.env = "development"
            mock_settings.log_level = "INVALID"
            configure_logging()

            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

    def test_clears_existing_handlers(self) -> None:
        root_logger = logging.getLogger()
        root_logger.addHandler(logging.StreamHandler())
        initial_count = len(root_logger.handlers)

        with patch("src.shared.logging_config.settings") as mock_settings:
            mock_settings.env = "development"
            mock_settings.log_level = "INFO"
            configure_logging()

        assert len(root_logger.handlers) < initial_count + 1

    def test_processor_formatter_on_handler(self) -> None:
        with patch("src.shared.logging_config.settings") as mock_settings:
            mock_settings.env = "development"
            mock_settings.log_level = "INFO"
            configure_logging()

            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 1
            handler = root_logger.handlers[0]
            assert isinstance(handler.formatter, structlog.stdlib.ProcessorFormatter)


class TestServiceName:
    def test_service_name_in_event_dict(self) -> None:
        with patch("src.shared.logging_config.settings") as mock_settings:
            mock_settings.env = "production"
            mock_settings.log_level = "INFO"
            configure_logging()

        event: structlog.types.EventDict = {}
        result = _add_service_name(logging.getLogger(), "info", event)
        assert result["service"] == "socialpulse"


class TestTimestampFormat:
    def test_timestamp_in_iso_format(self) -> None:
        event: structlog.types.EventDict = {}
        result = _format_timestamp(logging.getLogger(), "info", event)
        assert "timestamp" in result
        assert "T" in result["timestamp"]


class TestLogLevel:
    def test_log_level_added_to_event(self) -> None:
        event: structlog.types.EventDict = {}
        result = _add_log_level(logging.getLogger(), "warning", event)
        assert result["level"] == "warning"


class TestCallerInfo:
    def test_caller_info_with_record(self) -> None:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="test",
            args=(),
            exc_info=None,
        )
        event: structlog.types.EventDict = {"_record": record}
        result = _add_caller_info(logging.getLogger(), "info", event)
        assert result["caller"]["line"] == 42
        assert "module" in result["caller"]
        assert "function" in result["caller"]

    def test_caller_info_without_record(self) -> None:
        event: structlog.types.EventDict = {}
        result = _add_caller_info(logging.getLogger(), "info", event)
        assert "caller" not in result


class TestProductionJsonOutput:
    def test_produces_valid_json(self) -> None:
        with patch("src.shared.logging_config.settings") as mock_settings:
            mock_settings.env = "production"
            mock_settings.log_level = "INFO"
            configure_logging()

        bound_logger = structlog.get_logger("test_json")
        with structlog.testing.capture_logs() as captured:
            bound_logger.info("test_message", key="value")

        assert len(captured) == 1
        assert captured[0]["key"] == "value"
        assert captured[0]["event"] == "test_message"
