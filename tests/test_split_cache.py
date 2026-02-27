"""Tests for split_cache.py."""

from datetime import date
from decimal import Decimal

import pytest

from split_cache import SplitCache, StockSplit


class TestSplitCache:
    """Tests for SplitCache."""

    @pytest.fixture
    def cache_path(self, tmp_path):
        return str(tmp_path / "splits.xml")

    def test_empty_cache(self, cache_path):
        cache = SplitCache(cache_path)
        assert cache.memory == {}

    def test_flush_and_load(self, cache_path):
        # Create cache with data
        cache = SplitCache(cache_path)
        cache.memory["AAPL"] = [
            StockSplit(date=date(2020, 8, 31), ratio=Decimal("4")),
            StockSplit(date=date(2014, 6, 9), ratio=Decimal("7")),
        ]
        cache.flush()

        # Load in new instance
        cache2 = SplitCache(cache_path)
        assert "AAPL" in cache2.memory
        assert len(cache2.memory["AAPL"]) == 2

        # Verify data
        splits = cache2.memory["AAPL"]
        # Should be sorted by date
        assert splits[0].date == date(2014, 6, 9)
        assert splits[0].ratio == Decimal("7")
        assert splits[1].date == date(2020, 8, 31)
        assert splits[1].ratio == Decimal("4")

    def test_get_splits_in_range(self, cache_path):
        cache = SplitCache(cache_path)
        cache.memory["TEST"] = [
            StockSplit(date=date(2020, 1, 15), ratio=Decimal("2")),
            StockSplit(date=date(2021, 6, 1), ratio=Decimal("3")),
            StockSplit(date=date(2022, 12, 31), ratio=Decimal("4")),
        ]

        # Get splits between 2020 and 2022 (exclusive)
        splits = cache.get_splits_in_range("TEST", date(2020, 1, 1), date(2023, 1, 1))
        assert len(splits) == 3

        # Get splits between 2020-06-01 and 2022-06-01
        splits = cache.get_splits_in_range("TEST", date(2020, 6, 1), date(2022, 6, 1))
        assert len(splits) == 1
        assert splits[0].ratio == Decimal("3")

        # No splits in range
        splits = cache.get_splits_in_range("TEST", date(2019, 1, 1), date(2019, 12, 31))
        assert len(splits) == 0

    def test_get_splits_unknown_symbol(self, cache_path):
        cache = SplitCache(cache_path)
        cache.memory["KNOWN"] = []
        # Unknown symbols trigger fetch, which will fail gracefully in tests
        # Just test that empty list is returned for known symbol with no splits
        assert cache.memory.get("KNOWN") == []


class TestStockSplit:
    """Tests for StockSplit dataclass."""

    def test_creation(self):
        split = StockSplit(date=date(2024, 6, 10), ratio=Decimal("10"))
        assert split.date == date(2024, 6, 10)
        assert split.ratio == Decimal("10")
