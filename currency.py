from lxml import etree

def get_currency(dates):
    results = {}
    for event, element in etree.iterparse("data/currency.xml", tag="{http://www.bsi.si}tecajnica"):
        date = element.attrib["datum"]
        for child in element if date in dates else []:
            currency = child.attrib["oznaka"]
            if currency == "USD":
                results[date] = float(child.text)
        element.clear()
    return results
