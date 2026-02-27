"""Tests for lots.py replacement logic."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from lot_parser import HistoricalLot
from lots import (
    LotVerifier,
    COST_BASIS_TOLERANCE,
    replace_lots_from_historical,
    resolve_symbol,
    SYMBOL_ALIASES,
)
from split_cache import StockSplit


class TestLotVerifier:
    """Tests for LotVerifier core matching."""

    @pytest.fixture
    def mock_lots_directory(self, tmp_path):
        """Create mock lot files."""
        shop_content = '''"SHOP Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"10/30/2017 00:00:00","8","$893.34","$108.98","$7,146.72","$871.84","$6,274.88","+719.73%","Long Term",
"07/11/2017 00:00:00","2","$893.34","$91.45","$1,786.68","$182.90","$1,603.78","+876.86%","Long Term",
"Total","10","--","--","$8,933.40","$1,054.74","$7,878.66","+746.96%","--",'''

        (tmp_path / "Lot-Details-SHOP.CSV").write_text(shop_content)
        return str(tmp_path)

    @pytest.fixture
    def verifier(self, mock_lots_directory):
        """Create a LotVerifier with mocked split cache."""
        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            mock_cache.get_splits_in_range.return_value = []
            MockSplitCache.return_value = mock_cache
            v = LotVerifier(mock_lots_directory)
            v.split_cache = mock_cache
            return v

    def test_find_matching_lot_exact_match(self, verifier):
        """Should find lot when cost basis matches exactly."""
        matched, _ = verifier.find_matching_lot(
            symbol="SHOP",
            cost_basis=Decimal("871.84"),
            close_date=date(2024, 1, 1),
        )

        assert matched is not None
        assert matched.original.open_date == date(2017, 10, 30)
        assert matched.original.quantity == Decimal("8")

    def test_find_matching_lot_within_tolerance(self, verifier):
        """Should find lot when cost basis is within tolerance."""
        matched, _ = verifier.find_matching_lot(
            symbol="SHOP",
            cost_basis=Decimal("871.84") + COST_BASIS_TOLERANCE - Decimal("0.01"),
            close_date=date(2024, 1, 1),
        )

        assert matched is not None
        assert matched.original.open_date == date(2017, 10, 30)

    def test_find_matching_lot_no_match(self, verifier):
        """Should return None when no lot matches."""
        matched, _ = verifier.find_matching_lot(
            symbol="SHOP",
            cost_basis=Decimal("9999.99"),
            close_date=date(2024, 1, 1),
        )

        assert matched is None

    def test_find_matching_lot_unknown_symbol(self, verifier):
        """Should return None with message for unknown symbol."""
        matched, messages = verifier.find_matching_lot(
            symbol="UNKNOWN",
            cost_basis=Decimal("100.00"),
            close_date=date(2024, 1, 1),
        )

        assert matched is None
        assert any("No historical lots" in m for m in messages)


class TestGetReplacementLots:
    """Tests for get_replacement_lots() unconditional replacement."""

    @pytest.fixture
    def mock_lots_directory(self, tmp_path):
        shop_content = '''"SHOP Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"10/30/2017 00:00:00","8","$893.34","$108.98","$7,146.72","$871.84","$6,274.88","+719.73%","Long Term",
"07/11/2017 00:00:00","2","$893.34","$91.45","$1,786.68","$182.90","$1,603.78","+876.86%","Long Term",
"Total","10","--","--","$8,933.40","$1,054.74","$7,878.66","+746.96%","--",'''

        (tmp_path / "Lot-Details-SHOP.CSV").write_text(shop_content)
        return str(tmp_path)

    @pytest.fixture
    def verifier(self, mock_lots_directory):
        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            mock_cache.get_splits_in_range.return_value = []
            MockSplitCache.return_value = mock_cache
            v = LotVerifier(mock_lots_directory)
            v.split_cache = mock_cache
            return v

    def test_single_lot_always_replaces(self, verifier):
        """Even when Saxo dates match, historical data should be returned."""
        # Cost basis = 8 * 108.98 = 871.84
        lots, is_merged, messages = verifier.get_replacement_lots(
            symbol="SHOP",
            cost_basis=Decimal("871.84"),
            close_date=date(2024, 1, 1),
        )

        assert lots is not None
        assert len(lots) == 1
        assert is_merged is False
        assert lots[0].original.open_date == date(2017, 10, 30)
        assert lots[0].original.quantity == Decimal("8")
        assert lots[0].adjusted_quantity == Decimal("8")
        assert lots[0].adjusted_cost_per_share == Decimal("108.98")

    def test_single_lot_split_adjusted(self, tmp_path):
        """Split-adjusted qty/price should be returned for single lot."""
        content = '''"NVDA Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"07/11/2017 00:00:00","8","$258.24","$38.21","$2,065.92","$305.68","$1,760.26","+575.89%","Long Term",
"Total","8","--","--","$2,065.92","$305.68","$1,760.26","+575.89%","--",'''

        (tmp_path / "Lot-Details-NVDA.CSV").write_text(content)

        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            mock_cache.get_splits_in_range.return_value = [
                StockSplit(date=date(2024, 6, 10), ratio=Decimal("10"))
            ]
            MockSplitCache.return_value = mock_cache
            v = LotVerifier(str(tmp_path))
            v.split_cache = mock_cache

        lots, is_merged, messages = v.get_replacement_lots(
            symbol="NVDA",
            cost_basis=Decimal("305.68"),
            close_date=date(2024, 12, 1),
        )

        assert lots is not None
        assert len(lots) == 1
        assert lots[0].adjusted_quantity == Decimal("80")  # 8 * 10
        assert lots[0].adjusted_cost_per_share == Decimal("3.821")  # 38.21 / 10
        assert lots[0].original.open_date == date(2017, 7, 11)

    def test_unmatched_returns_none(self, verifier):
        """No match should return None."""
        lots, is_merged, messages = verifier.get_replacement_lots(
            symbol="SHOP",
            cost_basis=Decimal("9999.99"),
            close_date=date(2024, 1, 1),
        )

        assert lots is None
        assert is_merged is False


class TestMergedLotMatching:
    """Tests for merged lot detection and expansion."""

    @pytest.fixture
    def multi_lot_dir(self, tmp_path):
        shop_content = '''"SHOP Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"10/30/2017 00:00:00","8","$893.34","$108.98","$7,146.72","$871.84","$6,274.88","+719.73%","Long Term",
"07/11/2017 00:00:00","2","$893.34","$91.45","$1,786.68","$182.90","$1,603.78","+876.86%","Long Term",
"06/15/2015 00:00:00","50","$893.34","$36.69","$44,667.00","$1,834.50","$42,832.50","+2,334.83%","Long Term",
"03/22/2018 00:00:00","10","$893.34","$149.95","$8,933.40","$1,499.47","$7,433.93","+495.77%","Long Term",
"Total","70","--","--","$62,533.80","$4,388.71","$58,145.09","+1,324.88%","--",'''

        (tmp_path / "Lot-Details-SHOP.CSV").write_text(shop_content)
        return str(tmp_path)

    @pytest.fixture
    def verifier_multi(self, multi_lot_dir):
        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            mock_cache.get_splits_in_range.return_value = []
            MockSplitCache.return_value = mock_cache
            v = LotVerifier(multi_lot_dir)
            v.split_cache = mock_cache
            return v

    def test_detect_merged_lots(self, verifier_multi):
        """Should detect merged lots and return expanded individual lots."""
        # Sum of all SHOP lots: $871.84 + $182.90 + $1834.50 + $1499.47 = $4388.71
        lots, is_merged, messages = verifier_multi.get_replacement_lots(
            symbol="SHOP",
            cost_basis=Decimal("4388.72"),  # 70 * 62.696 ≈ 4388.72
            close_date=date(2025, 5, 1),
        )

        assert lots is not None
        assert is_merged is True
        assert len(lots) == 4
        assert any("expanding merged lot" in m for m in messages)

    def test_merged_lots_expanded_with_splits(self, tmp_path):
        """Merged lots should each be individually split-adjusted."""
        content = '''"TEST Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"01/15/2020 00:00:00","10","$50.00","$50.00","$500.00","$500.00","$0.00","0.00%","Long Term",
"06/20/2020 00:00:00","5","$80.00","$80.00","$400.00","$400.00","$0.00","0.00%","Long Term",
"Total","15","--","--","$900.00","$900.00","$0.00","0.00%","--",'''

        (tmp_path / "Lot-Details-TEST.CSV").write_text(content)

        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            # 2:1 split in 2023 applies to both lots
            mock_cache.get_splits_in_range.return_value = [
                StockSplit(date=date(2023, 1, 15), ratio=Decimal("2"))
            ]
            MockSplitCache.return_value = mock_cache
            v = LotVerifier(str(tmp_path))
            v.split_cache = mock_cache

        # Total cost basis = $500 + $400 = $900
        lots, is_merged, messages = v.get_replacement_lots(
            symbol="TEST",
            cost_basis=Decimal("900.00"),
            close_date=date(2024, 1, 1),
        )

        assert lots is not None
        assert is_merged is True
        assert len(lots) == 2

        # Sort by original date for predictable assertion
        lots_sorted = sorted(lots, key=lambda x: x.original.open_date)

        # First lot: 10 shares * 2 = 20, $50/share / 2 = $25
        assert lots_sorted[0].adjusted_quantity == Decimal("20")
        assert lots_sorted[0].adjusted_cost_per_share == Decimal("25")
        assert lots_sorted[0].original.open_date == date(2020, 1, 15)

        # Second lot: 5 shares * 2 = 10, $80/share / 2 = $40
        assert lots_sorted[1].adjusted_quantity == Decimal("10")
        assert lots_sorted[1].adjusted_cost_per_share == Decimal("40")
        assert lots_sorted[1].original.open_date == date(2020, 6, 20)

    def test_no_merge_for_single_lot(self, verifier_multi):
        """Should not report merge for single lot match."""
        # Match just one lot: $871.84
        lots, is_merged, messages = verifier_multi.get_replacement_lots(
            symbol="SHOP",
            cost_basis=Decimal("871.84"),
            close_date=date(2025, 5, 1),
        )

        assert lots is not None
        assert is_merged is False
        assert len(lots) == 1


class TestAdjustForSplits:
    """Tests for split adjustment logic."""

    @pytest.fixture
    def verifier_with_splits(self, tmp_path):
        content = '''"NVDA Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"07/11/2017 00:00:00","8","$258.24","$38.21","$2,065.92","$305.68","$1,760.26","+575.89%","Long Term",
"Total","8","--","--","$2,065.92","$305.68","$1,760.26","+575.89%","--",'''

        (tmp_path / "Lot-Details-NVDA.CSV").write_text(content)

        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            mock_cache.get_splits_in_range.return_value = [
                StockSplit(date=date(2024, 6, 10), ratio=Decimal("10"))
            ]
            MockSplitCache.return_value = mock_cache
            v = LotVerifier(str(tmp_path))
            v.split_cache = mock_cache
            return v

    def test_adjust_quantity_for_split(self, verifier_with_splits):
        """Quantity should be multiplied by split ratio."""
        lot = HistoricalLot(
            symbol="NVDA",
            open_date=date(2017, 7, 11),
            quantity=Decimal("8"),
            cost_per_share=Decimal("38.21"),
            cost_basis=Decimal("305.68"),
        )

        adjusted = verifier_with_splits.adjust_for_splits(lot, date(2024, 12, 1))

        assert adjusted.adjusted_quantity == Decimal("80")
        assert adjusted.adjusted_cost_per_share == Decimal("3.821")
        assert adjusted.original.quantity == Decimal("8")
        assert len(adjusted.splits_applied) == 1


class TestReplacLotsFromHistorical:
    """Integration tests for replace_lots_from_historical()."""

    def _make_df(self, rows):
        """Build a DataFrame matching Saxo ClosedPositions schema."""
        return pd.DataFrame(rows)

    def test_single_lot_replacement(self, tmp_path):
        """Single matched lot should replace open-side data."""
        content = '''"SHOP Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"10/30/2017 00:00:00","8","$893.34","$108.98","$7,146.72","$871.84","$6,274.88","+719.73%","Long Term",
"Total","8","--","--","$7,146.72","$871.84","$6,274.88","+719.73%","--",'''

        (tmp_path / "Lot-Details-SHOP.CSV").write_text(content)

        df = self._make_df([{
            "Instrument Symbol": "SHOP:xnas",
            "Trade Date Open": pd.Timestamp("2017-10-30"),
            "Quantity Open": 8.0,
            "Open Price": 108.98,
            "Trade Date Close": pd.Timestamp("2024-06-01"),
            "Close Price": 200.0,
            "QuantityClose": 8.0,
            "OpenPositionId": "OP1",
            "ClosePositionId": "CP1",
            "Instrument currency": "USD",
            "PnLAccountCurrency": 500.0,
        }])

        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            mock_cache.get_splits_in_range.return_value = []
            MockSplitCache.return_value = mock_cache

            result = replace_lots_from_historical(str(tmp_path), df)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["Trade Date Open"] == pd.Timestamp("2017-10-30")
        assert row["Quantity Open"] == 8.0
        assert row["Open Price"] == 108.98
        assert row["QuantityClose"] == 8.0
        # Close-side data unchanged
        assert row["Close Price"] == 200.0

    def test_split_adjusted_replacement(self, tmp_path):
        """Matched lot should use split-adjusted qty/price."""
        content = '''"NVDA Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"07/11/2017 00:00:00","8","$258.24","$38.21","$2,065.92","$305.68","$1,760.26","+575.89%","Long Term",
"Total","8","--","--","$2,065.92","$305.68","$1,760.26","+575.89%","--",'''

        (tmp_path / "Lot-Details-NVDA.CSV").write_text(content)

        # Saxo shows post-split data: 80 shares at $3.821 (cost basis 305.68)
        df = self._make_df([{
            "Instrument Symbol": "NVDA:xnas",
            "Trade Date Open": pd.Timestamp("2017-07-11"),
            "Quantity Open": 80.0,
            "Open Price": 3.821,
            "Trade Date Close": pd.Timestamp("2024-12-01"),
            "Close Price": 150.0,
            "QuantityClose": 80.0,
            "OpenPositionId": "OP1",
            "ClosePositionId": "CP1",
            "Instrument currency": "USD",
            "PnLAccountCurrency": 5000.0,
        }])

        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            # 10:1 split
            mock_cache.get_splits_in_range.return_value = [
                StockSplit(date=date(2024, 6, 10), ratio=Decimal("10"))
            ]
            MockSplitCache.return_value = mock_cache

            result = replace_lots_from_historical(str(tmp_path), df)

        assert len(result) == 1
        row = result.iloc[0]
        # Historical: 8 shares at $38.21, after 10:1 split -> 80 shares at $3.821
        assert row["Quantity Open"] == 80.0
        assert row["Open Price"] == pytest.approx(3.821)
        assert row["QuantityClose"] == 80.0
        assert row["Trade Date Open"] == pd.Timestamp("2017-07-11")

    def test_unmatched_row_passes_through(self, tmp_path):
        """Rows without historical lots should be unchanged."""
        content = '''"SHOP Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"10/30/2017 00:00:00","8","$893.34","$108.98","$7,146.72","$871.84","$6,274.88","+719.73%","Long Term",
"Total","8","--","--","$7,146.72","$871.84","$6,274.88","+719.73%","--",'''

        (tmp_path / "Lot-Details-SHOP.CSV").write_text(content)

        # AAPL is not in historical lots
        df = self._make_df([{
            "Instrument Symbol": "AAPL:xnas",
            "Trade Date Open": pd.Timestamp("2020-01-15"),
            "Quantity Open": 10.0,
            "Open Price": 300.0,
            "Trade Date Close": pd.Timestamp("2024-06-01"),
            "Close Price": 400.0,
            "QuantityClose": 10.0,
            "OpenPositionId": "OP1",
            "ClosePositionId": "CP1",
            "Instrument currency": "USD",
            "PnLAccountCurrency": 1000.0,
        }])

        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            mock_cache.get_splits_in_range.return_value = []
            MockSplitCache.return_value = mock_cache

            result = replace_lots_from_historical(str(tmp_path), df)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["Quantity Open"] == 10.0
        assert row["Open Price"] == 300.0
        assert row["Trade Date Open"] == pd.Timestamp("2020-01-15")

    def test_merged_lots_expand_to_multiple_rows(self, tmp_path):
        """Merged lots should expand into individual rows with split-adjusted data."""
        content = '''"TEST Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"01/15/2020 00:00:00","10","$50.00","$50.00","$500.00","$500.00","$0.00","0.00%","Long Term",
"06/20/2020 00:00:00","5","$80.00","$80.00","$400.00","$400.00","$0.00","0.00%","Long Term",
"Total","15","--","--","$900.00","$900.00","$0.00","0.00%","--",'''

        (tmp_path / "Lot-Details-TEST.CSV").write_text(content)

        # Broker merged: 15 shares at $60/share = $900 cost basis
        df = self._make_df([{
            "Instrument Symbol": "TEST:xnas",
            "Trade Date Open": pd.Timestamp("2020-03-01"),
            "Quantity Open": 15.0,
            "Open Price": 60.0,
            "Trade Date Close": pd.Timestamp("2024-06-01"),
            "Close Price": 100.0,
            "QuantityClose": 15.0,
            "OpenPositionId": "OP1",
            "ClosePositionId": "CP1",
            "Instrument currency": "USD",
            "PnLAccountCurrency": 600.0,
        }])

        with patch("lots.SplitCache") as MockSplitCache:
            mock_cache = MagicMock()
            mock_cache.get_splits_in_range.return_value = []
            MockSplitCache.return_value = mock_cache

            result = replace_lots_from_historical(str(tmp_path), df)

        assert len(result) == 2
        result = result.sort_values("Trade Date Open").reset_index(drop=True)

        # Lot 1: 10 shares at $50
        assert result.iloc[0]["Trade Date Open"] == pd.Timestamp("2020-01-15")
        assert result.iloc[0]["Quantity Open"] == 10.0
        assert result.iloc[0]["Open Price"] == pytest.approx(50.0)
        assert result.iloc[0]["QuantityClose"] == 10.0

        # Lot 2: 5 shares at $80
        assert result.iloc[1]["Trade Date Open"] == pd.Timestamp("2020-06-20")
        assert result.iloc[1]["Quantity Open"] == 5.0
        assert result.iloc[1]["Open Price"] == pytest.approx(80.0)
        assert result.iloc[1]["QuantityClose"] == 5.0

        # Close-side data preserved
        assert result.iloc[0]["Close Price"] == 100.0
        assert result.iloc[1]["Close Price"] == 100.0

        # Unique IDs for expanded lots
        assert result.iloc[0]["OpenPositionId"] != result.iloc[1]["OpenPositionId"]


class TestSymbolAliases:
    """Tests for symbol alias resolution."""

    def test_resolve_known_alias(self):
        assert resolve_symbol("SHOP_NEW") == "SHOP"
        assert resolve_symbol("META") == "FB"

    def test_resolve_unknown_symbol_unchanged(self):
        assert resolve_symbol("AAPL") == "AAPL"
        assert resolve_symbol("TSLA") == "TSLA"

    def test_aliases_defined(self):
        """Verify expected aliases are in the mapping."""
        assert "SHOP_NEW" in SYMBOL_ALIASES
        assert "META" in SYMBOL_ALIASES
