import csv

import pandas as pd

from interest import Interest, InterestType
from date_utils import parse_pandas_date_column


def process_revolut_csv(file_path) -> list[Interest]:
    # Skip the first 13 rows and use the column names from line 14
    df = pd.read_csv(
        file_path,
        skiprows=13,  # Skip the first 13 rows
        quoting=csv.QUOTE_MINIMAL,  # Handle quoted fields
        # The column names should be: Date, Description, Value, Price per share, Quantity per share
    )

    # Create explicit copies of the filtered DataFrames
    interest_df = df[df["Description"].str.contains("Interest PAID EUR")].copy()
    interest_df = parse_pandas_date_column(interest_df, "Date", None, "Revolut interest date")
    interest_df["Value"] = (
        interest_df["Value"].str.replace("€", "").str.replace(",", "").astype(float)
    )
    total_interest = round(abs(interest_df["Value"].sum()), 2)

    # Do the same for fees
    fees_df = df[df["Description"].str.contains("Service Fee Charged")].copy()
    fees_df["Value"] = (
        fees_df["Value"].str.replace("€", "").str.replace(",", "").astype(float)
    )
    total_fees = round(abs(fees_df["Value"].sum()), 2)

    # And for the "SELL EUR" case
    sell_df = df[df["Description"].str.contains("SELL EUR")].copy()
    sell_df["Value"] = (
        sell_df["Value"].str.replace("€", "").str.replace(",", "").astype(float)
    )
    total_sell = round(abs(sell_df["Value"].sum()), 2)

    print(
        f"[Revolut] total interest: {total_interest} EUR, total fees: {total_fees} EUR, total sell: {total_sell} EUR"
    )

    return [
        Interest(
            date=row["Date"].strftime(
                "%Y-%m-%d"
            ),  # TODO: this should be passed as date object and only converted at writing
            identification_number="305799582",
            name="Revolut Securities Europe UAB",
            address="Konstitucijos ave. 21B, Vilnius, 08130",
            country="LT",
            type=InterestType.FUND_INTEREST,
            value=row["Value"],
            country2="LT",
        )
        for _, row in interest_df.iterrows()
    ]
