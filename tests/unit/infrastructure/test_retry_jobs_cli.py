from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import src.infrastructure.ai.retry_jobs as retry_jobs_module
from src.infrastructure.ai.retry_jobs import main


@pytest.mark.unit
class TestRetryJobsCLI:
    def test_main_resets_all_failed_jobs(self, capsys):
        mock_conn = MagicMock()
        mock_repo = MagicMock()
        mock_repo.reset_failed_jobs.return_value = 5
        mock_duckdb = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        with (
            patch.object(retry_jobs_module, "DuckDBAIJobRepository", return_value=mock_repo),
            patch.object(retry_jobs_module, "create_all_tables"),
            patch("sys.argv", ["retry_jobs"]),
            patch.dict("sys.modules", {"duckdb": mock_duckdb}),
        ):
            main()

        mock_repo.reset_failed_jobs.assert_called_once_with(job_type=None)
        mock_conn.close.assert_called_once()
        captured = capsys.readouterr()
        assert "Reset 5 failed job(s)" in captured.out

    def test_main_resets_with_job_type(self, capsys):
        mock_conn = MagicMock()
        mock_repo = MagicMock()
        mock_repo.reset_failed_jobs.return_value = 2
        mock_duckdb = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        with (
            patch.object(retry_jobs_module, "DuckDBAIJobRepository", return_value=mock_repo),
            patch.object(retry_jobs_module, "create_all_tables"),
            patch("sys.argv", ["retry_jobs", "--job-type", "sentiment"]),
            patch.dict("sys.modules", {"duckdb": mock_duckdb}),
        ):
            main()

        mock_repo.reset_failed_jobs.assert_called_once_with(job_type="sentiment")
        captured = capsys.readouterr()
        assert "Reset 2 failed job(s)" in captured.out

    def test_main_no_failed_jobs(self, capsys):
        mock_conn = MagicMock()
        mock_repo = MagicMock()
        mock_repo.reset_failed_jobs.return_value = 0
        mock_duckdb = MagicMock()
        mock_duckdb.connect.return_value = mock_conn

        with (
            patch.object(retry_jobs_module, "DuckDBAIJobRepository", return_value=mock_repo),
            patch.object(retry_jobs_module, "create_all_tables"),
            patch("sys.argv", ["retry_jobs"]),
            patch.dict("sys.modules", {"duckdb": mock_duckdb}),
        ):
            main()

        captured = capsys.readouterr()
        assert "Reset 0 failed job(s)" in captured.out

    def test_main_db_connection_failure_exits(self):
        mock_duckdb = MagicMock()
        mock_duckdb.connect.side_effect = RuntimeError("connection failed")

        with (
            patch.dict("sys.modules", {"duckdb": mock_duckdb}),
            patch("sys.argv", ["retry_jobs"]),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
