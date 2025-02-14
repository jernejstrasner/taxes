import pandas as pd

from currency import Currency
from interest import Interest, InterestType


def process_saxo_xlsx(file_path) -> list[Interest]:
    # Open interest xlsx file
    df = pd.read_excel(file_path, sheet_name="Interest Details")

    # Parse the date values in GMT and convert to CET/CEST accounting for DST
    df["Date"] = (
        pd.to_datetime(df["Calculation dateGMT"], format="%d-%b-%Y")
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
