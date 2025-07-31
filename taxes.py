import argparse
import sys

import pandas as pd
import requests
from lxml.builder import ElementMaker

from cache import CompanyCache, CountryCache
from cache_utils import cache_daily
from currency import Currency
from finance import FinanceData
from gains import DohKDVP, KDVPSecurityClose, KDVPSecurityOpen
from interest import DohObr
from revolut import process_revolut_csv
from saxobank import process_saxo_xlsx
from taxpayer import Taxpayer
from xml_output import XML, XMLWriter
from date_utils import parse_pandas_date_column
from isin_utils import prompt_for_isin


def dividends(args, taxpayer, company_cache, country_cache):
    # Open dividends xlsx file
    df = pd.read_excel(args.saxo, sheet_name="Share Dividends")
    print("Opened dividends file: ", args.saxo)

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

    # Add a couple more columns that are required by the FURS XML schema and set them as null
    furs_df["ReliefStatement"] = None
    furs_df["PayerAddress"] = None
    furs_df["PayerIdentificationNumber"] = None
    furs_df["PayerCountry"] = None

    # Parse the date values in the Date column and convert them to the format YYYY-MM-DD
    furs_df = parse_pandas_date_column(furs_df, "Date", ["%d-%b-%Y"], "dividend payment")

    # Get the exchange rate for the dates in the Date column
    dates = [d.date() for d in furs_df["Date"].unique()]
    currency = Currency(dates, ["USD", "CAD"])

    finance_data = FinanceData(company_cache)
    symbols = furs_df["Symbol"].unique()
    finance_data.fetch_info(symbols)

    def process_row(row):
        # Dividend amount
        if row["Value"].startswith("USD"):
            value = float(row["Value"].replace("USD", ""))
            row["Value"] = value / currency.get_rate(row["Date"].date(), "USD")
        elif row["Value"].startswith("CAD"):
            value = float(row["Value"].replace("CAD", ""))
            row["Value"] = value / currency.get_rate(row["Date"].date(), "CAD")
        elif row["Value"].startswith("EUR"):
            row["Value"] = float(row["Value"].replace("EUR", ""))
        else:
            print("Currency not supported: ", row["Value"])
            sys.exit(1)
        # Tax witheld at source
        foreign_tax = row["ForeignTax"].lstrip(" +-")
        if foreign_tax.startswith("USD"):
            value = float(foreign_tax.replace("USD", ""))
            row["ForeignTax"] = value / currency.get_rate(row["Date"].date(), "USD")
        elif foreign_tax.startswith("CAD"):
            value = float(foreign_tax.replace("CAD", ""))
            row["ForeignTax"] = value / currency.get_rate(row["Date"].date(), "CAD")
        elif foreign_tax.startswith("EUR"):
            row["ForeignTax"] = float(foreign_tax.replace("EUR", ""))
        else:
            print("Currency not supported: ", row["ForeignTax"])
            sys.exit(1)
        # Payer identification number
        if not row["PayerIdentificationNumber"]:
            isin = finance_data.get_isin(row["Symbol"])
            if not isin:
                isin = prompt_for_isin(row["PayerName"])
                company_cache.set_isin(row["Symbol"], isin)
            row["PayerIdentificationNumber"] = isin
        # Payer country
        if not row["PayerCountry"]:
            row["PayerCountry"] = row["PayerIdentificationNumber"][:2]
        # Payer address
        if not row["PayerAddress"]:
            address = finance_data.get_address(row["Symbol"])
            if not address:
                address = input(
                    "Enter the payer address for {}: ".format(row["PayerName"])
                )
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

    # Filter the rows to only include the ones with the event "Cash dividend"
    furs_df = furs_df[furs_df["Event"] == "Cash dividend"]
    # Process the rows (convert currencies, get missing data from the user, etc.)
    furs_df = furs_df.apply(process_row, axis=1)

    # Output some informational info (e.g. the total amount of dividends)
    total_dividends = round(furs_df["Value"].sum(), 2)
    total_foreign_tax = round(furs_df["ForeignTax"].sum(), 2)
    print("Total dividends: ", total_dividends, "EUR")
    print("Total foreign tax: ", total_foreign_tax, "EUR")

    # Write the final XML file
    xml = XML(
        taxpayer,
        furs_df,  # type: ignore
        args.output or "data/dividends_furs.xml",
        args.correction,
    )
    xml.write()
    xml.verify("data/Doh_Div_3.xsd")


