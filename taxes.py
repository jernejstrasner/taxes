import argparse
import sys

import pandas as pd
import requests
from lxml.builder import ElementMaker

from cache import CompanyCache, CountryCache
from cache_utils import cache_daily
from currency import Currency
from finance import FinanceData
from gains import DohKDVP, KDVPSecurityClose
from ibkr import process_ibkr_xml, ibkr_trades_to_kdvp
from interest import DohObr
from revolut import process_revolut_csv
from saxobank import process_saxo_xlsx, saxo_trades_to_kdvp
from taxpayer import Taxpayer
from xml_output import XML, XMLWriter
from date_utils import parse_pandas_date_column
from isin_utils import prompt_for_isin
from network_utils import download_or_exit, validate_download
from error_utils import file_error, data_error
from file_utils import get_output_filename, ensure_directory_exists


def dividends(args, taxpayer, company_cache, country_cache):
    # Open dividends xlsx file
    try:
        df = pd.read_excel(args.saxo, sheet_name="Share Dividends")
        print("Opened dividends file: ", args.saxo)
    except FileNotFoundError:
        file_error(
            "reading", args.saxo, "File not found",
            [f"Check that the file path '{args.saxo}' is correct",
             "Ensure the Saxo Bank Excel file is in the expected location"]
        )
    except Exception as e:
        file_error(
            "reading", args.saxo, str(e),
            ["Ensure the file is a valid Excel file (.xlsx)",
             "Check that the file contains a 'Share Dividends' sheet",
             "Verify the file is not corrupted or password protected"]
        )

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
            print(f"Error: Unsupported currency in dividend value: {row['Value']}")
            print(f"This occurred for dividend from {row['PayerName']} on {row['Date']}")
            print("Currently supported currencies: USD, CAD, EUR")
            print("Please ensure your data uses one of these currencies or update the code")
            sys.exit(1)
        # Tax withheld at source
        if pd.isna(row["ForeignTax"]) or row["ForeignTax"] is None:
            print(f"Error: Missing foreign tax value for dividend from {row['PayerName']} on {row['Date']}")
            print("Expected format: currency code followed by amount (e.g., 'USD 10.00')")
            print("If no tax was withheld, the field should contain 'USD 0' or similar, not be empty")
            sys.exit(1)
        foreign_tax = str(row["ForeignTax"]).lstrip(" +-")
        if foreign_tax.startswith("USD"):
            value = float(foreign_tax.replace("USD", ""))
            row["ForeignTax"] = value / currency.get_rate(row["Date"].date(), "USD")
        elif foreign_tax.startswith("CAD"):
            value = float(foreign_tax.replace("CAD", ""))
            row["ForeignTax"] = value / currency.get_rate(row["Date"].date(), "CAD")
        elif foreign_tax.startswith("EUR"):
            row["ForeignTax"] = float(foreign_tax.replace("EUR", ""))
        else:
            print(f"Error: Unsupported currency in foreign tax: {row['ForeignTax']}")
            print(f"This occurred for dividend from {row['PayerName']} on {row['Date']}")
            print("Currently supported currencies for foreign tax: USD, CAD, EUR")
            print("Please check your Saxo Bank export format or update the code")
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
    output_file = get_output_filename(
        args.output, 
        "dividends_furs", 
        "dividends tax report",
        use_timestamp=not args.no_timestamp
    )
    ensure_directory_exists(output_file)
    
    xml = XML(
        taxpayer,
        furs_df,  # type: ignore
        output_file,
        args.correction,
    )
    xml.write()
    xml.verify("data/Doh_Div_3.xsd")
    print(f"Dividends tax report saved to: {output_file}")


