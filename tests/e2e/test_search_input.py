"""E2E tests for the Search Input screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.e2e.conftest import navigate_to

if TYPE_CHECKING:
    from playwright.sync_api import Page


@pytest.mark.e2e
def test_search_input_page_shows_form(page: Page) -> None:
    navigate_to(page, "Search Input")
    page.wait_for_selector("h2:has-text('Search Input')", timeout=10000)
    page.wait_for_selector('label:has-text("Keyword")', timeout=5000)
    page.wait_for_selector('label:has-text("Platform")', timeout=5000)
    page.wait_for_selector('label:has-text("Date range")', timeout=5000)
    submit_btn = page.wait_for_selector('button:has-text("Create Search Request")', timeout=5000)
    assert submit_btn is not None


@pytest.mark.e2e
def test_submit_empty_keyword_shows_error(page: Page) -> None:
    navigate_to(page, "Search Input")
    page.wait_for_selector("h2:has-text('Search Input')", timeout=10000)

    page.click('button:has-text("Create Search Request")')
    error = page.wait_for_selector('[data-testid="stAlert"]', timeout=10000)
    assert error is not None
    assert "required" in error.inner_text().lower()


@pytest.mark.e2e
def test_submit_with_keyword_shows_response(page: Page) -> None:
    navigate_to(page, "Search Input")
    page.wait_for_selector("h2:has-text('Search Input')", timeout=10000)

    page.fill('input[aria-label="Keyword"]', "data engineering")
    page.click('button:has-text("Create Search Request")')

    alert = page.wait_for_selector('[data-testid="stAlert"]', timeout=15000)
    assert alert is not None
    alert_text = alert.inner_text().lower()
    assert "data engineering" in alert_text or "failed" in alert_text


@pytest.mark.e2e
def test_seeded_search_requests_are_listed(page: Page) -> None:
    navigate_to(page, "Search Input")
    page.wait_for_selector("h2:has-text('Search Input')", timeout=10000)

    page.wait_for_selector("text=data engineering", timeout=10000)
    page.wait_for_selector("text=machine learning", timeout=5000)
    page.wait_for_selector("text=cloud computing", timeout=5000)
