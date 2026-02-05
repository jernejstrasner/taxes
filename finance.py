import time

import yfinance as yf
from cache import CompanyCache
from isin_utils import validate_isin
import requests


# Delay between Yahoo Finance API calls to avoid rate limiting
YF_REQUEST_DELAY = 1.0


class FinanceData:
    def __init__(self, cache: CompanyCache):
        self.cache = cache

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
            except requests.exceptions.Timeout:
                print(f"  Timeout fetching data for {symbol} from Yahoo Finance")
                return None
            except Exception as e:
                print(f"  Could not fetch info for {symbol} from Yahoo Finance: {e}")
                return None
        print(f"  Failed to fetch info for {symbol} after 3 retries (rate limited)")
        return None

    def fetch_info(self, symbols):
        session = requests.Session()
        session.timeout = 30

        for symbol in symbols:
            need_address = not self.cache.get_address(symbol)
            need_isin = not self.cache.get_isin(symbol)
            if not need_address and not need_isin:
                continue

            ticker = yf.Ticker(
                symbol.split(":")[0] if ":" in symbol else symbol,
                session=session
            )
            info = self._get_ticker_info(ticker, symbol)
            if not info:
                if need_address:
                    print("Address not found for", symbol)
                if need_isin:
                    print(f"ISIN not found for {symbol} in Yahoo Finance")
                continue

            if need_address:
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

            if need_isin:
                _isin = info.get('isin')
                if _isin:
                    validated_isin = validate_isin(_isin, f"Yahoo Finance for {symbol}")
                    self.cache.set_isin(symbol, validated_isin)
                    print(f"ISIN for {symbol} is {validated_isin} (from Yahoo Finance - please verify)")
                else:
                    print(f"ISIN not found for {symbol} in Yahoo Finance")

    def get_isin(self, ticker):
        return self.cache.get_isin(ticker)

    def get_address(self, ticker):
        return self.cache.get_address(ticker)