def gains(args, taxpayer):
    # Open gains xlsx file
    df = pd.read_excel(args.saxo, sheet_name="ClosedPositions")
    print("Opened gains file: ", args.saxo)

    # Parse the date values in the Date column and convert them to the format YYYY-MM-DD
    df = parse_pandas_date_column(df, "Trade Date Open", ["%d-%b-%Y"], "trade open date")
    df = parse_pandas_date_column(df, "Trade Date Close", ["%d-%b-%Y"], "trade close date")

    # Get the exchange rate for the dates in the Date column
    dates = list(df["Trade Date Open"]) + list(df["Trade Date Close"])
    # Convert string dates to datetime.date objects before creating the set
    currency = Currency([d.date() for d in list(set(dates))], ["USD", "CAD"])

    def process_row(row):
        # Process the currency of the trade
        conversion_open = 1
        conversion_close = 1
        if row["Instrument currency"] == "USD":
            conversion_open = currency.get_rate(row["Trade Date Open"].date(), "USD")
            conversion_close = currency.get_rate(row["Trade Date Close"].date(), "USD")
        elif row["Instrument currency"] == "CAD":
            conversion_open = currency.get_rate(row["Trade Date Open"].date(), "CAD")
            conversion_close = currency.get_rate(row["Trade Date Close"].date(), "CAD")
        row["Open Price"] = float(row["Open Price"]) / conversion_open
        row["Close Price"] = float(row["Close Price"]) / conversion_close
        # Clean up the symbol
        row["Symbol"] = row["Instrument Symbol"].split(":")[0]
        # Clean up quantities
        row["QuantityOpen"] = float(row["Quantity Open"])
        row["QuantityClose"] = abs(float(row["QuantityClose"]))
        # Gain
        row["Gain"] = (row["QuantityClose"] * row["Close Price"]) - (
            row["QuantityOpen"] * row["Open Price"]
        )
        return row

    # Process the rows (convert currencies, get missing data from the user, etc.)
    df = df.apply(process_row, axis=1)

    # Output some informational info (e.g. the total amount of gains and losses)
    print("Number of trades: ", df.shape[0])
    print("Total gains: ", df["Gain"].sum())

    # Convert the dataframe to typed DohKDVP objects
    doh_kdvp = DohKDVP()
    for i, row in df.iterrows():
        trade_open = KDVPSecurityOpen(
            row["Trade Date Open"].date(),
            row["QuantityOpen"],
            row["Open Price"],
            0,
            "B",
        )
        doh_kdvp.add_trade(row.Symbol, trade_open, row["Asset type"] != "Stock")
        trade_close = KDVPSecurityClose(
            row["Trade Date Close"].date(),
            row["QuantityClose"],
            row["Close Price"],
            0,
            row["Gain"] < 0,
        )
        doh_kdvp.add_trade(row.Symbol, trade_close, row["Asset type"] != "Stock")

    # Generate the XML structure
    EDP_NS = "http://edavki.durs.si/Documents/Schemas/EDP-Common-1.xsd"
    E = ElementMaker(nsmap={"edp": EDP_NS})
    EDP = ElementMaker(namespace=EDP_NS)
    envelope = E.Envelope(
        {"xmlns": "http://edavki.durs.si/Documents/Schemas/Doh_KDVP_9.xsd"},
        EDP.Header(
            EDP.taxpayer(
                EDP.taxNumber(taxpayer.taxNumber),
                EDP.taxpayerType("FO"),
                EDP.name(taxpayer.name),
                EDP.address1(taxpayer.address),
                EDP.city(taxpayer.city),
                EDP.postNumber(taxpayer.postNumber),
                EDP.birthDate(taxpayer.get_birth_date().strftime("%Y-%m-%d")),
            ),
        ),
        EDP.AttachmentList(),
        EDP.Signatures(),
        E.body(
            EDP.bodyContent(),
            E.Doh_KDVP(
                E.KDVP(
                    E.DocumentWorkflowID("O"),
                    E.Year(str(pd.Timestamp.now().year - 1)),
                    E.PeriodStart(str(pd.Timestamp.now().year - 1) + "-01-01"),
                    E.PeriodEnd(str(pd.Timestamp.now().year - 1) + "-12-31"),
                    E.IsResident("true"),
                    E.TelephoneNumber(taxpayer.phone),
                    E.SecurityCount(str(df.shape[0])),
                    E.SecurityShortCount("0"),
                    E.SecurityWithContractCount("0"),
                    E.SecurityWithContractShortCount("0"),
                    E.ShareCount("0"),
                    E.SecurityCapitalReductionCount("0"),
                    E.Email(taxpayer.email),
                ),
                *[
                    E.KDVPItem(
                        E.ItemID(str(i + 1)),
                        E.InventoryListType("PLVP"),
                        E.Name(item.name),
                        E.HasForeignTax("false"),
                        E.HasLossTransfer("false"),
                        E.ForeignTransfer("false"),
                        E.TaxDecreaseConformance("false"),
                        E.Securities(
                            E.Code(item.name),
                            E.IsFond(str(item.is_fond).lower()),
                            *[
                                E.Row(
                                    E.ID(str(i)),
                                    E.Sale(
                                        E.F6(trade.date.strftime("%Y-%m-%d")),
                                        E.F7("{:.4f}".format(trade.quantity)),
                                        E.F9("{:.4f}".format(trade.value)),
                                        E.F10("true"),
                                    )
                                    if isinstance(trade, KDVPSecurityClose)
                                    else E.Purchase(
                                        E.F1(trade.date.strftime("%Y-%m-%d")),
                                        E.F2(trade.acquisition_type),
                                        E.F3("{:.4f}".format(trade.quantity)),
                                        E.F4("{:.4f}".format(trade.value)),
                                    ),
                                    E.F8("{:.4f}".format(trade.stock)),
                                )
                                for i, trade in enumerate(item.securities)
                            ],
                        ),
                    )
                    for i, item in enumerate(doh_kdvp.items.values())
                ],
            ),
        ),
    )

    # Write the final XML file
    xml = XMLWriter(args.output or "data/gains_furs.xml")
    xml.write(envelope)
    xml.verify("data/Doh_KDVP_9.xsd")


