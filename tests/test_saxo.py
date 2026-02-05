"""Tests for Saxo Bank close position deduplication."""
import datetime

import pandas as pd
import pytest

from gains import DohKDVP, KDVPSecurityOpen, KDVPSecurityClose
from saxobank import saxo_trades_to_kdvp


def make_saxo_df(rows: list[dict]) -> pd.DataFrame:
    """Build a DataFrame mimicking processed Saxo ClosedPositions rows."""
    df = pd.DataFrame(rows)
    # Match the types that process_row produces
    df["Trade Date Open"] = pd.to_datetime(df["Trade Date Open"])
    df["Trade Date Close"] = pd.to_datetime(df["Trade Date Close"])
    return df


class TestSaxoCloseDeduplication:
    """Tests for grouping close trades by ClosePositionId."""

    def test_single_lot_close(self):
        """A simple single-lot close should produce one open and one close."""
        df = make_saxo_df([{
            "Trade Date Open": "2024-01-15",
            "Trade Date Close": "2024-06-15",
            "QuantityOpen": 100,
            "QuantityClose": 100,
            "Open Price": 150.0,
            "Close Price": 160.0,
            "Symbol": "AAPL",
            "Asset type": "Stock",
            "ClosePositionId": 1001,
            "OpenPositionId": 2001,
            "Gain": 1000.0,
        }])

        kdvp = DohKDVP()
        saxo_trades_to_kdvp(df, kdvp)

        item = kdvp.items["AAPL"]
        assert len(item.securities) == 2
        assert isinstance(item.securities[0], KDVPSecurityOpen)
        assert isinstance(item.securities[1], KDVPSecurityClose)
        assert item.securities[0].quantity == 100
        assert item.securities[1].quantity == 100
        assert item.securities[1].stock == 0

    def test_multi_lot_same_close_id(self):
        """Two lots closed by one sell should produce two opens and one close."""
        df = make_saxo_df([
            {
                "Trade Date Open": "2024-04-08",
                "Trade Date Close": "2025-01-03",
                "QuantityOpen": 71,
                "QuantityClose": 136,
                "Open Price": 70.09,
                "Close Price": 78.50,
                "Symbol": "XDPD",
                "Asset type": "Etf",
                "ClosePositionId": 6117617660,
                "OpenPositionId": 5864212530,
                "Gain": 597.0,
            },
            {
                "Trade Date Open": "2024-07-15",
                "Trade Date Close": "2025-01-03",
                "QuantityOpen": 65,
                "QuantityClose": 136,
                "Open Price": 75.74,
                "Close Price": 78.50,
                "Symbol": "XDPD",
                "Asset type": "Etf",
                "ClosePositionId": 6117617660,
                "OpenPositionId": 5956965426,
                "Gain": 179.0,
            },
        ])

        kdvp = DohKDVP()
        saxo_trades_to_kdvp(df, kdvp)

        item = kdvp.items["XDPD"]
        opens = [s for s in item.securities if isinstance(s, KDVPSecurityOpen)]
        closes = [s for s in item.securities if isinstance(s, KDVPSecurityClose)]

        assert len(opens) == 2
        assert len(closes) == 1
        assert opens[0].quantity == 71
        assert opens[1].quantity == 65
        assert closes[0].quantity == 136
        # Running total: 71 + 65 - 136 = 0
        assert closes[0].stock == 0

    def test_separate_close_ids_not_merged(self):
        """Different ClosePositionIds should produce separate close trades."""
        df = make_saxo_df([
            {
                "Trade Date Open": "2023-11-02",
                "Trade Date Close": "2025-10-07",
                "QuantityOpen": 7,
                "QuantityClose": 7,
                "Open Price": 596.30,
                "Close Price": 840.00,
                "Symbol": "ASML",
                "Asset type": "Stock",
                "ClosePositionId": 6432513912,
                "OpenPositionId": 5725875004,
                "Gain": 1705.60,
            },
            {
                "Trade Date Open": "2023-07-12",
                "Trade Date Close": "2025-10-08",
                "QuantityOpen": 15,
                "QuantityClose": 15,
                "Open Price": 646.20,
                "Close Price": 842.50,
                "Symbol": "ASML",
                "Asset type": "Stock",
                "ClosePositionId": 6432513914,
                "OpenPositionId": 5629909143,
                "Gain": 2944.50,
            },
        ])

        kdvp = DohKDVP()
        saxo_trades_to_kdvp(df, kdvp)

        item = kdvp.items["ASML"]
        opens = [s for s in item.securities if isinstance(s, KDVPSecurityOpen)]
        closes = [s for s in item.securities if isinstance(s, KDVPSecurityClose)]

        # Two separate sells (different dates/prices) produce two close trades
        assert len(opens) == 2
        assert len(closes) == 2

    def test_is_fond_for_etf(self):
        """ETFs should be marked as fond, stocks should not."""
        df = make_saxo_df([
            {
                "Trade Date Open": "2024-01-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 100,
                "QuantityClose": 100,
                "Open Price": 50.0,
                "Close Price": 55.0,
                "Symbol": "XDPD",
                "Asset type": "Etf",
                "ClosePositionId": 1001,
                "OpenPositionId": 2001,
                "Gain": 500.0,
            },
            {
                "Trade Date Open": "2024-01-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 10,
                "QuantityClose": 10,
                "Open Price": 150.0,
                "Close Price": 160.0,
                "Symbol": "AAPL",
                "Asset type": "Stock",
                "ClosePositionId": 1002,
                "OpenPositionId": 2002,
                "Gain": 100.0,
            },
        ])

        kdvp = DohKDVP()
        saxo_trades_to_kdvp(df, kdvp)

        assert kdvp.items["XDPD"].is_fond is True
        assert kdvp.items["AAPL"].is_fond is False

    def test_loss_transfer_from_total_gain(self):
        """loss_transfer should be based on summed gain across lots."""
        df = make_saxo_df([
            {
                "Trade Date Open": "2024-01-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 50,
                "QuantityClose": 100,
                "Open Price": 160.0,
                "Close Price": 150.0,
                "Symbol": "LOSE",
                "Asset type": "Stock",
                "ClosePositionId": 1001,
                "OpenPositionId": 2001,
                "Gain": -500.0,
            },
            {
                "Trade Date Open": "2024-02-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 50,
                "QuantityClose": 100,
                "Open Price": 155.0,
                "Close Price": 150.0,
                "Symbol": "LOSE",
                "Asset type": "Stock",
                "ClosePositionId": 1001,
                "OpenPositionId": 2002,
                "Gain": -250.0,
            },
        ])

        kdvp = DohKDVP()
        saxo_trades_to_kdvp(df, kdvp)

        closes = [s for s in kdvp.items["LOSE"].securities
                  if isinstance(s, KDVPSecurityClose)]
        assert len(closes) == 1
        assert closes[0].loss_transfer == True

    def test_mixed_gain_loss_lots_net_positive(self):
        """When one lot gains and another loses, net positive means no loss transfer."""
        df = make_saxo_df([
            {
                "Trade Date Open": "2024-01-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 50,
                "QuantityClose": 100,
                "Open Price": 140.0,
                "Close Price": 150.0,
                "Symbol": "MIX",
                "Asset type": "Stock",
                "ClosePositionId": 1001,
                "OpenPositionId": 2001,
                "Gain": 500.0,
            },
            {
                "Trade Date Open": "2024-02-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 50,
                "QuantityClose": 100,
                "Open Price": 155.0,
                "Close Price": 150.0,
                "Symbol": "MIX",
                "Asset type": "Stock",
                "ClosePositionId": 1001,
                "OpenPositionId": 2002,
                "Gain": -250.0,
            },
        ])

        kdvp = DohKDVP()
        saxo_trades_to_kdvp(df, kdvp)

        closes = [s for s in kdvp.items["MIX"].securities
                  if isinstance(s, KDVPSecurityClose)]
        assert len(closes) == 1
        assert closes[0].loss_transfer == False


