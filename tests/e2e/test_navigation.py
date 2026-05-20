"""E2E tests for sidebar navigation across all four screens."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.e2e.conftest import navigate_to

if TYPE_CHECKING:
    from playwright.sync_api import Page

SCREENS = [
    "Search Input",
    "Post Explorer",
    "Campaign Analytics",
    "Cross-Campaign Comparison",
]


@pytest.mark.e2e
def test_sidebar_navigation_selectbox_exists(page: Page) -> None:
    assert page.query_selector('[data-baseweb="select"]') is not None


@pytest.mark.e2e
@pytest.mark.parametrize("screen_name", SCREENS)
def test_navigate_to_screen_renders_header(page: Page, screen_name: str) -> None:
    navigate_to(page, screen_name)
    header = page.wait_for_selector(
        f'h2:has-text("{screen_name}")',
        timeout=10000,
    )
    assert header is not None
