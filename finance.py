import time

import yfinance as yf
from cache import CompanyCache


# Delay between Yahoo Finance API calls to avoid rate limiting
YF_REQUEST_DELAY = 1.0

# MIC codes to Yahoo Finance ticker suffixes
MIC_TO_YAHOO_SUFFIX = {
    "xetr": ".DE",   # XETRA (Germany)
    "xfra": ".F",    # Frankfurt
    "xams": ".AS",   # Euronext Amsterdam
    "xpar": ".PA",   # Euronext Paris
    "xbru": ".BR",   # Euronext Brussels
    "xlon": ".L",    # London Stock Exchange
    "xnys": "",      # NYSE (no suffix)
    "xnas": "",      # NASDAQ (no suffix)
    "xmil": ".MI",   # Milan
    "xswx": ".SW",   # SIX Swiss Exchange
    "xsto": ".ST",   # Stockholm
    "xcse": ".CO",   # Copenhagen
    "xosl": ".OL",   # Oslo
    "xhel": ".HE",   # Helsinki
    "xwbo": ".VI",   # Vienna
    "xmad": ".MC",   # Madrid
    "xlis": ".LS",   # Lisbon
    "xdub": ".IR",   # Dublin
}


class FinanceData:
    def __init__(self, cache: CompanyCache):
        self.cache = cache

    def _get_yahoo_ticker(self, symbol: str) -> str:
        """Convert Saxo symbol (e.g., XDPD:xetr) to Yahoo ticker (e.g., XDPD.DE)."""
        if ":" in symbol:
            ticker, mic = symbol.split(":", 1)
            suffix = MIC_TO_YAHOO_SUFFIX.get(mic.lower(), "")
            return ticker + suffix
        return symbol

    def _get_ticker_info(self, ticker: yf.Ticker, symbol: str) -> dict | None:
        """Fetch ticker.info with rate limit handling and retries."""
        for attempt in range(3):
            try:
                time.sleep(YF_REQUEST_DELAY)
                return ticker.info
            except yf.exceptions.YFRateLimitError:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited by Yahoo Finance for {symbol}, retrying in {wait}s...")
                time.sleep(wait)
            except Exception as e:
                print(f"  Could not fetch info for {symbol} from Yahoo Finance: {e}")
                return None
        print(f"  Failed to fetch info for {symbol} after 3 retries (rate limited)")
        return None

    def fetch_addresses(self, symbols):
        """Fetch company addresses from Yahoo Finance for symbols missing addresses."""
        for symbol in symbols:
            if self.cache.get_address(symbol):
                continue

            yahoo_ticker = self._get_yahoo_ticker(symbol)
            ticker = yf.Ticker(yahoo_ticker)
            info = self._get_ticker_info(ticker, symbol)

            # Fallback to bare ticker if exchange-specific lookup failed
            if not info and ":" in symbol:
                bare_ticker = symbol.split(":")[0]
                if bare_ticker != yahoo_ticker:
                    ticker = yf.Ticker(bare_ticker)
                    info = self._get_ticker_info(ticker, symbol)

            if not info:
                print("Address not found for", symbol)
                continue

            if info.get("address1"):
                address_components = [
                    info.get("address1"),
                    info.get("city"),
                    info.get("state"),
                    info.get("zip"),
                ]
                address = ", ".join(filter(None, address_components))
                self.cache.set_address(symbol, address)
                print("Address for", symbol, "is", address)
            else:
                print("Address not found for", symbol)

    def get_isin(self, ticker):
        return self.cache.get_isin(ticker)

    def get_address(self, ticker):
        return self.cache.get_address(ticker)
