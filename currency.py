from lxml import etree
import requests


def get_currency(dates):
    results = {}
    for event, element in etree.iterparse(
        "data/currency.xml", tag="{http://www.bsi.si}tecajnica"
    ):
        date = element.attrib["datum"]
        currencies = {}
        for child in element if date in dates else []:
            currency = child.attrib["oznaka"]
            if currency == "USD" or currency == "CAD":
                currencies[currency] = float(child.text)
        if len(currencies) > 0:
            results[date] = currencies
        element.clear()
    return results

def download_currency():
    url = "https://www.bsi.si/_data/tecajnice/dtecbs-l.xml"
    response = requests.get(url)
    with open("data/currency.xml", "wb") as f:
        f.write(response.content)