def interest(args, taxpayer):
    # Create a DohObr object
    doh_obr = DohObr(args.period, taxpayer)

    ### Saxobank
    saxobank_interests = process_saxo_xlsx(args.saxo)
    for interest in saxobank_interests:
        doh_obr.add_interest(interest)

    ### Revolut
    revolut_interests = process_revolut_csv(args.revolut)
    for interest in revolut_interests:
        doh_obr.add_interest(interest)

    # Condense the interests to one entry per payer
    if args.condensed:
        doh_obr.condense_interests()

    # Write the final XML file
    xml = XMLWriter(args.output or "data/interest_furs.xml")
    xml.write(doh_obr.to_xml())
    xml.verify("data/Doh_Obr_2.xsd")


@cache_daily("currency.cache")
def download_currency():
    print("Downloading latest currency data...")
    Currency.download_currency()
    print("Downloaded latest currency data")


@cache_daily("schemas.cache")
def download_schemas():
    # Download the latest XML schemas
    print("Downloading XML schemas...")
    schemas = ["Doh_Div_3.xsd", "Doh_KDVP_9.xsd", "EDP-Common-1.xsd", "Doh_Obr_2.xsd"]
    for schema in schemas:
        url = f"https://edavki.durs.si/Documents/Schemas/{schema}"
        response = requests.get(url)
        with open(f"data/{schema}", "wb") as f:
            f.write(response.content)
    print("Downloaded XML schemas")


def main():
    # Parse the arguments
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dividends", action="store_true")
    group.add_argument("--gains", action="store_true")
    group.add_argument("--interest", action="store_true")
    parser.add_argument(
        "--condensed",
        action="store_true",
        help="Condenses interest to one entry per payer",
    )

    parser.add_argument("--saxo", help="Path to the Saxobank xlsx file")
    parser.add_argument("--revolut", help="Path to the Revolut tax summary csv file")

    parser.add_argument(
        "--additional-info",
        help="Path to the additional info Saxobank xlsx file with ISINs and addresses of the payers",
        required=False,
    )

    parser.add_argument("--period", help="Period of the tax report", required=False)
    parser.add_argument("--output", help="Path to the output xml file", required=False)
    parser.add_argument(
        "--correction",
        help="Is this a correction of an already submitted report?",
        action="store_true",
    )
    parser.add_argument(
        "--taxpayer", help="Path to the taxpayer xml file", required=False
    )
    args = parser.parse_args()

    # Download fresh currency data if needed
    download_currency()

    # Download the latest XML schemas
    download_schemas()

    # Create a cache object
    company_cache = CompanyCache("company_cache.xml")
    if args.additional_info:
        company_cache.fill_isin_cache(args.additional_info)
        company_cache.flush()
    country_cache = CountryCache("country_cache.xml")

    # Load taxpayer data
    taxpayer = Taxpayer(args)

    # Process based on input
    if args.dividends:
        dividends(args, taxpayer, company_cache, country_cache)
    elif args.gains:
        gains(args, taxpayer)
    elif args.interest:
        interest(args, taxpayer)
    else:
        print("No input file provided")
        sys.exit(1)

    # Write the caches
    company_cache.flush()
    country_cache.flush()


if __name__ == "__main__":
    main()
