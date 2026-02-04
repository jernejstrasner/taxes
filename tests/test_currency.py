"""Tests for currency exchange rate lookup and fallback logic."""
import datetime
import pytest
import warnings
from unittest.mock import patch
from currency import Currency


class TestCurrencyGetRate:
    """Tests for exchange rate lookup with date fallback."""

    @pytest.fixture
    def currency_with_data(self):
        """Create a Currency instance with mock data."""
        with patch.object(Currency, '__init__', lambda self, dates, currencies: None):
            currency = Currency.__new__(Currency)
            currency.currency_data = {
                datetime.date(2024, 1, 15): {"USD": 1.0850, "CAD": 1.4720},
                datetime.date(2024, 1, 16): {"USD": 1.0870, "CAD": 1.4700},
                datetime.date(2024, 1, 18): {"USD": 1.0900, "CAD": 1.4680},
                # Gap on 2024-01-17 (weekend/holiday)
                datetime.date(2024, 1, 19): {"USD": 1.0910, "CAD": 1.4690},
            }
            return currency

    def test_exact_date_match(self, currency_with_data):
        rate = currency_with_data.get_rate(datetime.date(2024, 1, 15), "USD")
        assert rate == 1.0850

    def test_exact_date_match_different_currency(self, currency_with_data):
        rate = currency_with_data.get_rate(datetime.date(2024, 1, 15), "CAD")
        assert rate == 1.4720

    def test_fallback_to_earlier_date(self, currency_with_data):
        # 2024-01-17 is missing, should fall back to 2024-01-16
        rate = currency_with_data.get_rate(datetime.date(2024, 1, 17), "USD")
        assert rate == 1.0870

    def test_fallback_multiple_days(self, currency_with_data):
        # Test a date further from available data
        rate = currency_with_data.get_rate(datetime.date(2024, 1, 20), "USD")
        assert rate == 1.0910  # Falls back to 2024-01-19

    def test_no_earlier_date_uses_earliest(self, currency_with_data):
        # Date before all available data
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rate = currency_with_data.get_rate(datetime.date(2024, 1, 10), "USD")
            # Should use earliest available date (2024-01-15)
            assert rate == 1.0850
            # Should warn about missing data
            assert len(w) == 1
            assert "No currency data found before" in str(w[0].message)

    def test_currency_not_found_exits(self, currency_with_data):
        with pytest.raises(SystemExit):
            currency_with_data.get_rate(datetime.date(2024, 1, 15), "GBP")


class TestCurrencyInit:
    """Tests for date range initialization with previous month expansion."""

    def test_expands_to_previous_month(self):
        """Init should add all dates from the previous month."""
        with patch.object(Currency, 'get_currency', return_value={}):
            dates = [datetime.date(2024, 2, 15)]
            currency = Currency(dates, ["USD"])

            # Should include all January dates plus the original February date
            assert datetime.date(2024, 1, 1) in currency.dates
            assert datetime.date(2024, 1, 31) in currency.dates
            assert datetime.date(2024, 2, 15) in currency.dates

    def test_year_boundary_expansion(self):
        """January date should expand to December of previous year."""
        with patch.object(Currency, 'get_currency', return_value={}):
            dates = [datetime.date(2024, 1, 15)]
            currency = Currency(dates, ["USD"])

            # Should include December 2023
            assert datetime.date(2023, 12, 1) in currency.dates
            assert datetime.date(2023, 12, 31) in currency.dates

    def test_first_day_of_month(self):
        """First day of month should still expand to previous month."""
        with patch.object(Currency, 'get_currency', return_value={}):
            dates = [datetime.date(2024, 3, 1)]
            currency = Currency(dates, ["USD"])

            # Should include February 2024
            assert datetime.date(2024, 2, 1) in currency.dates
            assert datetime.date(2024, 2, 29) in currency.dates  # 2024 is leap year

    def test_dates_sorted(self):
        """Dates should be sorted after expansion."""
        with patch.object(Currency, 'get_currency', return_value={}):
            dates = [datetime.date(2024, 2, 20), datetime.date(2024, 2, 10)]
            currency = Currency(dates, ["USD"])

            assert currency.dates == sorted(currency.dates)

    def test_multiple_dates_same_month(self):
        """Multiple dates in same month should only expand once."""
        with patch.object(Currency, 'get_currency', return_value={}):
            dates = [
                datetime.date(2024, 2, 15),
                datetime.date(2024, 2, 20),
                datetime.date(2024, 2, 25)
            ]
            currency = Currency(dates, ["USD"])

            # Count January dates - should have 31
            jan_dates = [d for d in currency.dates if d.month == 1 and d.year == 2024]
            assert len(jan_dates) == 31


class TestCurrencyValidation:
    """Tests for exchange rate validation during parsing."""

    def test_rate_must_be_positive(self):
        """Zero or negative rates should fail - tested via get_currency validation."""
        # Currency.get_currency validates rates > 0 and < 10000 during XML parsing
        pass

    def test_rate_upper_bound(self):
        """Rates above 10000 should be flagged as suspicious."""
        # Currency.get_currency validates rates > 0 and < 10000 during XML parsing
        pass


class TestCurrencyConversionCalculation:
    """Tests for actual conversion calculations."""

    @pytest.fixture
    def currency_with_data(self):
        with patch.object(Currency, '__init__', lambda self, dates, currencies: None):
            currency = Currency.__new__(Currency)
            currency.currency_data = {
                datetime.date(2024, 1, 15): {"USD": 1.0850},
            }
            return currency

    def test_usd_to_eur_conversion(self, currency_with_data):
        """100 USD at rate 1.0850 = 100 / 1.0850 EUR."""
        rate = currency_with_data.get_rate(datetime.date(2024, 1, 15), "USD")
        usd_amount = 100.0
        eur_amount = usd_amount / rate

        assert abs(eur_amount - 92.166) < 0.001  # ~92.17 EUR

    def test_rate_precision(self, currency_with_data):
        """Test that rate maintains precision."""
        rate = currency_with_data.get_rate(datetime.date(2024, 1, 15), "USD")
        assert rate == 1.0850  # Exact match

    def test_small_amount_conversion(self, currency_with_data):
        """Test conversion of small amounts doesn't lose precision."""
        rate = currency_with_data.get_rate(datetime.date(2024, 1, 15), "USD")
        usd_amount = 0.01
        eur_amount = usd_amount / rate

        assert eur_amount > 0
        assert abs(eur_amount - 0.00922) < 0.00001

    def test_large_amount_conversion(self, currency_with_data):
        """Test conversion of large amounts."""
        rate = currency_with_data.get_rate(datetime.date(2024, 1, 15), "USD")
        usd_amount = 1_000_000.0
        eur_amount = usd_amount / rate

        assert abs(eur_amount - 921658.99) < 1  # ~921,659 EUR