def gains(args, taxpayer):
    doh_kdvp = DohKDVP()
    trade_count = 0

    # Process IBKR trades if provided
    if args.ibkr:
        ibkr_trades = process_ibkr_xml(args.ibkr)
        kdvp_trades = ibkr_trades_to_kdvp(ibkr_trades)
        for isin, trade, is_fond in kdvp_trades:
            doh_kdvp.add_trade(isin, trade, is_fond)
        trade_count += len(ibkr_trades)

    # Process Saxo trades if provided
    if args.saxo:
        try:
            df = pd.read_excel(args.saxo, sheet_name="ClosedPositions")
            print("Opened gains file: ", args.saxo)
        except FileNotFoundError:
            file_error(
                "reading", args.saxo, "File not found",
                [f"Check that the file path '{args.saxo}' is correct",
                 "Ensure the Saxo Bank Excel file is in the expected location"]
            )
        except Exception as e:
            file_error(
                "reading", args.saxo, str(e),
                ["Ensure the file is a valid Excel file (.xlsx)",
                 "Check that the file contains a 'ClosedPositions' sheet",
                 "Verify the file is not corrupted or password protected"]
            )

        df = parse_pandas_date_column(df, "Trade Date Open", ["%d-%b-%Y"], "trade open date")
        df = parse_pandas_date_column(df, "Trade Date Close", ["%d-%b-%Y"], "trade close date")

        invalid_dates = df[df["Trade Date Close"] < df["Trade Date Open"]]
        if not invalid_dates.empty:
            print("Error: Found trades where close date is before open date:")
            for _, row in invalid_dates.iterrows():
                print(f"  - {row['Instrument Symbol']}: opened {row['Trade Date Open'].date()}, closed {row['Trade Date Close'].date()}")
            print("Please check your Saxo Bank export for data errors")
            sys.exit(1)

        dates = list(df["Trade Date Open"]) + list(df["Trade Date Close"])
        currency = Currency([d.date() for d in list(set(dates))], ["USD", "CAD"])

        def process_row(row):
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
            row["Symbol"] = row["Instrument Symbol"].split(":")[0]
            row["QuantityOpen"] = float(row["Quantity Open"])
            row["QuantityClose"] = abs(float(row["QuantityClose"]))
            row["Gain"] = float(row["PnLAccountCurrency"])
            return row

        df = df.apply(process_row, axis=1)

        print("Number of Saxo trades: ", df.shape[0])
        print("Total Saxo gains: ", df["Gain"].sum())

        saxo_trades_to_kdvp(df, doh_kdvp)
        trade_count += df.shape[0]

    if trade_count == 0:
        print("Error: No trades to process")
        print("Please provide at least one of: --saxo or --ibkr")
        sys.exit(1)

    print(f"Total securities: {len(doh_kdvp.items)}")

    # Validate no security has a negative running total (indicates unhandled stock split)
    position_errors = doh_kdvp.validate_positions()
    if position_errors:
        for error in position_errors:
            print(f"Error: {error}")
        print("  This usually indicates an unhandled stock split or corporate action.")
        print("  The sell quantity exceeds total purchased shares.")
        print("  Please adjust quantities in your broker export to account for the split.")
        sys.exit(1)

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
                    E.SecurityCount(str(len(doh_kdvp.items))),
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
                                    E.ID(str(j)),
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
                                for j, trade in enumerate(item.securities)
                            ],
                        ),
                    )
                    for i, item in enumerate(doh_kdvp.items.values())
                ],
            ),
        ),
    )

    output_file = get_output_filename(
        args.output,
        "gains_furs",
        "capital gains tax report",
        use_timestamp=not args.no_timestamp
    )
    ensure_directory_exists(output_file)

    xml = XMLWriter(output_file)
    xml.write(envelope)
    xml.verify("data/Doh_KDVP_9.xsd")
    print(f"Capital gains tax report saved to: {output_file}")


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
    output_file = get_output_filename(
        args.output, 
        "interest_furs", 
        "interest tax report",
        use_timestamp=not args.no_timestamp
    )
    ensure_directory_exists(output_file)
    
    xml = XMLWriter(output_file)
    xml.write(doh_obr.to_xml())
    xml.verify("data/Doh_Obr_2.xsd")
    print(f"Interest tax report saved to: {output_file}")


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
        download_or_exit(
            url=url,
            output_file=f"data/{schema}",
            timeout=30,
            max_retries=3,
            context=f"FURS schema {schema}"
        )
        validate_download(f"data/{schema}", min_size=500, context=f"schema {schema}")
    print("All XML schemas downloaded successfully")


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
    parser.add_argument("--ibkr", help="Path to the IBKR Flex Query XML file")

    parser.add_argument(
        "--additional-info",
        help="Path to the additional info Saxobank xlsx file with ISINs and addresses of the payers",
        required=False,
    )

    parser.add_argument("--period", help="Period of the tax report", required=False)
    parser.add_argument("--output", help="Path to the output xml file", required=False)
    parser.add_argument(
        "--no-timestamp", 
        action="store_true", 
        help="Don't add timestamp to output filenames (will overwrite existing files)",
        required=False
    )
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
        print("Error: No input file provided")
        print("")
        print("Please specify one of the following options:")
        print("  --saxo FILE        Process Saxo Bank Excel file")
        print("  --revolut FILE     Process Revolut CSV file")
        print("  --download-schemas Download XML schemas from FURS")
        print("  --download-currency Download currency rates from Bank of Slovenia")
        print("")
        print("Use --help for more information about available options")
        sys.exit(1)

    # Write the caches
    company_cache.flush()
    country_cache.flush()


if __name__ == "__main__":
    main()
