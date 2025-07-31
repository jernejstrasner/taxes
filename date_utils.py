import datetime
import pandas as pd
import sys
from typing import Union, List


def parse_date(date_value: Union[str, datetime.date, pd.Timestamp], 
               formats: List[str] = None,
               context: str = "") -> datetime.date:
    """
    Parse a date from various formats with validation.
    
    Args:
        date_value: The date to parse (string, date, or pandas Timestamp)
        formats: List of date formats to try (defaults to common formats)
        context: Context string for error messages (e.g., "dividend payment")
    
    Returns:
        Parsed date as datetime.date
        
    Raises:
        SystemExit: If date cannot be parsed or is invalid
    """
    # If already a date, just validate it
    if isinstance(date_value, datetime.date):
        validate_date(date_value, context)
        return date_value
    
    # If pandas Timestamp, convert to date
    if isinstance(date_value, pd.Timestamp):
        date_obj = date_value.date()
        validate_date(date_obj, context)
        return date_obj
    
    # Default formats if none provided
    if formats is None:
        formats = [
            "%Y-%m-%d",      # ISO format
            "%d-%b-%Y",      # Saxo Bank format (01-Jan-2024)
            "%d.%m.%Y",      # Slovenian format
            "%Y/%m/%d",      # Alternative format
            "%d/%m/%Y",      # European format
            "%m/%d/%Y",      # US format
        ]
    
    # Try each format
    date_obj = None
    for fmt in formats:
        try:
            date_obj = datetime.datetime.strptime(str(date_value).strip(), fmt).date()
            break
        except ValueError:
            continue
    
    if date_obj is None:
        context_msg = f" for {context}" if context else ""
        print(f"Error: Unable to parse date '{date_value}'{context_msg}")
        print(f"Tried formats: {', '.join(formats)}")
        sys.exit(1)
    
    validate_date(date_obj, context)
    return date_obj


def validate_date(date_obj: datetime.date, context: str = ""):
    """
    Validate that a date is reasonable for financial data.
    
    Args:
        date_obj: The date to validate
        context: Context string for error messages
    """
    today = datetime.date.today()
    context_msg = f" for {context}" if context else ""
    
    # Check if date is in the future
    if date_obj > today:
        print(f"Error: Date {date_obj}{context_msg} is in the future")
        sys.exit(1)
    
    # Check if date is too old (before 1990 seems unreasonable for modern trading)
    min_date = datetime.date(1990, 1, 1)
    if date_obj < min_date:
        print(f"Error: Date {date_obj}{context_msg} is before {min_date} - seems too old for financial data")
        sys.exit(1)


def parse_pandas_date_column(df: pd.DataFrame, 
                            column: str, 
                            formats: List[str] = None,
                            context: str = "") -> pd.DataFrame:
    """
    Parse and validate a date column in a pandas DataFrame.
    
    Args:
        df: The DataFrame containing the date column
        column: Name of the column to parse
        formats: List of date formats to try
        context: Context string for error messages
        
    Returns:
        DataFrame with parsed date column
    """
    if column not in df.columns:
        print(f"Error: Column '{column}' not found in DataFrame")
        sys.exit(1)
    
    # Try pandas to_datetime first
    try:
        if formats and len(formats) == 1:
            df[column] = pd.to_datetime(df[column], format=formats[0])
        else:
            df[column] = pd.to_datetime(df[column], infer_datetime_format=True)
        
        # Validate all dates
        for idx, date in df[column].items():
            if pd.notna(date):
                validate_date(date.date(), f"{context} at row {idx}")
        
        return df
    except Exception as e:
        # Fall back to row-by-row parsing
        parsed_dates = []
        for idx, value in df[column].items():
            if pd.isna(value):
                parsed_dates.append(pd.NaT)
            else:
                context_with_row = f"{context} at row {idx}" if context else f"row {idx}"
                date_obj = parse_date(value, formats, context_with_row)
                parsed_dates.append(pd.Timestamp(date_obj))
        
        df[column] = parsed_dates
        return df