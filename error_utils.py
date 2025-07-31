import sys
from typing import Optional, List


def fatal_error(message: str, 
                context: str = "",
                suggestions: Optional[List[str]] = None,
                exit_code: int = 1):
    """
    Print a formatted error message and exit the application.
    
    Args:
        message: The main error message
        context: Optional context about what was being done when the error occurred
        suggestions: Optional list of suggestions for fixing the error
        exit_code: Exit code to use (default: 1)
    """
    print(f"FATAL ERROR: {message}")
    
    if context:
        print(f"Context: {context}")
    
    if suggestions:
        print("\nSuggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    
    print()  # Empty line before exit
    sys.exit(exit_code)


def validation_error(item: str,
                    value: str,
                    expected: str,
                    context: str = "",
                    suggestions: Optional[List[str]] = None):
    """
    Print a validation error and exit.
    
    Args:
        item: What was being validated (e.g., "ISIN", "date", "currency")
        value: The invalid value
        expected: What was expected
        context: Context about where this occurred
        suggestions: Suggestions for fixing the issue
    """
    message = f"Invalid {item}: '{value}'"
    full_context = f"Expected {expected}"
    if context:
        full_context += f" (occurred {context})"
    
    fatal_error(message, full_context, suggestions)


def file_error(operation: str,
               file_path: str,
               reason: str,
               suggestions: Optional[List[str]] = None):
    """
    Print a file operation error and exit.
    
    Args:
        operation: What was being done (e.g., "reading", "writing", "parsing")
        file_path: Path to the file
        reason: Why the operation failed
        suggestions: Suggestions for fixing the issue
    """
    message = f"Failed {operation} file: {file_path}"
    context = f"Reason: {reason}"
    
    if not suggestions:
        suggestions = [
            "Check that the file exists and is readable",
            "Verify the file is not corrupted or in use by another program",
            "Ensure you have the necessary permissions"
        ]
    
    fatal_error(message, context, suggestions)


def network_error(operation: str,
                 url: str,
                 reason: str,
                 suggestions: Optional[List[str]] = None):
    """
    Print a network operation error and exit.
    
    Args:
        operation: What was being done (e.g., "downloading", "connecting to")
        url: The URL that failed
        reason: Why the operation failed
        suggestions: Suggestions for fixing the issue
    """
    message = f"Failed {operation}: {url}"
    context = f"Reason: {reason}"
    
    if not suggestions:
        suggestions = [
            "Check your internet connection",
            "Verify the URL is correct and the server is accessible",
            "Try again later if the server is temporarily unavailable",
            "Check if you're behind a firewall or proxy"
        ]
    
    fatal_error(message, context, suggestions)


def data_error(data_type: str,
              issue: str,
              location: str = "",
              suggestions: Optional[List[str]] = None):
    """
    Print a data validation error and exit.
    
    Args:
        data_type: Type of data that had an issue (e.g., "dividend data", "exchange rate")
        issue: What the issue was
        location: Where the issue occurred (e.g., "row 5", "MSFT dividend")
        suggestions: Suggestions for fixing the issue
    """
    message = f"Data validation error in {data_type}: {issue}"
    context = f"Location: {location}" if location else ""
    
    fatal_error(message, context, suggestions)