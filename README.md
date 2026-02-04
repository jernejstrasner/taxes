# FURS Taxes

This is a Python script that generates XML tax reports for dividends, interest and gains according to the regulations of the Financial Administration of the Republic of Slovenia (FURS).

Supported data sources:
- Saxo Bank (`.xlsx` exports)
- Revolut (`.csv` exports, interest only)

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

1. Clone the repository or download the .zip archive of the code
2. Install the dependencies using `uv sync`

## Usage

```shell
# Generate dividend report from Saxo Bank export
uv run python taxes.py --dividends --saxo path/to/export.xlsx

# Generate capital gains report
uv run python taxes.py --gains --saxo path/to/export.xlsx

# Generate interest report (Saxo or Revolut)
uv run python taxes.py --interest --saxo path/to/export.xlsx
uv run python taxes.py --interest --revolut path/to/export.csv

# Common options
--period YEAR          # Tax year (defaults to previous year)
--output PATH          # Custom output path
--taxpayer PATH        # Path to cached taxpayer XML
--correction           # Generate correction report
--no-timestamp         # Don't add timestamp to output filename
--condensed            # Condense interest to one entry per payer
```

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
