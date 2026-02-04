"""Tests for ISIN validation logic."""
import pytest
from isin_utils import validate_isin, validate_isin_checksum


class TestValidateIsinChecksum:
    """Tests for the Luhn checksum validation."""

    def test_valid_apple_isin(self):
        assert validate_isin_checksum("US0378331005") is True

    def test_valid_microsoft_isin(self):
        assert validate_isin_checksum("US5949181045") is True

    def test_valid_tesla_isin(self):
        assert validate_isin_checksum("US88160R1014") is True

    def test_valid_german_isin(self):
        # Siemens AG
        assert validate_isin_checksum("DE0007236101") is True

    def test_valid_uk_isin(self):
        # HSBC
        assert validate_isin_checksum("GB0005405286") is True

    def test_valid_japanese_isin(self):
        # Toyota
        assert validate_isin_checksum("JP3633400001") is True

    def test_invalid_checksum_off_by_one(self):
        # Apple ISIN with wrong check digit (5 -> 6)
        assert validate_isin_checksum("US0378331006") is False

    def test_invalid_checksum_transposed_digits(self):
        # Apple ISIN with transposed digits
        assert validate_isin_checksum("US0378313005") is False

    def test_check_digit_zero(self):
        # Test ISIN where check digit is 0
        assert validate_isin_checksum("AU0000XVGZA3") is True

    def test_all_letters_country_code(self):
        # Letters get converted to numbers (A=10, B=11, etc.)
        assert validate_isin_checksum("US0378331005") is True

    def test_mixed_alphanumeric_nsin(self):
        # ISIN with letters in NSIN portion
        assert validate_isin_checksum("AU0000XVGZA3") is True


class TestValidateIsin:
    """Tests for complete ISIN format and checksum validation."""

    def test_valid_isin_returns_uppercase(self):
        result = validate_isin("us0378331005")
        assert result == "US0378331005"

    def test_valid_isin_strips_whitespace(self):
        result = validate_isin("  US0378331005  ")
        assert result == "US0378331005"

    def test_empty_isin_exits(self):
        with pytest.raises(SystemExit):
            validate_isin("")

    def test_none_isin_exits(self):
        with pytest.raises(SystemExit):
            validate_isin(None)

    def test_too_short_exits(self):
        with pytest.raises(SystemExit):
            validate_isin("US03783310")  # 10 chars

    def test_too_long_exits(self):
        with pytest.raises(SystemExit):
            validate_isin("US03783310050")  # 13 chars

    def test_invalid_country_code_numbers_exits(self):
        with pytest.raises(SystemExit):
            validate_isin("120378331005")  # Numbers instead of letters

    def test_invalid_check_digit_not_number_exits(self):
        with pytest.raises(SystemExit):
            validate_isin("US037833100A")  # Letter instead of digit

    def test_invalid_checksum_exits(self):
        with pytest.raises(SystemExit):
            validate_isin("US0378331006")  # Wrong check digit

    def test_context_in_error_message(self, capsys):
        with pytest.raises(SystemExit):
            validate_isin("", context="Apple Inc")
        captured = capsys.readouterr()
        assert "Apple Inc" in captured.out

    def test_valid_isin_with_context(self):
        result = validate_isin("US0378331005", context="Apple Inc")
        assert result == "US0378331005"
