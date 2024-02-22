from lxml import etree
import pandas as pd


class Cache:
    def __init__(self) -> None:
        self.company = {}
        self.country = {}
        self.read_cache()

    def read_cache(self):
        # Read the company cache from an XML file
        try:
            companies = etree.parse("company_cache.xml")
            for element in companies.getroot():
                symbol = element.attrib["symbol"]
                data = {}
                for el in element:
                    data[el.tag] = el.text
                self.company[symbol] = data
        except (FileNotFoundError, OSError):
            self.company = {}
        # Read the country cache from an XML file
        try:
            country = etree.parse("country_cache.xml")
            for element in country.getroot():
                country = element.attrib["code"]
                data = {}
                for el in element:
                    data[el.tag] = el.text
                self.country[country] = data
        except (FileNotFoundError, OSError):
            self.country = {}

    def write_cache(self):
        # Write the company cache to an XML file
        with etree.xmlfile("company_cache.xml", encoding="utf-8") as xf:
            xf.write_declaration()
            root = etree.Element("company_cache")
            for symbol, data in self.company.items():
                company_el = etree.SubElement(root, "company", symbol=symbol)
                for key, value in data.items():
                    el = etree.SubElement(company_el, key)
                    el.text = value
            xf.write(root, pretty_print=True)
        # Write the country cache to an XML file
        with etree.xmlfile("country_cache.xml", encoding="utf-8") as xf:
            xf.write_declaration()
            root = etree.Element("country_cache")
            for country, data in self.country.items():
                country_el = etree.SubElement(root, "country", code=country)
                for key, value in data.items():
                    el = etree.SubElement(country_el, key)
                    el.text = value
            xf.write(root, pretty_print=True)

    def fill_isin_cache(self, additional_info_file):
        info = pd.read_excel(additional_info_file, sheet_name=0)
        for _, row in info.iterrows():
            self.set_isin(row["Instrument Symbol"], row["Instrument ISIN"])

    def get_isin(self, symbol):
        return self.company.get(symbol, {}).get("isin")

    def set_isin(self, symbol, isin):
        if symbol in self.company:
            self.company[symbol]["isin"] = isin
        else:
            self.company[symbol] = {"isin": isin}

    def get_address(self, symbol):
        return self.company.get(symbol, {}).get("address")

    def set_address(self, symbol, address):
        if symbol in self.company:
            self.company[symbol]["address"] = address
        else:
            self.company[symbol] = {"address": address}

    def get_relief_statement(self, country):
        return self.country.get(country, {}).get("relief_statement")

    def set_relief_statement(self, country, relief_statement):
        if country in self.country:
            self.country[country]["relief_statement"] = relief_statement
        else:
            self.country[country] = {"relief_statement": relief_statement}

    def get_country_name(self, country):
        return self.country.get(country, {}).get("name")

    def set_country_name(self, country, name):
        if country in self.country:
            self.country[country]["name"] = name
        else:
            self.country[country] = {"name": name}
