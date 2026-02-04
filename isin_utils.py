import re
import sys


def validate_isin(isin: str, context: str = "") -> str:
    """
    Validate ISIN (International Securities Identification Number) format.
    
    ISIN format: 12 characters
    - 2 letters: Country code (ISO 3166-1 alpha-2)
    - 9 characters: National security identifier (alphanumeric)
    - 1 digit: Check digit (calculated using Luhn algorithm)
    
    Args:
        isin: The ISIN to validate
        context: Context string for error messages
        
    Returns:
        The validated ISIN (uppercase)
        
    Raises:
        SystemExit: If ISIN is invalid
    """
    context_msg = f" for {context}" if context else ""
    
    if not isin:
        print(f"Error: Empty ISIN provided{context_msg}")
        sys.exit(1)
    
    # Convert to uppercase for validation
    isin = isin.upper().strip()
    
    # Check length
    if len(isin) != 12:
        print(f"Error: ISIN '{isin}'{context_msg} must be exactly 12 characters (got {len(isin)})")
        sys.exit(1)
    
    # Check format: 2 letters + 9 alphanumeric + 1 digit
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$', isin):
        print(f"Error: ISIN '{isin}'{context_msg} has invalid format")
        print("Expected: 2 letters (country) + 9 alphanumeric + 1 check digit")
        sys.exit(1)
    
    # Validate check digit using Luhn algorithm
    if not validate_isin_checksum(isin):
        print(f"Error: ISIN '{isin}'{context_msg} has invalid check digit")
        print("The last digit doesn't match the calculated checksum - possible typo")
        sys.exit(1)
    
    return isin


def validate_isin_checksum(isin: str) -> bool:
    """
    Validate ISIN checksum using the Luhn algorithm.
    
    Args:
        isin: The ISIN to validate (must be 12 characters)
        
    Returns:
        True if checksum is valid, False otherwise
    """
    # Convert letters to numbers (A=10, B=11, ..., Z=35)
    digits = []
    for char in isin[:-1]:  # Exclude check digit
        if char.isdigit():
            digits.append(int(char))
        else:
            # A=10, B=11, ..., Z=35
            digits.append(ord(char) - ord('A') + 10)
    
    # Flatten multi-digit numbers into individual digits
    flattened = []
    for d in digits:
        if d >= 10:
            flattened.extend([d // 10, d % 10])
        else:
            flattened.append(d)
    
    # Apply Luhn algorithm (ISIN variant per ISO 6166)
    # For odd-length strings: double even indices (0, 2, 4, ...)
    # For even-length strings: double odd indices (1, 3, 5, ...)
    if len(flattened) % 2 == 1:
        # Odd length: double indices 0, 2, 4, ...
        indices_to_double = range(0, len(flattened), 2)
    else:
        # Even length: double indices 1, 3, 5, ...
        indices_to_double = range(1, len(flattened), 2)

    for i in indices_to_double:
        flattened[i] *= 2
        if flattened[i] > 9:
            flattened[i] -= 9
    
    # Sum all digits
    total = sum(flattened)
    
    # Calculate check digit
    check_digit = (10 - (total % 10)) % 10
    
    return check_digit == int(isin[-1])


def prompt_for_isin(company_name: str, default_isin: str = None) -> str:
    """
    Prompt user to enter a valid ISIN.
    
    Args:
        company_name: The company name to show in the prompt
        default_isin: Optional default ISIN to suggest
        
    Returns:
        A valid ISIN entered by the user
    """
    while True:
        prompt = f"Enter the ISIN for {company_name}"
        if default_isin:
            prompt += f" (or press Enter for {default_isin})"
        prompt += ": "
        
        user_input = input(prompt).strip()
        
        # Use default if provided and user pressed Enter
        if not user_input and default_isin:
            user_input = default_isin
        
        try:
            return validate_isin(user_input, company_name)
        except SystemExit:
            print("Please try again or press Ctrl+C to exit")
            continue