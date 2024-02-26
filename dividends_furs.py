import sys

import pandas as pd
import currency
from cache import CompanyCache, CountryCache
import argparse
from finance import FinanceData
from xml_output import XML, XMLWriter
from taxpayer import Taxpayer
from lxml.builder import ElementMaker


def dividends(args, company_cache, country_cache):
    # Open dividends xlsx file
    df = pd.read_excel(args.dividends, sheet_name="Share Dividends")
    print("Opened dividends file: ", args.dividends)

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
    furs_df["Date"] = pd.to_datetime(furs_df["Date"], format="%d-%b-%Y").dt.strftime(
        "%Y-%m-%d"
    )

    # Get the exchange rate for the dates in the Date column
    exchange_rates = currency.get_currency(furs_df["Date"].unique())

    finance_data = FinanceData(company_cache)
    symbols = furs_df["Symbol"].unique()
    finance_data.fetch_info(symbols)

    def process_row(row):
        # Dividend amount
        if row["Value"].startswith("USD"):
            value = float(row["Value"].replace("USD", ""))
            row["Value"] = value / exchange_rates[row["Date"]]["USD"]
        elif row["Value"].startswith("CAD"):
            value = float(row["Value"].replace("CAD", ""))
            row["Value"] = value / exchange_rates[row["Date"]]["CAD"]
        elif row["Value"].startswith("EUR"):
            row["Value"] = float(row["Value"].replace("EUR", ""))
        else:
            print("Currency not supported: ", row["Value"])
            sys.exit(1)
        # Tax witheld at source
        foreign_tax = row["ForeignTax"].lstrip(" +-")
        if foreign_tax.startswith("USD"):
            value = float(foreign_tax.replace("USD", ""))
            row["ForeignTax"] = value / exchange_rates[row["Date"]]["USD"]
        elif foreign_tax.startswith("CAD"):
            value = float(foreign_tax.replace("CAD", ""))
            row["ForeignTax"] = value / exchange_rates[row["Date"]]["CAD"]
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

    # Load taxpayer data
    taxpayer = Taxpayer()
    taxpayer.get_input()

    # Write the final XML file
    xml = XML(taxpayer, furs_df, args.output or "dividends_furs.xml", args.correction)
    xml.write()
    xml.verify("data/Doh_Div_3.xsd")


def gains(args):
    # Open gains xlsx file
    df = pd.read_excel(args.gains, sheet_name="ClosedPositions")
    print("Opened gains file: ", args.gains)

    # Parse the date values in the Date column and convert them to the format YYYY-MM-DD
    df["Trade Date Open"] = pd.to_datetime(
        df["Trade Date Open"], format="%d-%b-%Y"
    ).dt.strftime("%Y-%m-%d")
    df["Trade Date Close"] = pd.to_datetime(
        df["Trade Date Close"], format="%d-%b-%Y"
    ).dt.strftime("%Y-%m-%d")

    # Get the exchange rate for the dates in the Date column
    dates = list(df["Trade Date Open"]) + list(df["Trade Date Close"])
    exchange_rates = currency.get_currency(dates)

    def process_row(row):
        # Process the currency of the trade
        conversion_open = 1
        conversion_close = 1
        if row["Instrument currency"] == "USD":
            conversion_open = exchange_rates[row["Trade Date Open"]]["USD"]
            conversion_close = exchange_rates[row["Trade Date Close"]]["USD"]
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

    # Load taxpayer data
    taxpayer = Taxpayer()
    taxpayer.get_input()

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
                EDP.birthDate(taxpayer.birthDate),
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
                        E.ItemID(str(i+1)),
                        E.InventoryListType("PLVP"),
                        E.Name(row["Symbol"]),
                        E.HasForeignTax("false"),
                        E.HasLossTransfer("false"),
                        E.ForeignTransfer("false"),
                        E.TaxDecreaseConformance("false"),
                        E.Securities(
                            E.Code(row["Symbol"]),
                            E.IsFond("false" if row["Asset type"] == "Stock" else "true"),
                            E.Row(
                                E.ID("0"),
                                E.Purchase(
                                    E.F1(row["Trade Date Open"]),
                                    E.F2("B"),
                                    E.F3("{:.4f}".format(row["QuantityOpen"])),
                                    E.F4("{:.4f}".format(row["Open Price"])),
                                ),
                                E.F8("{:.4f}".format(row["QuantityOpen"])),
                            ),
                            E.Row(
                                E.ID("1"),
                                E.Sale(
                                    E.F6(row["Trade Date Close"]),
                                    E.F7("{:.4f}".format(row["QuantityClose"])),
                                    E.F9("{:.4f}".format(row["Close Price"])),
                                    E.F10("false" if row["Gain"] > 0 else "true")
                                ),
                                E.F8("{:.4f}".format(row["QuantityOpen"] - row["QuantityClose"])),
                            ),
                        ),
                    )
                    for i, row in df.iterrows()
                ],
            ),
        ),
    )

    # Write the final XML file
    xml = XMLWriter(args.output or "gains_furs.xml")
    xml.write(envelope)
    xml.verify("data/Doh_KDVP_9.xsd")


def main():
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--broker", help="Name of the broker", required=True, choices=["saxo"]
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dividends", help="Path to the dividends xlsx file")
    group.add_argument("--gains", help="Path to the gains xlsx file")
    parser.add_argument(
        "--additional-info",
        help="Path to the additional info xlsx file with ISINs and addresses of the payers",
        required=False,
    )
    parser.add_argument("--output", help="Path to the output xml file", required=False)
    parser.add_argument("--correction", help="Is this a correction?", action="store_true")
    args = parser.parse_args()

    # Create a cache object
    company_cache = CompanyCache("company_cache.xml")
    if args.additional_info:
        company_cache.fill_isin_cache(args.additional_info)
        company_cache.flush()
    country_cache = CountryCache("country_cache.xml")

    # Process based on input
    if args.dividends:
        dividends(args, company_cache, country_cache)
    elif args.gains:
        gains(args)
    else:
        print("No input file provided")
        sys.exit(1)

    # Write the caches
    company_cache.flush()
    country_cache.flush()


if __name__ == "__main__":
    main()
