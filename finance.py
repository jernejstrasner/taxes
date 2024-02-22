import yfinance as yf
from cache import CompanyCache


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
            # Getting ISIN is unreliable. Sometimes it picks the wrong country/exchange.
            # TODO: Add ability to also provide the exchange to the Ticker object and then correctly fetch the ISIN.
            # isin = self.cache.get_isin(ticker.ticker)
            # if not isin:
            #   _isin = ticker.isin
            #   if _isin and re.match(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$', _isin):
            #     isin = _isin
            #     self.cache.set_isin(symbol, isin)
            #     print("ISIN for", symbol, "is", isin)
            #   else:
            #     print("ISIN not found for", symbol)

    def get_isin(self, ticker):
        return self.cache.get_isin(ticker)

    def get_address(self, ticker):
        return self.cache.get_address(ticker)
