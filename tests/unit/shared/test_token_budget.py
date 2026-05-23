from __future__ import annotations

from collections import defaultdict

from src.shared.token_budget import TokenBudget, estimate_tokens


class TestEstimateTokens:
    def test_empty_string(self) -> None:
        assert estimate_tokens("") == 0

    def test_short_string(self) -> None:
        result = estimate_tokens("hello")
        assert result == 1

    def test_four_chars_one_token(self) -> None:
        assert estimate_tokens("abcd") == 1

    def test_eight_chars_two_tokens(self) -> None:
        assert estimate_tokens("abcdefgh") == 2

    def test_five_chars_rounds_down(self) -> None:
        assert estimate_tokens("abcde") == 1

    def test_returns_at_least_one_for_nonempty(self) -> None:
        assert estimate_tokens("a") >= 1

    def test_long_text(self) -> None:
        text = "a" * 4000
        assert estimate_tokens(text) == 1000


class TestTokenBudgetCheckBudget:
    def test_allows_within_budget(self) -> None:
        budget = TokenBudget(daily_budget=1000, hourly_budget=500)
        assert budget.check_budget(100) is True

    def test_rejects_over_hourly_budget(self) -> None:
        budget = TokenBudget(daily_budget=10000, hourly_budget=100)
        budget.record_usage(80)
        assert budget.check_budget(30) is False

    def test_rejects_over_daily_budget(self) -> None:
        budget = TokenBudget(daily_budget=200, hourly_budget=10000)
        budget.record_usage(180)
        assert budget.check_budget(30) is False

    def test_exact_budget_boundary_allowed(self) -> None:
        budget = TokenBudget(daily_budget=100, hourly_budget=100)
        assert budget.check_budget(100) is True

    def test_one_over_budget_rejected(self) -> None:
        budget = TokenBudget(daily_budget=100, hourly_budget=100)
        assert budget.check_budget(101) is False


class TestTokenBudgetRecordUsage:
    def test_record_increments_usage(self) -> None:
        budget = TokenBudget(daily_budget=10000, hourly_budget=10000)
        budget.record_usage(50)
        budget.record_usage(30)
        summary = budget.get_usage_summary()
        assert summary["hourly_used"] == 80
        assert summary["daily_used"] == 80


class TestTokenBudgetGetUsageSummary:
    def test_initial_summary_is_zero(self) -> None:
        budget = TokenBudget(daily_budget=1000, hourly_budget=500)
        summary = budget.get_usage_summary()
        assert summary["daily_used"] == 0
        assert summary["hourly_used"] == 0
        assert summary["daily_budget"] == 1000
        assert summary["hourly_budget"] == 500

    def test_summary_after_usage(self) -> None:
        budget = TokenBudget(daily_budget=1000, hourly_budget=500)
        budget.record_usage(42)
        summary = budget.get_usage_summary()
        assert summary["hourly_used"] == 42
        assert summary["daily_used"] == 42


class TestTokenBudgetDefaults:
    def test_default_daily_budget(self) -> None:
        budget = TokenBudget()
        summary = budget.get_usage_summary()
        assert summary["daily_budget"] == 1_000_000

    def test_default_hourly_budget(self) -> None:
        budget = TokenBudget()
        summary = budget.get_usage_summary()
        assert summary["hourly_budget"] == 100_000


class TestTokenBudgetEviction:
    def test_evict_removes_old_buckets(self) -> None:
        budget = TokenBudget()
        budget._hourly_buckets = defaultdict(int)
        budget._hourly_buckets["2020-01-01T00"] = 100
        budget._hourly_buckets["2020-01-01T01"] = 200
        budget._evict_old_buckets()
        assert len(budget._hourly_buckets) == 0
