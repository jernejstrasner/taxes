"""Tests for interest aggregation and condensation."""
from unittest.mock import MagicMock
from interest import Interest, InterestType, DohObr


def make_taxpayer():
    """Create a mock taxpayer for testing."""
    tp = MagicMock()
    tp.taxNumber = "12345678"
    tp.name = "Test User"
    tp.address = "Test Address 1"
    tp.city = "Ljubljana"
    tp.postNumber = "1000"
    tp.postName = "Ljubljana"
    tp.email = "test@example.com"
    tp.phone = "040123456"
    return tp


class TestCondenseInterests:
    """Tests for condensing multiple interest entries from same payer."""

    def test_single_interest_unchanged(self):
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=100.0,
            country2="DK"
        ))
        doh.condense_interests()

        assert len(doh.interests) == 1
        assert doh.interests[0].value == 100.0

    def test_same_payer_values_summed(self):
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=100.0,
            country2="DK"
        ))
        doh.add_interest(Interest(
            date="2024-02-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=50.0,
            country2="DK"
        ))
        doh.condense_interests()

        assert len(doh.interests) == 1
        assert doh.interests[0].value == 150.0

    def test_same_payer_keeps_latest_date(self):
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=100.0,
            country2="DK"
        ))
        doh.add_interest(Interest(
            date="2024-03-20",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=50.0,
            country2="DK"
        ))
        doh.condense_interests()

        assert doh.interests[0].date == "2024-03-20"

    def test_different_payers_not_merged(self):
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=100.0,
            country2="DK"
        ))
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="789012",
            name="Other Bank",
            address="Other Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=50.0,
            country2="DK"
        ))
        doh.condense_interests()

        assert len(doh.interests) == 2

    def test_different_types_not_merged(self):
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=100.0,
            country2="DK"
        ))
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.NON_EU_BANK_INTEREST,
            value=50.0,
            country2="DK"
        ))
        doh.condense_interests()

        assert len(doh.interests) == 2

    def test_different_countries_not_merged(self):
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=100.0,
            country2="DK"
        ))
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DE",
            type=InterestType.FUND_INTEREST,
            value=50.0,
            country2="DE"
        ))
        doh.condense_interests()

        assert len(doh.interests) == 2

    def test_empty_interests_unchanged(self):
        doh = DohObr(2024, make_taxpayer())
        doh.condense_interests()
        assert len(doh.interests) == 0

    def test_multiple_entries_same_payer_summed(self):
        doh = DohObr(2024, make_taxpayer())
        # Add 5 monthly payments
        for month in range(1, 6):
            doh.add_interest(Interest(
                date=f"2024-{month:02d}-15",
                identification_number="123456",
                name="Test Bank",
                address="Bank Street 1",
                country="DK",
                type=InterestType.FUND_INTEREST,
                value=100.0,
                country2="DK"
            ))
        doh.condense_interests()

        assert len(doh.interests) == 1
        assert doh.interests[0].value == 500.0
        assert doh.interests[0].date == "2024-05-15"  # Latest date

    def test_zero_value_interest(self):
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=0.0,
            country2="DK"
        ))
        doh.condense_interests()

        assert len(doh.interests) == 1
        assert doh.interests[0].value == 0.0

    def test_negative_value_interest(self):
        """Negative values might represent corrections/fees."""
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=100.0,
            country2="DK"
        ))
        doh.add_interest(Interest(
            date="2024-02-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=-10.0,
            country2="DK"
        ))
        doh.condense_interests()

        assert len(doh.interests) == 1
        assert doh.interests[0].value == 90.0

    def test_precision_float_values(self):
        """Test floating point precision in summation."""
        doh = DohObr(2024, make_taxpayer())
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=0.01,
            country2="DK"
        ))
        doh.add_interest(Interest(
            date="2024-02-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=0.02,
            country2="DK"
        ))
        doh.condense_interests()

        # 0.01 + 0.02 should be exactly 0.03 after rounding
        assert doh.interests[0].value == 0.03

    def test_rounding_to_four_decimals(self):
        """Test that condensation rounds to 4 decimal places."""
        doh = DohObr(2024, make_taxpayer())
        # Add values with more than 4 decimal places
        doh.add_interest(Interest(
            date="2024-01-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=1.23456789,
            country2="DK"
        ))
        doh.add_interest(Interest(
            date="2024-02-15",
            identification_number="123456",
            name="Test Bank",
            address="Bank Street 1",
            country="DK",
            type=InterestType.FUND_INTEREST,
            value=2.34567891,
            country2="DK"
        ))
        doh.condense_interests()

        # Sum would be 3.5802468, rounded to 4 decimals = 3.5802
        assert doh.interests[0].value == 3.5802