class TestSaxoCloseQuantityValidation:
    """Tests for sanity check on inconsistent QuantityClose."""

    def test_inconsistent_close_quantities_exits(self):
        """Rows with same ClosePositionId but different QuantityClose should error."""
        df = make_saxo_df([
            {
                "Trade Date Open": "2024-01-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 50,
                "QuantityClose": 100,
                "Open Price": 150.0,
                "Close Price": 160.0,
                "Symbol": "BAD",
                "Asset type": "Stock",
                "ClosePositionId": 1001,
                "OpenPositionId": 2001,
                "Gain": 500.0,
            },
            {
                "Trade Date Open": "2024-02-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 50,
                "QuantityClose": 90,  # Different from 100 above
                "Open Price": 155.0,
                "Close Price": 160.0,
                "Symbol": "BAD",
                "Asset type": "Stock",
                "ClosePositionId": 1001,
                "OpenPositionId": 2002,
                "Gain": 250.0,
            },
        ])

        kdvp = DohKDVP()
        with pytest.raises(SystemExit):
            saxo_trades_to_kdvp(df, kdvp)

    def test_consistent_close_quantities_ok(self):
        """Rows with same ClosePositionId and same QuantityClose should not error."""
        df = make_saxo_df([
            {
                "Trade Date Open": "2024-01-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 50,
                "QuantityClose": 100,
                "Open Price": 150.0,
                "Close Price": 160.0,
                "Symbol": "OK",
                "Asset type": "Stock",
                "ClosePositionId": 1001,
                "OpenPositionId": 2001,
                "Gain": 500.0,
            },
            {
                "Trade Date Open": "2024-02-15",
                "Trade Date Close": "2024-06-15",
                "QuantityOpen": 50,
                "QuantityClose": 100,
                "Open Price": 155.0,
                "Close Price": 160.0,
                "Symbol": "OK",
                "Asset type": "Stock",
                "ClosePositionId": 1001,
                "OpenPositionId": 2002,
                "Gain": 250.0,
            },
        ])

        kdvp = DohKDVP()
        saxo_trades_to_kdvp(df, kdvp)  # Should not raise
