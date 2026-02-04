"""Parser for Interactive Brokers Flex Query XML exports."""

import datetime
import sys
from xml.etree import ElementTree
from typing import NamedTuple

from gains import KDVPSecurityOpen, KDVPSecurityClose


class IBKRTrade(NamedTuple):
    """Parsed trade from IBKR Flex Query."""
    symbol: str
    isin: str
    trade_date: datetime.date
    quantity: float
    price: float  # per-share price in EUR
    is_buy: bool
    is_etf: bool


def parse_ibkr_date(date_str: str) -> datetime.date:
    """Parse IBKR date format (yyyyMMdd)."""
    return datetime.datetime.strptime(date_str, "%Y%m%d").date()


def process_ibkr_xml(file_path: str) -> list[IBKRTrade]:
    """
    Parse IBKR Flex Query XML and extract trades.

    Args:
        file_path: Path to the Flex Query XML file

    Returns:
        List of IBKRTrade objects
    """
    try:
        tree = ElementTree.parse(file_path)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        print("Please check the file path and try again")
        sys.exit(1)
    except ElementTree.ParseError as e:
        print(f"Error: Failed to parse XML file: {file_path}")
        print(f"Parse error: {e}")
        print("Ensure this is a valid IBKR Flex Query XML export")
        sys.exit(1)

    root = tree.getroot()

    # Find all Trade elements
    trades_elem = root.find(".//Trades")
    if trades_elem is None:
        print(f"Error: No Trades section found in {file_path}")
        print("Ensure your Flex Query includes the Trades section")
        sys.exit(1)

    trades: list[IBKRTrade] = []

    for trade_elem in trades_elem.findall("Trade"):
        # Skip non-stock trades (options, futures, etc.)
        asset_category = trade_elem.get("assetCategory", "")
        if asset_category != "STK":
            continue

        currency = trade_elem.get("currency", "")

        # Only EUR is supported for now
        if currency != "EUR":
            print(f"Error: Unsupported currency '{currency}' in IBKR trade")
            print(f"  Symbol: {trade_elem.get('symbol')}")
            print(f"  Date: {trade_elem.get('tradeDate')}")
            print("")
            print("Currently only EUR trades are supported.")
            print("USD support requires Bank of Slovenia exchange rate integration.")
            print("Please file a feature request or wait for USD support to be implemented.")
            sys.exit(1)

        symbol = trade_elem.get("symbol", "")
        isin = trade_elem.get("isin", "")
        trade_date_str = trade_elem.get("tradeDate", "")
        quantity_str = trade_elem.get("quantity", "0")
        price_str = trade_elem.get("tradePrice", "0")
        buy_sell = trade_elem.get("buySell", "")
        sub_category = trade_elem.get("subCategory", "")

        if not symbol or not trade_date_str:
            print("Warning: Skipping trade with missing symbol or date")
            continue

        if not isin:
            print(f"Warning: Trade for {symbol} on {trade_date_str} has no ISIN")
            print("  ISIN is required for FURS reporting")
            print("  Please ensure your Flex Query includes the ISIN field")
            sys.exit(1)

        trade_date = parse_ibkr_date(trade_date_str)
        quantity = abs(float(quantity_str))
        price = float(price_str)
        is_buy = buy_sell == "BUY"
        is_etf = sub_category == "ETF"

        trades.append(IBKRTrade(
            symbol=symbol,
            isin=isin,
            trade_date=trade_date,
            quantity=quantity,
            price=price,
            is_buy=is_buy,
            is_etf=is_etf,
        ))

    print(f"Parsed {len(trades)} stock trades from IBKR export")

    # Print summary
    buys = sum(1 for t in trades if t.is_buy)
    sells = len(trades) - buys
    print(f"  Buys: {buys}, Sells: {sells}")

    return trades


def ibkr_trades_to_kdvp(trades: list[IBKRTrade]) -> list[tuple[str, KDVPSecurityOpen | KDVPSecurityClose, bool]]:
    """
    Convert IBKR trades to KDVP domain objects.

    Returns:
        List of tuples: (symbol, trade_object, is_fond)
    """
    result = []

    for trade in trades:
        if trade.is_buy:
            kdvp_trade = KDVPSecurityOpen(
                date=trade.trade_date,
                quantity=trade.quantity,
                value=trade.price,
                stock=0,  # will be calculated by DohKDVP
                acquisition_type="A",  # regular purchase
            )
        else:
            kdvp_trade = KDVPSecurityClose(
                date=trade.trade_date,
                quantity=trade.quantity,
                value=trade.price,
                stock=0,  # will be calculated by DohKDVP
                loss_transfer=False,  # TODO: determine from fifoPnlRealized if negative
            )

        # Use symbol as identifier (FURS Code field is max 10 chars, ISIN is 12)
        result.append((trade.symbol, kdvp_trade, trade.is_etf))

    return result
