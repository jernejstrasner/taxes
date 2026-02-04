"""Tests for capital gains calculation and stock tracking."""
import datetime
from gains import KDVPItem, KDVPSecurityOpen, KDVPSecurityClose, DohKDVP


class TestKDVPItemStockTracking:
    """Tests for running stock position calculation."""

    def test_single_open_trade(self):
        item = KDVPItem("AAPL", False, [])
        trade = KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        )
        item.add_trade(trade)

        assert len(item.securities) == 1
        assert item.securities[0].stock == 100

    def test_single_close_trade(self):
        item = KDVPItem("AAPL", False, [])
        # First open position
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        # Then close position
        item.add_trade(KDVPSecurityClose(
            date=datetime.date(2024, 2, 15),
            quantity=50,
            value=160.0,
            stock=0,
            loss_transfer=False
        ))

        assert len(item.securities) == 2
        assert item.securities[0].stock == 100  # After open
        assert item.securities[1].stock == 50   # After partial close

    def test_multiple_opens_accumulate(self):
        item = KDVPItem("AAPL", False, [])
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 2, 15),
            quantity=50,
            value=155.0,
            stock=0,
            acquisition_type="A"
        ))

        assert item.securities[0].stock == 100
        assert item.securities[1].stock == 150

    def test_full_close_results_in_zero_stock(self):
        item = KDVPItem("AAPL", False, [])
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        item.add_trade(KDVPSecurityClose(
            date=datetime.date(2024, 2, 15),
            quantity=100,
            value=160.0,
            stock=0,
            loss_transfer=False
        ))

        assert item.securities[1].stock == 0

    def test_trades_sorted_by_date(self):
        item = KDVPItem("AAPL", False, [])
        # Add trades out of order
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 3, 15),
            quantity=50,
            value=155.0,
            stock=0,
            acquisition_type="A"
        ))
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))

        # Should be sorted chronologically
        assert item.securities[0].date == datetime.date(2024, 1, 15)
        assert item.securities[1].date == datetime.date(2024, 3, 15)
        # Stock should be recalculated in correct order
        assert item.securities[0].stock == 100
        assert item.securities[1].stock == 150


class TestKDVPItemTradeMerging:
    """Tests for merging trades with same date/price/type."""

    def test_merge_same_date_price_type(self):
        item = KDVPItem("AAPL", False, [])
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        # Same date, price, and acquisition type - should merge
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=50,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))

        assert len(item.securities) == 1
        assert item.securities[0].quantity == 150
        assert item.securities[0].stock == 150

    def test_no_merge_different_dates(self):
        item = KDVPItem("AAPL", False, [])
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 16),
            quantity=50,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))

        assert len(item.securities) == 2

    def test_no_merge_different_prices(self):
        item = KDVPItem("AAPL", False, [])
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=50,
            value=151.0,
            stock=0,
            acquisition_type="A"
        ))

        assert len(item.securities) == 2

    def test_no_merge_different_acquisition_types(self):
        item = KDVPItem("AAPL", False, [])
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=50,
            value=150.0,
            stock=0,
            acquisition_type="B"
        ))

        assert len(item.securities) == 2

    def test_no_merge_open_and_close(self):
        item = KDVPItem("AAPL", False, [])
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        item.add_trade(KDVPSecurityClose(
            date=datetime.date(2024, 1, 15),
            quantity=50,
            value=150.0,
            stock=0,
            loss_transfer=False
        ))

        assert len(item.securities) == 2

    def test_merge_close_trades_same_loss_transfer(self):
        item = KDVPItem("AAPL", False, [])
        # First open some positions
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=200,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        # Close trades on same date with same settings
        item.add_trade(KDVPSecurityClose(
            date=datetime.date(2024, 2, 15),
            quantity=50,
            value=160.0,
            stock=0,
            loss_transfer=False
        ))
        item.add_trade(KDVPSecurityClose(
            date=datetime.date(2024, 2, 15),
            quantity=30,
            value=160.0,
            stock=0,
            loss_transfer=False
        ))

        # Open + one merged close
        assert len(item.securities) == 2
        close_trade = item.securities[1]
        assert close_trade.quantity == 80

    def test_no_merge_different_loss_transfer(self):
        item = KDVPItem("AAPL", False, [])
        item.add_trade(KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=200,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        item.add_trade(KDVPSecurityClose(
            date=datetime.date(2024, 2, 15),
            quantity=50,
            value=160.0,
            stock=0,
            loss_transfer=False
        ))
        item.add_trade(KDVPSecurityClose(
            date=datetime.date(2024, 2, 15),
            quantity=30,
            value=160.0,
            stock=0,
            loss_transfer=True
        ))

        # Different loss_transfer, so 3 trades
        assert len(item.securities) == 3


class TestDohKDVP:
    """Tests for the main KDVP tracking class."""

    def test_add_trade_creates_item(self):
        kdvp = DohKDVP()
        trade = KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        )
        kdvp.add_trade("AAPL", trade)

        assert "AAPL" in kdvp.items
        assert kdvp.items["AAPL"].name == "AAPL"

    def test_add_trade_reuses_existing_item(self):
        kdvp = DohKDVP()
        kdvp.add_trade("AAPL", KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        kdvp.add_trade("AAPL", KDVPSecurityOpen(
            date=datetime.date(2024, 2, 15),
            quantity=50,
            value=155.0,
            stock=0,
            acquisition_type="A"
        ))

        assert len(kdvp.items) == 1
        assert len(kdvp.items["AAPL"].securities) == 2

    def test_multiple_symbols(self):
        kdvp = DohKDVP()
        kdvp.add_trade("AAPL", KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=150.0,
            stock=0,
            acquisition_type="A"
        ))
        kdvp.add_trade("MSFT", KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=50,
            value=400.0,
            stock=0,
            acquisition_type="A"
        ))

        assert len(kdvp.items) == 2
        assert "AAPL" in kdvp.items
        assert "MSFT" in kdvp.items

    def test_is_fond_flag(self):
        kdvp = DohKDVP()
        kdvp.add_trade("FUND1", KDVPSecurityOpen(
            date=datetime.date(2024, 1, 15),
            quantity=100,
            value=50.0,
            stock=0,
            acquisition_type="A"
        ), is_fond=True)

        assert kdvp.items["FUND1"].is_fond is True
