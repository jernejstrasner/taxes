import sys

import pandas as pd
import currency
from cache import CompanyCache, CountryCache
import argparse
from finance import FinanceData
from xml_output import XML
from taxpayer import Taxpayer

# Parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument("dividends", help="Path to the dividends xlsx file")
parser.add_argument(
    "--additional-info",
    help="Path to the additional info xlsx file with ISINs and addresses of the payers",
    required=False,
)
parser.add_argument("--output", help="Path to the output xml file", required=False)
args = parser.parse_args()

# Open dividends xlsx file
df = pd.read_excel(args.dividends, sheet_name="Share Dividends")
print("Opened dividends file: ", args.dividends)

# Create a cache object
company_cache = CompanyCache("company_cache.xml")
if args.additional_info:
    company_cache.fill_isin_cache(args.additional_info)
    company_cache.flush()
country_cache = CountryCache("country_cache.xml")

# Rename the columns
furs_df = df.rename(
    columns={
        "Instrument": "PayerName",
        "Pay Date": "Date",
        "Dividend amount": "Value",
        "Withholding tax amount": "ForeignTax",
        "Instrument Symbol": "Symbol",
    }
)

# Parse the date values in the Date column and convert them to the format YYYY-MM-DD
furs_df["Date"] = pd.to_datetime(furs_df["Date"], format="%d-%b-%Y").dt.strftime(
    "%Y-%m-%d"
)

# Add a couple more columns that are required by the FURS XML schema and set them as null
furs_df["ReliefStatement"] = None
furs_df["PayerAddress"] = None
furs_df["PayerIdentificationNumber"] = None
furs_df["PayerCountry"] = None

# Get the exchange rate for the dates in the Date column
exchange_rates = currency.get_currency(furs_df["Date"].unique())

finance_data = FinanceData(company_cache)
symbols = furs_df["Symbol"].unique()
finance_data.fetch_info(symbols)


def process_row(row):
    # Dividend amount
    if row["Value"].startswith("USD"):
        value = float(row["Value"].replace("USD", ""))
        row["Value"] = value * exchange_rates[row["Date"]]["USD"]
    elif row["Value"].startswith("CAD"):
        value = float(row["Value"].replace("CAD", ""))
        row["Value"] = value * exchange_rates[row["Date"]]["CAD"]
    elif row["Value"].startswith("EUR"):
        row["Value"] = float(row["Value"].replace("EUR", ""))
    else:
        print("Currency not supported: ", row["Value"])
        sys.exit(1)
    # Tax witheld at source
    foreign_tax = row["ForeignTax"].lstrip(" +\-")
    if foreign_tax.startswith("USD"):
        value = float(foreign_tax.replace("USD", ""))
        row["ForeignTax"] = value * exchange_rates[row["Date"]]["USD"]
    elif foreign_tax.startswith("CAD"):
        value = float(foreign_tax.replace("CAD", ""))
        row["ForeignTax"] = value * exchange_rates[row["Date"]]["CAD"]
    elif foreign_tax.startswith("EUR"):
        row["ForeignTax"] = float(foreign_tax.replace("EUR", ""))
    else:
        print("Currency not supported: ", row["ForeignTax"])
        sys.exit(1)
    # Payer identification number
    if not row["PayerIdentificationNumber"]:
        isin = finance_data.get_isin(row["Symbol"])
        if not isin:
            isin = input("Enter the ISIN for {}: ".format(row["PayerName"]))
            company_cache.set_isin(row["Symbol"], isin)
        row["PayerIdentificationNumber"] = isin
    # Payer country
    if not row["PayerCountry"]:
        row["PayerCountry"] = row["PayerIdentificationNumber"][:2]
    # Payer address
    if not row["PayerAddress"]:
        address = finance_data.get_address(row["Symbol"])
        if not address:
            address = input("Enter the payer address for {}: ".format(row["PayerName"]))
            company_cache.set_address(row["Symbol"], address)
        row["PayerAddress"] = address
    # Relief statement
    if not row["ReliefStatement"]:
        statement = country_cache.get_relief_statement(row["PayerCountry"])
        if not statement:
            statement = input(
                "Enter the relief statement for country {}: ".format(
                    row["PayerCountry"]
                )
            )
            country_cache.set_relief_statement(row["PayerCountry"], statement)
        row["ReliefStatement"] = statement
    # Flush the caches for each rown
    company_cache.flush()
    country_cache.flush()
    return row


# Process the rows (convert currencies, get missing data from the user, etc.)
furs_df = furs_df.apply(process_row, axis=1)

# Output some informational info (e.g. the total amount of dividends)
total_dividends = round(furs_df["Value"].sum(), 2)
total_foreign_tax = round(furs_df["ForeignTax"].sum(), 2)
print("Total dividends: ", total_dividends, "EUR")
print("Total foreign tax: ", total_foreign_tax, "EUR")

# Load taxpayer data
taxpayer = Taxpayer()
taxpayer.get_input()

# Write the final XML file
xml = XML(taxpayer, furs_df, args.output or "dividends_furs.xml")
xml.write()
xml.verify("data/Doh_Div_3.xsd")

# Write the caches
company_cache.flush()
country_cache.flush()
