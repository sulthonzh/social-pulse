"""E2E tests for the Post Explorer screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.e2e.conftest import navigate_to

if TYPE_CHECKING:
    from playwright.sync_api import Page


@pytest.mark.e2e
def test_post_explorer_renders_header_and_total_metric(page: Page) -> None:
    navigate_to(page, "Post Explorer")
    page.wait_for_selector("h1:has-text('Post Explorer')", timeout=10000)
    metric = page.wait_for_selector('[data-testid="stMetricValue"]', timeout=10000)
    assert metric is not None
    # Seeded DB has 14 posts total
    assert metric.inner_text() == "14"


@pytest.mark.e2e
def test_post_explorer_renders_header_and_total_metric(page: Page) -> None:
    navigate_to(page, "Post Explorer")
    page.wait_for_selector("h2:has-text('Post Explorer')", timeout=10000)
    metric = page.wait_for_selector('[data-testid="stMetricValue"]', timeout=10000)
    assert metric is not None
    assert metric.inner_text() == "14"


@pytest.mark.e2e
def test_post_explorer_displays_posts(page: Page) -> None:
    navigate_to(page, "Post Explorer")
    page.wait_for_selector("h2:has-text('Post Explorer')", timeout=10000)

    page.wait_for_selector('text=@dataeng_guru', timeout=10000)


@pytest.mark.e2e
def test_post_explorer_sentiment_filter(page: Page) -> None:
    navigate_to(page, "Post Explorer")
    page.wait_for_selector("h2:has-text('Post Explorer')", timeout=10000)

    sidebar = page.query_selector('[data-testid="stSidebar"]')
    sidebar_selects = sidebar.query_selector_all('[data-baseweb="select"]')

    sidebar_selects[1].click()

    positive_opt = page.wait_for_selector(
        'li[role="option"]:has-text("Positive")', timeout=5000
    )
    positive_opt.click()
    page.wait_for_timeout(2000)

    metric = page.wait_for_selector('[data-testid="stMetricValue"]', timeout=10000)
    assert metric is not None
    assert metric.inner_text() == "7"
