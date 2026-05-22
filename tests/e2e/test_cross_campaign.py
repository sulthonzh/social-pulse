"""E2E tests for the Cross-Campaign Comparison screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.e2e.conftest import navigate_to

if TYPE_CHECKING:
    from playwright.sync_api import Page


@pytest.mark.e2e
def test_cross_campaign_renders_header(page: Page) -> None:
    navigate_to(page, "Cross-Campaign Comparison")
    page.wait_for_selector(
        "h2:has-text('Cross-Campaign Comparison')",
        timeout=10000,
    )


@pytest.mark.e2e
def test_cross_campaign_shows_warning_with_less_than_two(page: Page) -> None:
    navigate_to(page, "Cross-Campaign Comparison")
    page.wait_for_selector(
        "h2:has-text('Cross-Campaign Comparison')",
        timeout=10000,
    )

    warning = page.wait_for_selector('[data-testid="stAlert"]', timeout=10000)
    assert warning is not None
    assert "at least 2" in warning.inner_text().lower()
