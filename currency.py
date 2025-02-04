from lxml import etree
import requests
import datetime
import warnings

class Currency:
    @staticmethod
    def download_currency():
        url = "https://www.bsi.si/_data/tecajnice/dtecbs-l.xml"
        response = requests.get(url)
        with open("data/currency.xml", "wb") as f:
            f.write(response.content)

    def __init__(self, dates: list[datetime.date], currencies: list[str]):
        # For the dates we need also all dates of the first past month of the earliest date
        earliest_date = min(dates)
        first_of_month = datetime.date(earliest_date.year, earliest_date.month, 1)
        last_of_prev_month = first_of_month - datetime.timedelta(days=1)
        first_of_prev_month = datetime.date(last_of_prev_month.year, last_of_prev_month.month, 1)

        # Add all dates from the previous month
        current = first_of_prev_month
        while current <= last_of_prev_month:
            dates.append(current)
            current += datetime.timedelta(days=1)

        dates.sort()
        self.dates = dates
        self.currencies = currencies
        self.currency_data = self.get_currency()

    def get_currency(self):
        results = {}
        for event, element in etree.iterparse(
            "data/currency.xml", tag="{http://www.bsi.si}tecajnica"
        ):
            date = datetime.datetime.strptime(element.attrib["datum"], "%Y-%m-%d").date()
            currencies = {}
            for child in element if date in self.dates else []:
                currency = child.attrib["oznaka"]
                if currency in self.currencies:
                    currencies[currency] = float(child.text)
            if len(currencies) > 0:
                results[date] = currencies
            element.clear()
        return results

    def get_rate(self, date: datetime.date, currency: str) -> float:
        if date not in self.currency_data:
            earlier_dates = [d for d in self.currency_data if d < date]
            if not earlier_dates:
                earliest_date = min(self.currency_data.keys())
                latest_date = max(self.currency_data.keys())
                warnings.warn(
                    f"No currency data found before {date}, "
                    f"available date range is {earliest_date} to {latest_date}"
                )
                date = earliest_date
            else:
                date = max(earlier_dates)
        return self.currency_data[date][currency]


