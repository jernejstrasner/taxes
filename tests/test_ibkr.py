"""Tests for IBKR Flex Query XML parser."""

import datetime
import tempfile
import os
import pytest

from ibkr import parse_ibkr_date, process_ibkr_xml, ibkr_trades_to_kdvp, IBKRTrade
from gains import KDVPSecurityOpen, KDVPSecurityClose


class TestParseIBKRDate:
    """Tests for IBKR date format parsing."""

    def test_standard_date(self):
        assert parse_ibkr_date("20240115") == datetime.date(2024, 1, 15)

    def test_year_boundary(self):
        assert parse_ibkr_date("20231231") == datetime.date(2023, 12, 31)
        assert parse_ibkr_date("20240101") == datetime.date(2024, 1, 1)


class TestProcessIBKRXML:
    """Tests for IBKR XML parsing."""

    def test_parse_single_buy_trade(self):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Tax" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U12345" fromDate="20240101" toDate="20241231">
<Trades>
<Trade accountId="U12345" currency="EUR" assetCategory="STK" subCategory="ETF"
       symbol="VUAA" isin="IE00BFMXXD54" tradeDate="20240315"
       quantity="10" tradePrice="100.50" buySell="BUY" />
</Trades>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            f.flush()
            try:
                trades = process_ibkr_xml(f.name)
                assert len(trades) == 1
                trade = trades[0]
                assert trade.symbol == "VUAA"
                assert trade.isin == "IE00BFMXXD54"
                assert trade.trade_date == datetime.date(2024, 3, 15)
                assert trade.quantity == 10.0
                assert trade.price == 100.50
                assert trade.is_buy is True
                assert trade.is_etf is True
            finally:
                os.unlink(f.name)

    def test_parse_sell_trade(self):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Tax" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U12345" fromDate="20240101" toDate="20241231">
<Trades>
<Trade accountId="U12345" currency="EUR" assetCategory="STK" subCategory=""
       symbol="AAPL" isin="US0378331005" tradeDate="20240415"
       quantity="-5" tradePrice="175.00" buySell="SELL" />
</Trades>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            f.flush()
            try:
                trades = process_ibkr_xml(f.name)
                assert len(trades) == 1
                trade = trades[0]
                assert trade.symbol == "AAPL"
                assert trade.is_buy is False
                assert trade.is_etf is False
                assert trade.quantity == 5.0  # Should be absolute value
            finally:
                os.unlink(f.name)

    def test_skip_non_stock_trades(self):
        """Options and other non-STK assets should be skipped."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Tax" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U12345" fromDate="20240101" toDate="20241231">
<Trades>
<Trade accountId="U12345" currency="EUR" assetCategory="OPT" subCategory=""
       symbol="AAPL 240315C00150000" isin="" tradeDate="20240115"
       quantity="1" tradePrice="5.00" buySell="BUY" />
<Trade accountId="U12345" currency="EUR" assetCategory="STK" subCategory=""
       symbol="AAPL" isin="US0378331005" tradeDate="20240115"
       quantity="10" tradePrice="150.00" buySell="BUY" />
</Trades>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            f.flush()
            try:
                trades = process_ibkr_xml(f.name)
                assert len(trades) == 1
                assert trades[0].symbol == "AAPL"
            finally:
                os.unlink(f.name)

    def test_multiple_trades(self):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Tax" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U12345" fromDate="20240101" toDate="20241231">
<Trades>
<Trade accountId="U12345" currency="EUR" assetCategory="STK" subCategory=""
       symbol="AAPL" isin="US0378331005" tradeDate="20240115"
       quantity="10" tradePrice="150.00" buySell="BUY" />
<Trade accountId="U12345" currency="EUR" assetCategory="STK" subCategory=""
       symbol="MSFT" isin="US5949181045" tradeDate="20240116"
       quantity="5" tradePrice="400.00" buySell="BUY" />
<Trade accountId="U12345" currency="EUR" assetCategory="STK" subCategory=""
       symbol="AAPL" isin="US0378331005" tradeDate="20240215"
       quantity="-10" tradePrice="160.00" buySell="SELL" />
</Trades>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            f.flush()
            try:
                trades = process_ibkr_xml(f.name)
                assert len(trades) == 3
                assert trades[0].symbol == "AAPL"
                assert trades[0].is_buy is True
                assert trades[1].symbol == "MSFT"
                assert trades[2].symbol == "AAPL"
                assert trades[2].is_buy is False
            finally:
                os.unlink(f.name)

    def test_usd_currency_error(self):
        """USD trades should raise an error until currency conversion is implemented."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Tax" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U12345" fromDate="20240101" toDate="20241231">
