import yfinance as yf
from cache import CompanyCache
from isin_utils import validate_isin


class FinanceData:
    def __init__(self, cache: CompanyCache):
        self.cache = cache

    def fetch_info(self, symbols):
        for symbol in symbols:
            ticker = yf.Ticker(symbol.split(":")[0] if ":" in symbol else symbol)
            address = self.cache.get_address(symbol)
            if not address:
                info = ticker.info
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
            # Try to get ISIN from Yahoo Finance (unreliable but worth trying)
            # Note: Sometimes picks wrong country/exchange, manual verification recommended
            isin = self.cache.get_isin(symbol)
            if not isin:
                try:
                    _isin = ticker.info.get('isin')
                    if _isin:
                        # Validate ISIN format and checksum
                        validated_isin = validate_isin(_isin, f"Yahoo Finance for {symbol}")
                        self.cache.set_isin(symbol, validated_isin)
                        print(f"ISIN for {symbol} is {validated_isin} (from Yahoo Finance - please verify)")
                    else:
                        print(f"ISIN not found for {symbol} in Yahoo Finance")
                except Exception as e:
                    print(f"Could not validate ISIN for {symbol}: {e}")

    def get_isin(self, ticker):
        return self.cache.get_isin(ticker)

    def get_address(self, ticker):
        return self.cache.get_address(ticker)
