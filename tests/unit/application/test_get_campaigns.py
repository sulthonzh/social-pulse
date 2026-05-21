from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from src.application.use_cases.get_campaigns import GetCampaigns


def _build_use_case(campaigns: list[dict[str, str]] | None = None):
    repo = MagicMock(spec=["get_campaigns"])
    repo.get_campaigns.return_value = campaigns or []
    return GetCampaigns(gold_repo=repo), repo


@pytest.mark.unit
class TestGetCampaigns:
    def test_execute_returns_campaigns_from_repo(self):
        campaigns = [
            {"id": "abc-123", "keyword": "python", "platform": "twitter"},
            {"id": "def-456", "keyword": "java", "platform": "facebook"},
        ]
        use_case, repo = _build_use_case(campaigns)

        result = use_case.execute()

        assert result == campaigns
        repo.get_campaigns.assert_called_once_with()

    def test_execute_returns_empty_when_no_campaigns(self):
        use_case, repo = _build_use_case([])

        result = use_case.execute()

        assert result == []
        repo.get_campaigns.assert_called_once_with()

    def test_execute_delegates_to_repository(self):
        use_case, repo = _build_use_case()

        use_case.execute()

        repo.get_campaigns.assert_called_once_with()

    def test_execute_preserves_all_campaign_fields(self):
        campaigns = [
            {"id": "a", "keyword": "k1", "platform": "p1"},
            {"id": "b", "keyword": "k2", "platform": "p2"},
            {"id": "c", "keyword": "k3", "platform": "p3"},
        ]
        use_case, _ = _build_use_case(campaigns)

        result = use_case.execute()

        assert len(result) == 3
        assert result[0]["id"] == "a"
        assert result[1]["keyword"] == "k2"
        assert result[2]["platform"] == "p3"
