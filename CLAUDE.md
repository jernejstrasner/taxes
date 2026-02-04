# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FURS Taxes is a Python tool that generates XML tax reports for the Slovenian Financial Administration (FURS). It processes financial data from brokers (Saxo Bank, Revolut, IBKR) and outputs validated XML for:
- **Doh_Div**: Dividend income reports
- **Doh_KDVP**: Capital gains/losses from securities
- **Doh_Obr**: Interest income reports

## Commands

```bash
# Install dependencies
uv sync

# Run linter
uv run ruff check .

# Run tests
uv run pytest tests/

# Generate dividend report
uv run python taxes.py --dividends --saxo path/to/export.xlsx

# Generate capital gains report (Saxo or IBKR)
uv run python taxes.py --gains --saxo path/to/export.xlsx
uv run python taxes.py --gains --ibkr path/to/flexquery.xml

# Generate interest report (Saxo or Revolut)
uv run python taxes.py --interest --saxo path/to/export.xlsx
uv run python taxes.py --interest --revolut path/to/export.csv

# Common flags
--period YEAR           # Tax year (defaults to current year)
--output PATH           # Custom output path
--taxpayer PATH         # Cached taxpayer XML
--additional-info PATH  # Excel with ISIN mappings
--correction            # Generate correction report (P workflow)
--no-timestamp          # Disable timestamp in output filename
```

## Architecture

### Data Flow
```
Broker Export → Parse (saxobank.py/revolut.py/ibkr.py) → Domain Models →
  Fetch External Data (finance.py, currency.py) → Generate XML (xml_output.py) →
  Validate Against XSD → Write Output
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `taxes.py` | CLI entry point, orchestrates report generation |
| `saxobank.py` | Parses Saxo Bank Excel exports |
| `revolut.py` | Parses Revolut CSV exports |
| `ibkr.py` | Parses IBKR Flex Query XML exports (capital gains only) |
| `xml_output.py` | Generates FURS-compliant XML with namespace handling |
| `finance.py` | Fetches company info/ISINs from Yahoo Finance |
| `currency.py` | Downloads EUR exchange rates from Bank of Slovenia |
| `gains.py`, `interest.py` | Domain models for financial data |

### External Data Sources
- **Exchange rates**: Bank of Slovenia (`bsi.si`) - cached in `data/currency.xml`
- **Company info**: Yahoo Finance - cached in `cache/company_cache.xml`

### Validation
- Output XML is validated against FURS XSD schemas in `data/` directory
- ISIN validation includes Luhn checksum verification
- Date parsing validates against unreasonable dates (future, pre-1990)

### Caching
Caches are stored as XML files:
- `cache/taxpayer.xml`: Personal tax information
- `cache/company_cache.xml`: Company names and ISINs
- `cache/country_cache.xml`: Country-specific relief statements
- `data/currency.xml`: Exchange rates (refreshed from BSI)

### Network Reliability
HTTP requests use exponential backoff retry (3 retries, 30s timeout) via `network_utils.py`.
