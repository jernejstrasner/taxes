"""Cache for stock split data from Yahoo Finance."""

import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import yfinance as yf
from lxml import etree


YF_REQUEST_DELAY = 1.0


@dataclass
class StockSplit:
    """A stock split event."""
    date: date
    ratio: Decimal  # e.g., 10 for a 10:1 split (10 new shares per old share)


class SplitCache:
    """Cache for stock split data, persisted as XML."""

    def __init__(self, path: str = "cache/split_cache.xml"):
        self.path = path
        self.memory: dict[str, list[StockSplit]] = {}
        self._load()

    def _load(self):
        """Load cache from XML file."""
        try:
            tree = etree.parse(self.path)
            for symbol_el in tree.getroot():
                symbol = symbol_el.attrib["id"]
                splits = []
                for split_el in symbol_el:
                    split_date = date.fromisoformat(split_el.attrib["date"])
                    ratio = Decimal(split_el.attrib["ratio"])
                    splits.append(StockSplit(date=split_date, ratio=ratio))
                self.memory[symbol] = splits
        except (FileNotFoundError, OSError):
            pass

    def flush(self):
        """Write cache to XML file."""
        root = etree.Element("splits")
        for symbol, splits in sorted(self.memory.items()):
            symbol_el = etree.SubElement(root, "symbol", id=symbol)
            for split in sorted(splits, key=lambda s: s.date):
                etree.SubElement(
                    symbol_el, "split",
                    date=split.date.isoformat(),
                    ratio=str(split.ratio)
                )

        with open(self.path, "wb") as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8"))

    def get_splits(self, symbol: str) -> list[StockSplit]:
        """Get all splits for a symbol. Fetches from Yahoo if not cached."""
        if symbol not in self.memory:
            self._fetch_splits(symbol)
        return self.memory.get(symbol, [])

    def get_splits_in_range(self, symbol: str, after: date, before: date) -> list[StockSplit]:
        """Get splits for a symbol that occurred between two dates (exclusive)."""
        all_splits = self.get_splits(symbol)
        return [s for s in all_splits if after < s.date < before]

    def _fetch_splits(self, symbol: str):
        """Fetch splits from Yahoo Finance and cache them."""
        print(f"  Fetching splits for {symbol}...")
        time.sleep(YF_REQUEST_DELAY)

        try:
            ticker = yf.Ticker(symbol)
            splits_series = ticker.splits

            if splits_series is None or splits_series.empty:
                self.memory[symbol] = []
                return

            splits = []
            for split_date, ratio in splits_series.items():
                # yfinance returns splits as pandas Timestamp index
                split_date_obj = split_date.date()
                # ratio is "new_shares : old_shares" e.g., 10.0 means 10:1
                splits.append(StockSplit(
                    date=split_date_obj,
                    ratio=Decimal(str(ratio))
                ))

            self.memory[symbol] = splits

        except Exception as e:
            print(f"  Warning: Could not fetch splits for {symbol}: {e}")
            self.memory[symbol] = []
