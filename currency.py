from lxml import etree
import requests
import datetime
import warnings
import sys
from date_utils import parse_date
from network_utils import download_or_exit, validate_download

class Currency:
    @staticmethod
    def download_currency():
        url = "https://www.bsi.si/_data/tecajnice/dtecbs-l.xml"
        download_or_exit(
            url=url,
            output_file="data/currency.xml",
            timeout=30,
            max_retries=3,
            context="Bank of Slovenia exchange rates"
        )
        validate_download("data/currency.xml", min_size=1000, context="currency data")
        print("Currency exchange rates downloaded successfully")

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
        try:
            for event, element in etree.iterparse(
                "data/currency.xml", tag="{http://www.bsi.si}tecajnica"
            ):
            try:
                date = parse_date(element.attrib["datum"], ["%Y-%m-%d"], "currency exchange rate")
            except SystemExit:
                element.clear()
                continue
            currencies = {}
            for child in element if date in self.dates else []:
                currency = child.attrib["oznaka"]
                if currency in self.currencies:
                    try:
                        rate = float(child.text)
                        # Validate exchange rate is reasonable
                        if rate <= 0:
                            raise ValueError(f"Exchange rate for {currency} on {date} is not positive: {rate}")
                        if rate > 10000:
                            raise ValueError(f"Exchange rate for {currency} on {date} seems unreasonably high: {rate}")
                        currencies[currency] = rate
                    except ValueError as e:
                        print(f"Error parsing exchange rate for {currency} on {date}: {e}")
                        sys.exit(1)
            if len(currencies) > 0:
                results[date] = currencies
                element.clear()
        except Exception as e:
            print(f"Error parsing currency XML file: {e}")
            print("Please ensure data/currency.xml exists and is valid")
            sys.exit(1)
        
        # Validate we have data for required currencies
        if not results:
            print("Error: No currency data found in the XML file")
            sys.exit(1)
            
        missing_currencies = set()
        for date_data in results.values():
            for currency in self.currencies:
                if currency not in date_data:
                    missing_currencies.add(currency)
        
        if missing_currencies:
            print(f"Warning: Some currencies are missing from certain dates: {', '.join(missing_currencies)}")
            
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
        if currency not in self.currency_data[date]:
            available_currencies = list(self.currency_data[date].keys())
            print(f"Error: Currency {currency} not found for date {date}")
            print(f"Available currencies for this date: {', '.join(available_currencies)}")
            sys.exit(1)
        return self.currency_data[date][currency]


