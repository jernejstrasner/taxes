import sys

import pandas as pd
from lxml import etree
from lxml.builder import ElementMaker
import currency
from cache import Cache
import argparse
from finance import FinanceData

class XMLNamespaces:
    main = "http://edavki.durs.si/Documents/Schemas/Doh_Div_3.xsd"
    edp = "http://edavki.durs.si/Documents/Schemas/EDP-Common-1.xsd"

class Taxpayer:
    def __init__(self, taxpayer_file):
        self.taxpayer = etree.parse(taxpayer_file)

    # Creates a header XML element compatible with the FURS XML schema
    def get_header(self):
        E = ElementMaker(namespace=XMLNamespaces.edp)
        root = E.taxpayer(
            E.taxNumber(self.taxpayer.findtext("taxNumber")),
            E.taxpayerType("FO"),
            E.name(self.taxpayer.findtext("name")),
            E.address1(self.taxpayer.findtext("address")),
            E.city(self.taxpayer.findtext("city")),
            E.postNumber(self.taxpayer.findtext("postNumber")),
            E.postName(self.taxpayer.findtext("postName"))
        )
        return root

    # Creates the first body element Doh_Div compatible with the FURS XML schema
    def get_doh_div(self):
        E = ElementMaker()
        root = E.Doh_Div(
            E.Period(str(pd.Timestamp.now().year - 1)),
            E.EmailAddress(self.taxpayer.findtext("email")),
            E.PhoneNumber(self.taxpayer.findtext("phone")),
            E.ResidentCountry("SI"),
            E.IsResident("true"),
            E.SelfReport("false"),
            E.WfTypeU("false"),
        )
        return root

def write_xml(dividends, path):
    # Write the xml to a file pretty printed with an xml declaration
    with etree.xmlfile(path, encoding="utf-8") as xf:
        xf.write_declaration()
        E = ElementMaker(nsmap={"edp": XMLNamespaces.edp})
        EDP = ElementMaker(namespace=XMLNamespaces.edp)
        envelope = E.Envelope(
            {"xmlns": XMLNamespaces.main},
            EDP.Header(
                taxpayer.get_header(),
                EDP.Workflow(
                    EDP.DocumentWorkflowID("O"),
                    EDP.DocumentWorkflowName(),
                ),
                EDP.domain("edavki.durs.si"),
            ),
            EDP.AttachmentList(),
            EDP.Signatures(),
                E.body(
                    taxpayer.get_doh_div(),
                    *[E.Dividend(
                        E.Date(row.Date),
                        E.PayerIdentificationNumber(row.PayerIdentificationNumber),
                        E.PayerName(row.PayerName),
                        E.PayerAddress(row.PayerAddress),
                        E.PayerCountry(row.PayerCountry),
                        E.Type("1"),
                        E.Value("{:.2f}".format(row.Value)),
                        E.ForeignTax("{:.2f}".format(row.ForeignTax)),
                        E.SourceCountry(row.PayerCountry),
                        E.ReliefStatement(row.ReliefStatement),
                    ) for row in dividends.itertuples()],
                ),
            )
        xf.write(envelope, pretty_print=True)
        print("XML file written to dividends_furs.xml")

def verify_xml():
    # Verify the generated XML using an xsd schema
    schema = etree.XMLSchema(etree.parse("data/Doh_Div_3.xsd"))
    xml = etree.parse("dividends_furs.xml")
    schema.assertValid(xml)
    print("XML is valid according to FURS schema")

# Parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument("dividends", help="Path to the dividends xlsx file")
parser.add_argument("--taxpayer", help="Path to the taxpayer xml info file", required=True)
parser.add_argument("--additional-info", help="Path to the additional info xlsx file with ISINs and addresses of the payers", required=False)
parser.add_argument("--output", help="Path to the output xml file", required=False)
args = parser.parse_args()

# Load taxpayer data
taxpayer = Taxpayer(args.taxpayer)

# Open dividends xlsx file
df = pd.read_excel(args.dividends, sheet_name='Share Dividends')
print("Opened dividends file: ", args.dividends)

# Create a cache object
cache = Cache()
if args.additional_info:
    cache.fill_isin_cache(args.additional_info)

# Rename the columns
furs_df = df.rename(columns={
    "Instrument": "PayerName",
    "Pay Date": "Date",
    "Dividend amount":"Value",
    "Withholding tax amount": "ForeignTax",
    "Instrument Symbol": "Symbol",
})

# Parse the date values in the Date column and convert them to the format YYYY-MM-DD
furs_df["Date"] = pd.to_datetime(furs_df["Date"], format="%d-%b-%Y").dt.strftime("%Y-%m-%d")

# Add a couple more columns that are required by the FURS XML schema and set them as null
furs_df["ReliefStatement"] = None
furs_df["PayerAddress"] = None
furs_df["PayerIdentificationNumber"] = None
furs_df["PayerCountry"] = None

# Get the exchange rate for the dates in the Date column
exchange_rates = currency.get_currency(furs_df["Date"].unique())

finance_data = FinanceData(cache)
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
            cache.set_isin(row["Symbol"], isin)
        row["PayerIdentificationNumber"] = isin
    # Payer country
    if not row["PayerCountry"]:
        row["PayerCountry"] = row["PayerIdentificationNumber"][:2]
    # Payer address
    if not row["PayerAddress"]:
        address = finance_data.get_address(row["Symbol"])
        if not address:
            address = input("Enter the payer address for {}: ".format(row["PayerName"]))
            cache.set_address(row["Symbol"], address)
        row["PayerAddress"] = address
    # Relief statement
    if not row["ReliefStatement"]:
        statement = cache.get_relief_statement(row["PayerCountry"])
        if not statement:
            statement = input("Enter the relief statement for country {}: ".format(row["PayerCountry"]))
            cache.set_relief_statement(row["PayerCountry"], statement)
        row["ReliefStatement"] = statement
    return row

# Process the rows (convert currencies, get missing data from the user, etc.)
furs_df = furs_df.apply(process_row, axis=1)

# Write the final XML file
write_xml(furs_df, args.output or "dividends_furs.xml")
verify_xml()

# Write the caches
cache.write_cache()
