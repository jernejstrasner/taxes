import pytest
from unittest.mock import MagicMock

from finance import FinanceData, MIC_TO_YAHOO_SUFFIX


class TestGetYahooTicker:
    """Tests for _get_yahoo_ticker symbol conversion."""

    @pytest.fixture
    def finance_data(self):
        mock_cache = MagicMock()
        return FinanceData(mock_cache)

    def test_xetra_exchange(self, finance_data):
        """XETRA symbols get .DE suffix."""
        assert finance_data._get_yahoo_ticker("XDPD:xetr") == "XDPD.DE"

    def test_amsterdam_exchange(self, finance_data):
        """Amsterdam symbols get .AS suffix."""
        assert finance_data._get_yahoo_ticker("ASML:xams") == "ASML.AS"

    def test_paris_exchange(self, finance_data):
        """Paris symbols get .PA suffix."""
        assert finance_data._get_yahoo_ticker("AIR:xpar") == "AIR.PA"

    def test_nyse_no_suffix(self, finance_data):
        """NYSE symbols get no suffix."""
        assert finance_data._get_yahoo_ticker("AAPL:xnys") == "AAPL"

    def test_nasdaq_no_suffix(self, finance_data):
        """NASDAQ symbols get no suffix."""
        assert finance_data._get_yahoo_ticker("MSFT:xnas") == "MSFT"

    def test_case_insensitive_mic(self, finance_data):
        """MIC codes should be case-insensitive."""
        assert finance_data._get_yahoo_ticker("XDPD:XETR") == "XDPD.DE"
        assert finance_data._get_yahoo_ticker("ASML:XAMS") == "ASML.AS"

    def test_unknown_mic_returns_bare_ticker(self, finance_data):
        """Unknown MIC codes return just the ticker without suffix."""
        assert finance_data._get_yahoo_ticker("FOO:unknown") == "FOO"

    def test_no_mic_returns_symbol_unchanged(self, finance_data):
        """Symbols without MIC code are returned unchanged."""
        assert finance_data._get_yahoo_ticker("AAPL") == "AAPL"
        assert finance_data._get_yahoo_ticker("MSFT") == "MSFT"

    def test_all_known_exchanges(self, finance_data):
        """Verify all mapped exchanges produce correct suffixes."""
        test_cases = [
            ("TEST:xetr", "TEST.DE"),
            ("TEST:xfra", "TEST.F"),
            ("TEST:xams", "TEST.AS"),
            ("TEST:xpar", "TEST.PA"),
            ("TEST:xbru", "TEST.BR"),
            ("TEST:xlon", "TEST.L"),
            ("TEST:xnys", "TEST"),
            ("TEST:xnas", "TEST"),
            ("TEST:xmil", "TEST.MI"),
            ("TEST:xswx", "TEST.SW"),
            ("TEST:xsto", "TEST.ST"),
            ("TEST:xcse", "TEST.CO"),
            ("TEST:xosl", "TEST.OL"),
            ("TEST:xhel", "TEST.HE"),
            ("TEST:xwbo", "TEST.VI"),
            ("TEST:xmad", "TEST.MC"),
            ("TEST:xlis", "TEST.LS"),
            ("TEST:xdub", "TEST.IR"),
        ]
        for saxo_symbol, expected_yahoo in test_cases:
            assert finance_data._get_yahoo_ticker(saxo_symbol) == expected_yahoo


class TestMicMapping:
    """Tests for MIC_TO_YAHOO_SUFFIX mapping."""

    def test_mapping_has_expected_exchanges(self):
        """Verify expected exchanges are in the mapping."""
        expected = ["xetr", "xfra", "xams", "xpar", "xbru", "xlon", "xnys",
                    "xnas", "xmil", "xswx", "xsto", "xcse", "xosl", "xhel",
                    "xwbo", "xmad", "xlis", "xdub"]
        for mic in expected:
            assert mic in MIC_TO_YAHOO_SUFFIX

    def test_us_exchanges_have_empty_suffix(self):
        """US exchanges should have empty suffix."""
        assert MIC_TO_YAHOO_SUFFIX["xnys"] == ""
        assert MIC_TO_YAHOO_SUFFIX["xnas"] == ""
