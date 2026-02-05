import sys

import pandas as pd

from currency import Currency
from gains import DohKDVP, KDVPSecurityOpen, KDVPSecurityClose
from interest import Interest, InterestType
from date_utils import parse_pandas_date_column
from error_utils import file_error


def process_saxo_xlsx(file_path) -> list[Interest]:
    # Open interest xlsx file
    try:
        df = pd.read_excel(file_path, sheet_name="Interest Details")
    except FileNotFoundError:
        file_error(
            "reading", file_path, "File not found",
            [f"Check that the file path '{file_path}' is correct",
             "Ensure the Saxo Bank Excel file is in the expected location"]
        )
    except Exception as e:
        file_error(
            "reading", file_path, str(e),
            ["Ensure the file is a valid Excel file (.xlsx)",
             "Check that the file contains an 'Interest Details' sheet",
             "Verify the file is not corrupted or password protected"]
        )

    # Parse the date values in GMT and convert to CET/CEST accounting for DST
    df = parse_pandas_date_column(df, "Calculation dateGMT", ["%d-%b-%Y"], "Saxo interest date")
    df["Date"] = (
        df["Calculation dateGMT"]
        .dt.tz_localize("GMT")  # Mark the time as GMT
        .dt.tz_convert("Europe/Ljubljana")  # Convert to CET/CEST (Slovenia timezone)
    )

    # Get the exchange rate for the dates in the Date column
    currency = Currency(
        [d.date() for d in df["Date"].unique()],  # Convert Timestamp to datetime.date
        ["USD"],
    )

    # Convert USD amounts to EUR using vectorized operations
    usd_mask = df["Account Currency"].str.startswith("USD")
    df.loc[usd_mask, "Interest amount "] = df.loc[usd_mask, "Interest amount "] / df[
        usd_mask
    ]["Date"].map(lambda date: currency.get_rate(date.date(), "USD"))

    # Write to console the total interest amount calculated in EUR
    total_interest = round(df["Interest amount "].sum(), 2)
    print(f"[Saxobank] total interest: {total_interest} EUR")

    return [
        Interest(
            row["Date"].strftime("%Y-%m-%d"),
            "15731249",
            "Saxo Bank A/S",
            "Philip Heymans Alle 15, 2900 Hellerup",
            "DK",
            InterestType.FUND_INTEREST,
            row["Interest amount "],
            "DK",
        )
        for _, row in df.iterrows()
    ]


def saxo_trades_to_kdvp(
    df: pd.DataFrame,
    doh_kdvp: DohKDVP,
):
    """
    Process Saxo ClosedPositions rows into KDVP trades.

    Deduplicates close trades by ClosePositionId since Saxo repeats the
    full close quantity on each row when a single sell closes multiple lots.
    """
    seen_close_ids = set()

    for _, row in df.iterrows():
        trade_open = KDVPSecurityOpen(
            row["Trade Date Open"].date(),
            row["QuantityOpen"],
            row["Open Price"],
            0,
            "B",
        )
        doh_kdvp.add_trade(row.Symbol, trade_open, row["Asset type"] != "Stock")

        close_id = row["ClosePositionId"]
        if close_id not in seen_close_ids:
            seen_close_ids.add(close_id)

            group = df[df["ClosePositionId"] == close_id]
            close_quantities = group["QuantityClose"].unique()
            if len(close_quantities) > 1:
                print(f"Error: Inconsistent close quantities for ClosePositionId {close_id}:")
                for _, r in group.iterrows():
                    print(f"  OpenPositionId {r['OpenPositionId']}: QuantityClose={r['QuantityClose']}")
                sys.exit(1)

            total_gain = group["Gain"].sum()
            trade_close = KDVPSecurityClose(
                row["Trade Date Close"].date(),
                row["QuantityClose"],
                row["Close Price"],
                0,
                total_gain < 0,
            )
            doh_kdvp.add_trade(row.Symbol, trade_close, row["Asset type"] != "Stock")
