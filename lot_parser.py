"""Parse historical lot CSV files exported from brokers."""

import csv
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


@dataclass
class HistoricalLot:
    """A single historical lot from a broker export."""
    symbol: str
    open_date: date
    quantity: Decimal
    cost_per_share: Decimal
    cost_basis: Decimal


def parse_currency_value(value: str) -> Decimal:
    """Parse a currency string like '$1,234.56' to Decimal."""
    cleaned = value.replace("$", "").replace(",", "").strip()
    if not cleaned or cleaned == "--":
        raise ValueError(f"Invalid currency value: {value}")
    return Decimal(cleaned)


def parse_lot_csv(file_path: str) -> list[HistoricalLot]:
    """
    Parse a lot details CSV file.

    Expected format (Robinhood/Schwab):
    - First line: header like "SHOP Lot Details for XXXX-5792 as of..."
    - Second line: column headers
    - Data lines: Open Date, Quantity, Price, Cost/Share, ...Cost Basis...
    - Last line: "Total" row to skip
    """
    lots = []

    # Extract symbol from filename (e.g., "Lot-Details-SHOP.CSV" -> "SHOP")
    filename = os.path.basename(file_path)
    match = re.match(r"Lot-Details-(\w+)\.CSV", filename, re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot extract symbol from filename: {filename}")
    symbol = match.group(1)

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)

        # Skip header line
        next(reader)

        # Skip blank line (if present)
        headers = next(reader)
        while not headers or not any(headers):
            headers = next(reader)
        # Remove trailing empty columns and normalize headers
        headers = [h.strip() for h in headers if h.strip()]

        # Find required columns
        try:
            date_idx = headers.index("Open Date")
            qty_idx = headers.index("Quantity")
            cost_share_idx = headers.index("Cost/Share")
            cost_basis_idx = headers.index("Cost Basis")
        except ValueError as e:
            raise ValueError(f"Missing required column in {file_path}: {e}")

        for row in reader:
            if not row or not row[0].strip():
                continue

            # Skip total row
            if row[0].strip().lower() == "total":
                continue

            try:
                # Parse date (format: "10/30/2017 00:00:00" or "10/30/2017")
                date_str = row[date_idx].strip()
                if " " in date_str:
                    date_str = date_str.split(" ")[0]
                open_date = datetime.strptime(date_str, "%m/%d/%Y").date()

                quantity = Decimal(row[qty_idx].strip())
                cost_per_share = parse_currency_value(row[cost_share_idx])
                cost_basis = parse_currency_value(row[cost_basis_idx])

                lots.append(HistoricalLot(
                    symbol=symbol,
                    open_date=open_date,
                    quantity=quantity,
                    cost_per_share=cost_per_share,
                    cost_basis=cost_basis,
                ))
            except (ValueError, InvalidOperation) as e:
                raise ValueError(f"Error parsing row in {file_path}: {row} - {e}")

    return lots


def parse_lots_directory(directory: str) -> dict[str, list[HistoricalLot]]:
    """
    Parse all lot CSV files in a directory.

    Returns a dict mapping symbol -> list of HistoricalLot.
    """
    lots_by_symbol: dict[str, list[HistoricalLot]] = {}

    path = Path(directory)
    if not path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    for csv_file in path.glob("Lot-Details-*.CSV"):
        lots = parse_lot_csv(str(csv_file))
        for lot in lots:
            if lot.symbol not in lots_by_symbol:
                lots_by_symbol[lot.symbol] = []
            lots_by_symbol[lot.symbol].append(lot)

    return lots_by_symbol
