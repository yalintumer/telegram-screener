"""Input validation utilities"""

import re
from pathlib import Path


def is_valid_symbol(symbol: str) -> bool:
    """
    Validate stock ticker symbol
    
    Rules:
    - 1-5 characters
    - Only uppercase letters and optional numbers
    - No special characters except dot (for international stocks like BRK.A)
    
    Examples:
        AAPL -> True
        MSFT -> True
        BRK.A -> True
        GOOGL -> True
        ABC123 -> False (mixed)
        A -> True
        ABCDEF -> False (too long)
        APL$ -> False (special char)
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Clean whitespace
    symbol = symbol.strip()
    
    # Length check
    if len(symbol) < 1 or len(symbol) > 6:
        return False
    
    # Pattern: 1-6 uppercase letters, optionally followed by dot and letter
    pattern = r'^[A-Z]{1,5}(\.[A-Z])?$'
    return bool(re.match(pattern, symbol))


def sanitize_symbol(symbol: str) -> str:
    """
    Sanitize and normalize stock ticker symbol
    
    Returns cleaned symbol or raises ValueError if invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError(f"Invalid symbol: {symbol}")
    
    # Clean and uppercase
    symbol = symbol.strip().upper()
    
    # Validate
    if not is_valid_symbol(symbol):
        raise ValueError(f"Invalid ticker format: {symbol}")
    
    return symbol


def sanitize_symbols(symbols: list[str]) -> list[str]:
    """
    Sanitize list of symbols, skip invalid ones
    
    Returns:
        tuple of (valid_symbols, invalid_symbols)
    """
    valid = []
    invalid = []
    
    for s in symbols:
        try:
            cleaned = sanitize_symbol(s)
            valid.append(cleaned)
        except ValueError:
            invalid.append(s)
    
    return valid, invalid


def is_safe_path(path: str, base_dir: str = None) -> bool:
    """
    Check if path is safe (no directory traversal)
    
    Args:
        path: Path to check
        base_dir: Base directory to restrict to (optional)
        
    Returns:
        True if path is safe
    """
    try:
        p = Path(path).resolve()
        
        # Check for directory traversal
        if '..' in str(path):
            return False
        
        # If base_dir provided, ensure path is within it
        if base_dir:
            base = Path(base_dir).resolve()
            return p.is_relative_to(base)
        
        return True
        
    except (ValueError, OSError):
        return False