<Trades>
<Trade accountId="U12345" currency="USD" assetCategory="STK" subCategory=""
       symbol="AAPL" isin="US0378331005" tradeDate="20240115"
       quantity="10" tradePrice="150.00" buySell="BUY" />
</Trades>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            f.flush()
            try:
                with pytest.raises(SystemExit):
                    process_ibkr_xml(f.name)
            finally:
                os.unlink(f.name)

    def test_missing_isin_error(self):
        """Trades without ISIN should raise an error."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Tax" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U12345" fromDate="20240101" toDate="20241231">
<Trades>
<Trade accountId="U12345" currency="EUR" assetCategory="STK" subCategory=""
       symbol="AAPL" isin="" tradeDate="20240115"
       quantity="10" tradePrice="150.00" buySell="BUY" />
</Trades>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            f.flush()
            try:
                with pytest.raises(SystemExit):
                    process_ibkr_xml(f.name)
            finally:
                os.unlink(f.name)

    def test_empty_trades_section(self):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Tax" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U12345" fromDate="20240101" toDate="20241231">
<Trades>
</Trades>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            f.flush()
            try:
                trades = process_ibkr_xml(f.name)
                assert len(trades) == 0
            finally:
                os.unlink(f.name)

    def test_file_not_found(self):
        with pytest.raises(SystemExit):
            process_ibkr_xml("/nonexistent/path/to/file.xml")


class TestIBKRTradesToKDVP:
    """Tests for converting IBKR trades to KDVP domain objects."""

    def test_buy_trade_conversion(self):
        trades = [IBKRTrade(
            symbol="VUAA",
            isin="IE00BFMXXD54",
            trade_date=datetime.date(2024, 3, 15),
            quantity=10.0,
            price=100.50,
            is_buy=True,
            is_etf=True,
        )]

        result = ibkr_trades_to_kdvp(trades)
        assert len(result) == 1

        symbol, trade, is_fond = result[0]
        assert symbol == "VUAA"
        assert isinstance(trade, KDVPSecurityOpen)
        assert trade.date == datetime.date(2024, 3, 15)
        assert trade.quantity == 10.0
        assert trade.value == 100.50
        assert trade.acquisition_type == "A"
        assert is_fond is True

    def test_sell_trade_conversion(self):
        trades = [IBKRTrade(
            symbol="AAPL",
            isin="US0378331005",
            trade_date=datetime.date(2024, 4, 15),
            quantity=5.0,
            price=175.00,
            is_buy=False,
            is_etf=False,
        )]

        result = ibkr_trades_to_kdvp(trades)
        assert len(result) == 1

        symbol, trade, is_fond = result[0]
        assert symbol == "AAPL"
        assert isinstance(trade, KDVPSecurityClose)
        assert trade.date == datetime.date(2024, 4, 15)
        assert trade.quantity == 5.0
        assert trade.value == 175.00
        assert is_fond is False

    def test_multiple_trades_conversion(self):
        trades = [
            IBKRTrade("AAPL", "US0378331005", datetime.date(2024, 1, 15), 10.0, 150.0, True, False),
            IBKRTrade("AAPL", "US0378331005", datetime.date(2024, 2, 15), 10.0, 160.0, False, False),
        ]

        result = ibkr_trades_to_kdvp(trades)
        assert len(result) == 2

        # First is buy (Open)
        assert isinstance(result[0][1], KDVPSecurityOpen)
        # Second is sell (Close)
        assert isinstance(result[1][1], KDVPSecurityClose)

    def test_fractional_shares(self):
        trades = [IBKRTrade(
            symbol="VUAA",
            isin="IE00BFMXXD54",
            trade_date=datetime.date(2024, 3, 15),
            quantity=0.5,
            price=100.50,
            is_buy=True,
            is_etf=True,
        )]

        result = ibkr_trades_to_kdvp(trades)
        assert result[0][1].quantity == 0.5
