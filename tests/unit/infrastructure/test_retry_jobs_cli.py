from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import src.infrastructure.ai.retry_jobs as retry_jobs_module
from src.infrastructure.ai.retry_jobs import main


@pytest.mark.unit
class TestRetryJobsCLI:
    def test_main_resets_all_failed_jobs(self):
        mock_conn = MagicMock()
        mock_repo = MagicMock()
        mock_repo.reset_failed_jobs.return_value = 5
        mock_logger = MagicMock()

        with (
            patch.object(retry_jobs_module, "DuckDBAIJobRepository", return_value=mock_repo),
            patch.object(retry_jobs_module, "create_all_tables"),
            patch.object(retry_jobs_module, "connect_with_retry", return_value=mock_conn),
            patch.object(retry_jobs_module, "logger", mock_logger),
            patch("sys.argv", ["retry_jobs"]),
        ):
            main()

        mock_repo.reset_failed_jobs.assert_called_once_with(job_type=None)
        mock_conn.close.assert_called_once()
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("5" in c and "reset_count" in c for c in info_calls)

    def test_main_resets_with_job_type(self):
        mock_conn = MagicMock()
        mock_repo = MagicMock()
        mock_repo.reset_failed_jobs.return_value = 2
        mock_logger = MagicMock()

        with (
            patch.object(retry_jobs_module, "DuckDBAIJobRepository", return_value=mock_repo),
            patch.object(retry_jobs_module, "create_all_tables"),
            patch.object(retry_jobs_module, "connect_with_retry", return_value=mock_conn),
            patch.object(retry_jobs_module, "logger", mock_logger),
            patch("sys.argv", ["retry_jobs", "--job-type", "sentiment"]),
        ):
            main()

        mock_repo.reset_failed_jobs.assert_called_once_with(job_type="sentiment")
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("2" in c and "reset_count" in c for c in info_calls)

    def test_main_no_failed_jobs(self):
        mock_conn = MagicMock()
        mock_repo = MagicMock()
        mock_repo.reset_failed_jobs.return_value = 0
        mock_logger = MagicMock()

        with (
            patch.object(retry_jobs_module, "DuckDBAIJobRepository", return_value=mock_repo),
            patch.object(retry_jobs_module, "create_all_tables"),
            patch.object(retry_jobs_module, "connect_with_retry", return_value=mock_conn),
            patch.object(retry_jobs_module, "logger", mock_logger),
            patch("sys.argv", ["retry_jobs"]),
        ):
            main()

        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("0" in c and "reset_count" in c for c in info_calls)

    def test_main_db_connection_failure_exits(self):
        with (
            patch.object(
                retry_jobs_module, "connect_with_retry", side_effect=RuntimeError("connection failed")
            ),
            patch("sys.argv", ["retry_jobs"]),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
