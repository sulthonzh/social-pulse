"""E2E tests for the Campaign Analytics screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.e2e.conftest import navigate_to

if TYPE_CHECKING:
    from playwright.sync_api import Page


@pytest.mark.e2e
def test_campaign_analytics_renders_header(page: Page) -> None:
    navigate_to(page, "Campaign Analytics")
    page.wait_for_selector("h2:has-text('Campaign Analytics')", timeout=10000)


@pytest.mark.e2e
def test_campaign_analytics_shows_campaign_data(page: Page) -> None:
    navigate_to(page, "Campaign Analytics")
    page.wait_for_selector("h2:has-text('Campaign Analytics')", timeout=10000)

    page.wait_for_selector('[data-testid="stMetricValue"]', timeout=10000)
    metrics = page.query_selector_all('[data-testid="stMetricValue"]')
    assert len(metrics) >= 5


@pytest.mark.e2e
def test_campaign_analytics_shows_charts(page: Page) -> None:
    navigate_to(page, "Campaign Analytics")
    page.wait_for_selector("h2:has-text('Campaign Analytics')", timeout=10000)

    page.wait_for_selector('h3:has-text("Sentiment Breakdown")', timeout=10000)
    page.wait_for_selector('h3:has-text("Volume Trend")', timeout=5000)
