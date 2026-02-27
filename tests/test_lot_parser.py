"""Tests for lot_parser.py."""

from datetime import date
from decimal import Decimal

import pytest

from lot_parser import (
    parse_currency_value,
    parse_lot_csv,
    parse_lots_directory,
)


class TestParseCurrencyValue:
    """Tests for parse_currency_value."""

    def test_simple_value(self):
        assert parse_currency_value("$100.00") == Decimal("100.00")

    def test_with_thousands(self):
        assert parse_currency_value("$1,234.56") == Decimal("1234.56")

    def test_large_value(self):
        assert parse_currency_value("$44,667.00") == Decimal("44667.00")

    def test_no_dollar_sign(self):
        assert parse_currency_value("100.00") == Decimal("100.00")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_currency_value("")

    def test_dashes_raises(self):
        with pytest.raises(ValueError):
            parse_currency_value("--")


class TestParseLotCsv:
    """Tests for parse_lot_csv."""

    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create a sample lot CSV file."""
        # Format: header line, blank line, column headers, data rows
        content = '''"SHOP Lot Details for XXXX-5792 as of 08:03 AM ET, 02/11/2022"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"10/30/2017 00:00:00","8","$893.34","$108.98","$7,146.72","$871.84","$6,274.88","+719.73%","Long Term",
"07/11/2017 00:00:00","2","$893.34","$91.45","$1,786.68","$182.90","$1,603.78","+876.86%","Long Term",
"Total","70","--","--","$62,533.80","$4,388.71","$58,145.09","+1,324.88%","--",'''

        csv_file = tmp_path / "Lot-Details-SHOP.CSV"
        csv_file.write_text(content)
        return str(csv_file)

    def test_parses_lots(self, sample_csv):
        lots = parse_lot_csv(sample_csv)

        assert len(lots) == 2

        # First lot
        assert lots[0].symbol == "SHOP"
        assert lots[0].open_date == date(2017, 10, 30)
        assert lots[0].quantity == Decimal("8")
        assert lots[0].cost_per_share == Decimal("108.98")
        assert lots[0].cost_basis == Decimal("871.84")

        # Second lot
        assert lots[1].symbol == "SHOP"
        assert lots[1].open_date == date(2017, 7, 11)
        assert lots[1].quantity == Decimal("2")
        assert lots[1].cost_per_share == Decimal("91.45")
        assert lots[1].cost_basis == Decimal("182.90")

    def test_skips_total_row(self, sample_csv):
        lots = parse_lot_csv(sample_csv)
        # Should have 2 lots, not 3 (total row skipped)
        assert len(lots) == 2

    def test_invalid_filename_raises(self, tmp_path):
        csv_file = tmp_path / "invalid-name.csv"
        csv_file.write_text("test")

        with pytest.raises(ValueError, match="Cannot extract symbol"):
            parse_lot_csv(str(csv_file))


class TestParseLotsDirectory:
    """Tests for parse_lots_directory."""

    @pytest.fixture
    def sample_dir(self, tmp_path):
        """Create a directory with multiple lot CSV files."""
        # SHOP lots
        shop_content = '''"SHOP Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"10/30/2017 00:00:00","8","$893.34","$108.98","$7,146.72","$871.84","$6,274.88","+719.73%","Long Term",
"Total","8","--","--","$7,146.72","$871.84","$6,274.88","+719.73%","--",'''

        # NVDA lots
        nvda_content = '''"NVDA Lot Details"

"Open Date","Quantity","Price","Cost/Share","Market Value","Cost Basis","Gain/Loss $","Gain/Loss %","Holding Period",
"07/11/2017 00:00:00","8","$258.24","$38.21","$2,065.92","$305.66","$1,760.26","+575.89%","Long Term",
"06/27/2018 00:00:00","40","$258.24","$61.12","$10,329.60","$2,444.89","$7,884.71","+322.5%","Long Term",
"Total","48","--","--","$12,395.52","$2,750.55","$9,644.97","+350.66%","--",'''

        (tmp_path / "Lot-Details-SHOP.CSV").write_text(shop_content)
        (tmp_path / "Lot-Details-NVDA.CSV").write_text(nvda_content)

        return tmp_path

    def test_parses_all_files(self, sample_dir):
        lots = parse_lots_directory(str(sample_dir))

        assert "SHOP" in lots
        assert "NVDA" in lots
        assert len(lots["SHOP"]) == 1
        assert len(lots["NVDA"]) == 2

    def test_empty_directory(self, tmp_path):
        lots = parse_lots_directory(str(tmp_path))
        assert lots == {}

    def test_invalid_directory_raises(self):
        with pytest.raises(ValueError, match="Not a directory"):
            parse_lots_directory("/nonexistent/path")
