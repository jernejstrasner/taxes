"""Tests for date parsing and validation logic."""
import datetime
import pytest
import pandas as pd
from date_utils import parse_date, validate_date, parse_pandas_date_column


class TestParseDate:
    """Tests for date parsing from various formats."""

    def test_iso_format(self):
        result = parse_date("2024-01-15")
        assert result == datetime.date(2024, 1, 15)

    def test_saxo_format(self):
        result = parse_date("15-Jan-2024")
        assert result == datetime.date(2024, 1, 15)

    def test_slovenian_format(self):
        result = parse_date("15.01.2024")
        assert result == datetime.date(2024, 1, 15)

    def test_alternative_format(self):
        result = parse_date("2024/01/15")
        assert result == datetime.date(2024, 1, 15)

    def test_european_format(self):
        result = parse_date("15/01/2024")
        assert result == datetime.date(2024, 1, 15)

    def test_us_format(self):
        result = parse_date("01/15/2024")
        assert result == datetime.date(2024, 1, 15)

    def test_datetime_date_passthrough(self):
        input_date = datetime.date(2024, 1, 15)
        result = parse_date(input_date)
        assert result == input_date

    def test_pandas_timestamp_conversion(self):
        ts = pd.Timestamp("2024-01-15")
        result = parse_date(ts)
        assert result == datetime.date(2024, 1, 15)

    def test_whitespace_stripped(self):
        result = parse_date("  2024-01-15  ")
        assert result == datetime.date(2024, 1, 15)

    def test_invalid_format_exits(self):
        with pytest.raises(SystemExit):
            parse_date("not-a-date")

    def test_invalid_date_feb_30_exits(self):
        with pytest.raises(SystemExit):
            parse_date("2024-02-30")

    def test_leap_year_feb_29_valid(self):
        result = parse_date("2024-02-29")
        assert result == datetime.date(2024, 2, 29)

    def test_non_leap_year_feb_29_exits(self):
        with pytest.raises(SystemExit):
            parse_date("2023-02-29")

    def test_custom_format_list(self):
        result = parse_date("15/01/2024", formats=["%d/%m/%Y"])
        assert result == datetime.date(2024, 1, 15)

    def test_context_in_error(self, capsys):
        with pytest.raises(SystemExit):
            parse_date("invalid", context="dividend payment")
        captured = capsys.readouterr()
        assert "dividend payment" in captured.out


class TestValidateDate:
    """Tests for date validation (future dates, too old dates)."""

    def test_today_valid(self):
        today = datetime.date.today()
        # Should not raise
        validate_date(today)

    def test_yesterday_valid(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        validate_date(yesterday)

    def test_future_date_exits(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        with pytest.raises(SystemExit):
            validate_date(tomorrow)

    def test_boundary_1990_valid(self):
        boundary = datetime.date(1990, 1, 1)
        validate_date(boundary)

    def test_before_1990_exits(self):
        old_date = datetime.date(1989, 12, 31)
        with pytest.raises(SystemExit):
            validate_date(old_date)

    def test_very_old_date_exits(self):
        with pytest.raises(SystemExit):
            validate_date(datetime.date(1970, 1, 1))

    def test_context_in_error(self, capsys):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        with pytest.raises(SystemExit):
            validate_date(tomorrow, context="trade date")
        captured = capsys.readouterr()
        assert "trade date" in captured.out


class TestParsePandasDateColumn:
    """Tests for batch date parsing in DataFrames."""

    def test_single_format_fast_path(self):
        df = pd.DataFrame({"Date": ["2024-01-15", "2024-01-16"]})
        result = parse_pandas_date_column(df, "Date", formats=["%Y-%m-%d"])
        assert result["Date"].iloc[0] == pd.Timestamp("2024-01-15")
        assert result["Date"].iloc[1] == pd.Timestamp("2024-01-16")

    def test_missing_column_exits(self):
        df = pd.DataFrame({"OtherColumn": ["value"]})
        with pytest.raises(SystemExit):
            parse_pandas_date_column(df, "Date")

    def test_nan_values_preserved(self):
        df = pd.DataFrame({"Date": ["2024-01-15", None, "2024-01-17"]})
        result = parse_pandas_date_column(df, "Date")
        assert pd.isna(result["Date"].iloc[1])

    def test_empty_dataframe(self):
        df = pd.DataFrame({"Date": []})
        result = parse_pandas_date_column(df, "Date")
        assert len(result) == 0

    def test_mixed_formats_fallback(self):
        # When pandas can't infer, it falls back to row-by-row
        df = pd.DataFrame({"Date": ["15-Jan-2024", "16-Jan-2024"]})
        result = parse_pandas_date_column(df, "Date")
        assert result["Date"].iloc[0].date() == datetime.date(2024, 1, 15)
