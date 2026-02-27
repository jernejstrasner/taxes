"""Replace closed position open-side data with historical lot data."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd

from lot_parser import HistoricalLot, parse_lots_directory
from split_cache import SplitCache, StockSplit


# Tolerance for matching cost basis (handles rounding differences)
COST_BASIS_TOLERANCE = Decimal("0.15")

# Map current symbols to historical symbols (for ticker changes/reorganizations)
SYMBOL_ALIASES = {
    "SHOP_NEW": "SHOP",  # Shopify reorganization
    "META": "FB",        # Facebook rebrand
    "GOOGL": "GOOG",     # Google class A/C
}


def resolve_symbol(symbol: str) -> str:
    """Resolve a symbol to its historical equivalent if aliased."""
    return SYMBOL_ALIASES.get(symbol, symbol)


@dataclass
class MergedLotMatch:
    """Result of matching against sum of multiple historical lots."""
    lots: list[HistoricalLot]
    total_cost_basis: Decimal
    total_adjusted_quantity: Decimal
    earliest_date: date
    latest_date: date


@dataclass
class AdjustedLot:
    """A historical lot with split-adjusted quantities."""
    original: HistoricalLot
    adjusted_quantity: Decimal
    adjusted_cost_per_share: Decimal
    splits_applied: list[StockSplit]


class LotVerifier:
    """Verifies closed positions against historical lot data."""

    def __init__(self, lots_directory: str):
        self.historical_lots = parse_lots_directory(lots_directory)
        self.split_cache = SplitCache()

    def adjust_for_splits(
        self,
        lot: HistoricalLot,
        current_date: date,
    ) -> AdjustedLot:
        """
        Adjust a historical lot for splits that occurred between lot open and current date.

        Cost basis is invariant under splits, but quantity and cost per share change.
        """
        splits = self.split_cache.get_splits_in_range(
            lot.symbol, lot.open_date, current_date
        )

        adjusted_quantity = lot.quantity
        adjusted_cost_per_share = lot.cost_per_share

        for split in splits:
            adjusted_quantity *= split.ratio
            adjusted_cost_per_share /= split.ratio

        return AdjustedLot(
            original=lot,
            adjusted_quantity=adjusted_quantity,
            adjusted_cost_per_share=adjusted_cost_per_share,
            splits_applied=splits,
        )

    def find_matching_lot(
        self,
        symbol: str,
        cost_basis: Decimal,
        close_date: date,
    ) -> tuple[AdjustedLot | None, list[str]]:
        """
        Find a historical lot matching the given cost basis.

        Returns (matched_lot, messages) where messages contains split info.
        """
        messages = []

        # Resolve symbol alias (e.g., SHOP_NEW -> SHOP)
        lookup_symbol = resolve_symbol(symbol)
        if lookup_symbol != symbol:
            messages.append(f"  {symbol} -> {lookup_symbol} (symbol alias)")

        if lookup_symbol not in self.historical_lots:
            return None, [f"No historical lots found for {symbol}"]

        lots = self.historical_lots[lookup_symbol]

        for lot in lots:
            # Adjust for splits
            adjusted = self.adjust_for_splits(lot, close_date)

            if adjusted.splits_applied:
                for split in adjusted.splits_applied:
                    messages.append(
                        f"  {symbol}: {split.ratio}:1 split applied ({split.date})"
                    )

            # Match by cost basis (invariant under splits)
            if abs(lot.cost_basis - cost_basis) <= COST_BASIS_TOLERANCE:
                return adjusted, messages

        return None, messages

    def find_merged_lot_match(
        self,
        symbol: str,
        cost_basis: Decimal,
        close_date: date,
    ) -> tuple[MergedLotMatch | None, list[str]]:
        """
        Check if statement row matches the sum of all historical lots for a symbol.

        This detects when a broker has consolidated multiple lots into one row.
        """
        messages = []

        lookup_symbol = resolve_symbol(symbol)
        if lookup_symbol not in self.historical_lots:
            return None, messages

        lots = self.historical_lots[lookup_symbol]
        if len(lots) < 2:
            return None, messages

        total_cost_basis = sum(lot.cost_basis for lot in lots)
        total_adjusted_quantity = Decimal("0")

        for lot in lots:
            adjusted = self.adjust_for_splits(lot, close_date)
            total_adjusted_quantity += adjusted.adjusted_quantity

        # Use larger tolerance for merged lots since rounding compounds
        merged_tolerance = COST_BASIS_TOLERANCE * len(lots)
        cost_matches = abs(total_cost_basis - cost_basis) <= merged_tolerance

        if cost_matches:
            dates = [lot.open_date for lot in lots]
            return MergedLotMatch(
                lots=lots,
                total_cost_basis=total_cost_basis,
                total_adjusted_quantity=total_adjusted_quantity,
                earliest_date=min(dates),
                latest_date=max(dates),
            ), messages

        return None, messages

    def get_adjusted_lots(
        self,
        symbol: str,
        close_date: date,
    ) -> list[AdjustedLot]:
        """Get all historical lots for a symbol, adjusted for splits."""
        lookup_symbol = resolve_symbol(symbol)
        if lookup_symbol not in self.historical_lots:
            return []

        lots = self.historical_lots[lookup_symbol]
        return [self.adjust_for_splits(lot, close_date) for lot in lots]

    def get_replacement_lots(
        self,
        symbol: str,
        cost_basis: Decimal,
        close_date: date,
    ) -> tuple[list[AdjustedLot] | None, bool, list[str]]:
        """
        Get split-adjusted historical lots to replace a Saxo row's open-side data.

        Matches by cost basis (single lot first, then merged lots).
        When matched, returns adjusted lots unconditionally.

        Returns (adjusted_lots, is_merged, messages) where:
        - adjusted_lots: replacement lots (None if no match)
        - is_merged: True if this was a merged lot match (multiple lots)
        - messages: informational messages about splits/aliases
        """
        messages = []

        # Try single lot match
        matched_lot, match_messages = self.find_matching_lot(symbol, cost_basis, close_date)
        messages.extend(match_messages)

        if matched_lot is not None:
            return [matched_lot], False, messages

        # Try merged lot match
        merged_match, merge_messages = self.find_merged_lot_match(symbol, cost_basis, close_date)
        messages.extend(merge_messages)

        if merged_match is not None:
            adjusted_lots = self.get_adjusted_lots(symbol, close_date)
            lot_dates = ", ".join(
                str(lot.open_date) for lot in sorted(merged_match.lots, key=lambda x: x.open_date)
            )
            messages.append(
                f"  {symbol}: expanding merged lot into {len(merged_match.lots)} "
                f"individual lots ({lot_dates})"
            )
            return adjusted_lots, True, messages

        return None, False, messages


def replace_lots_from_historical(
    lots_directory: str,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Replace open-side data in closed positions with split-adjusted historical lot data.

    Historical lots are the source of truth for trade opens. When a match is found
    by cost basis, the open date, quantity, and price are replaced unconditionally.

    Args:
        lots_directory: Path to directory containing Lot-Details-*.CSV files
        df: DataFrame with Saxo ClosedPositions data (pre-processed with dates parsed)

    Returns:
        DataFrame with historical lot data replacing open-side fields where matched.
    """
    print("\nReplacing lots from historical data...")

    verifier = LotVerifier(lots_directory)
    replaced_count = 0
    passthrough_count = 0
    symbols_seen = set()

    rows_to_drop = []
    new_rows = []

    for idx, row in df.iterrows():
        symbol = row["Instrument Symbol"].split(":")[0]
        symbols_seen.add(symbol)
        symbols_seen.add(resolve_symbol(symbol))

        cost_basis = Decimal(str(row["Quantity Open"])) * Decimal(str(row["Open Price"]))
        close_date = row["Trade Date Close"].date()

        adjusted_lots, is_merged, messages = verifier.get_replacement_lots(
            symbol, cost_basis, close_date,
        )

        for msg in messages:
            print(msg)

        if adjusted_lots is not None:
            rows_to_drop.append(idx)
            replaced_count += 1

            for i, adj_lot in enumerate(adjusted_lots):
                new_row = row.copy()
                new_row["Trade Date Open"] = pd.Timestamp(adj_lot.original.open_date)
                new_row["Quantity Open"] = float(adj_lot.adjusted_quantity)
                new_row["Open Price"] = float(adj_lot.adjusted_cost_per_share)
                new_row["QuantityClose"] = float(adj_lot.adjusted_quantity)
                # Unique IDs when expanding merged lots into multiple rows
                if len(adjusted_lots) > 1:
                    new_row["OpenPositionId"] = f"{row['OpenPositionId']}_lot{i}"
                    new_row["ClosePositionId"] = f"{row['ClosePositionId']}_lot{i}"
                new_rows.append(new_row)
        else:
            passthrough_count += 1

    corrected_df = df.drop(rows_to_drop)
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        corrected_df = pd.concat([corrected_df, new_df], ignore_index=True)

    # Report symbols in historical data but not in statement
    historical_symbols = set(verifier.historical_lots.keys())
    missing_symbols = historical_symbols - symbols_seen
    if missing_symbols:
        print(f"\n  Note: Historical lots exist for symbols not in statement: {', '.join(sorted(missing_symbols))}")

    verifier.split_cache.flush()

    print(f"\nLot replacement complete: {replaced_count} replaced, {passthrough_count} unmatched")

    return corrected_df
