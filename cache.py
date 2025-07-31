from lxml import etree
import pandas as pd
from isin_utils import validate_isin


class Cache:
    def __init__(self, path: str) -> None:
        self.path = path
        try:
            file = etree.parse(self.path)
            self.memory = {}
            for element in file.getroot():
                id = element.attrib["id"]
                data = {}
                for el in element:
                    data[el.tag] = el.text
                self.memory[id] = data
        except (FileNotFoundError, OSError):
            self.memory = {}

    def flush(self):
        with etree.xmlfile(self.path, encoding="utf-8") as xf:
            xf.write_declaration()
            root = etree.Element("cache")
            for id, data in self.memory.items():
                el = etree.SubElement(root, "item", id=id)
                for key, value in data.items():
                    el2 = etree.SubElement(el, key)
                    el2.text = value
            xf.write(root, pretty_print=True)


class CompanyCache(Cache):
    def fill_isin_cache(self, additional_info_file):
        info = pd.read_excel(additional_info_file, sheet_name=0)
        for _, row in info.iterrows():
            self.set_isin(row["Instrument Symbol"], row["Instrument ISIN"])

    def get_isin(self, symbol):
        return self.memory.get(symbol, {}).get("isin")

    def set_isin(self, symbol, isin):
        # Validate ISIN before storing
        validated_isin = validate_isin(isin, f"symbol {symbol}")
        if symbol in self.memory:
            self.memory[symbol]["isin"] = validated_isin
        else:
            self.memory[symbol] = {"isin": validated_isin}

    def get_address(self, symbol):
        return self.memory.get(symbol, {}).get("address")

    def set_address(self, symbol, address):
        if symbol in self.memory:
            self.memory[symbol]["address"] = address
        else:
            self.memory[symbol] = {"address": address}


class CountryCache(Cache):
    def get_relief_statement(self, country):
        return self.memory.get(country, {}).get("relief_statement")

    def set_relief_statement(self, country, relief_statement):
        if country in self.memory:
            self.memory[country]["relief_statement"] = relief_statement
        else:
            self.memory[country] = {"relief_statement": relief_statement}

    def get_country_name(self, country):
        return self.memory.get(country, {}).get("name")

    def set_country_name(self, country, name):
        if country in self.memory:
            self.memory[country]["name"] = name
        else:
            self.memory[country] = {"name": name}
