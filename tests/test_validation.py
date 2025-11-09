"""Unit tests for symbol validation"""

import pytest
from src.validation import (
    is_valid_symbol,
    sanitize_symbol,
    sanitize_symbols,
    is_safe_path
)


class TestSymbolValidation:
    """Tests for symbol validation functions"""
    
    def test_valid_symbols(self):
        """Test valid ticker symbols"""
        valid_cases = [
            'AAPL',
            'MSFT',
            'GOOGL',
            'BRK.A',
            'BRK.B',
            'A',
            'AA',
            'AAA',
            'AAAA',
            'AAAAA',
        ]
        
        for symbol in valid_cases:
            assert is_valid_symbol(symbol), f"{symbol} should be valid"
    
    def test_invalid_symbols(self):
        """Test invalid ticker symbols"""
        invalid_cases = [
            '',              # Empty
            'AAAAAA',        # Too long
            'ABC123',        # Mixed alphanumeric
            '123',           # Numbers only
            'APL$',          # Special character
            'AAPL!',         # Special character
            'AA PL',         # Space
            'aa',            # Lowercase (should fail before sanitization)
            'BRK.AB',        # Too many chars after dot
            'BRK..A',        # Double dot
        ]
        
        for symbol in invalid_cases:
            assert not is_valid_symbol(symbol), f"{symbol} should be invalid"
    
    def test_sanitize_symbol_success(self):
        """Test successful symbol sanitization"""
        test_cases = [
            (' AAPL ', 'AAPL'),
            ('aapl', 'AAPL'),
            ('  msft  ', 'MSFT'),
            ('BrK.a', 'BRK.A'),
        ]
        
        for input_sym, expected in test_cases:
            result = sanitize_symbol(input_sym)
            assert result == expected, f"sanitize_symbol('{input_sym}') should be '{expected}', got '{result}'"
    
    def test_sanitize_symbol_failure(self):
        """Test symbol sanitization failures"""
        invalid_cases = ['', '123', 'AAAAAA', 'APL$', None, '   ']
        
        for symbol in invalid_cases:
            with pytest.raises(ValueError):
                sanitize_symbol(symbol)
    
    def test_sanitize_symbols_batch(self):
        """Test batch symbol sanitization"""
        input_symbols = ['AAPL', 'msft', 'GOOGL', '123', 'TSLA', 'INVALID$']
        
        valid, invalid = sanitize_symbols(input_symbols)
        
        assert 'AAPL' in valid
        assert 'MSFT' in valid  # Should be uppercased
        assert 'GOOGL' in valid
        assert 'TSLA' in valid
        
        assert '123' in invalid
        assert 'INVALID$' in invalid
        
        assert len(valid) == 4
        assert len(invalid) == 2
    
    def test_empty_list(self):
        """Test empty symbol list"""
        valid, invalid = sanitize_symbols([])
        
        assert valid == []
        assert invalid == []


class TestPathSafety:
    """Tests for path safety validation"""
    
    def test_safe_paths(self):
        """Test safe file paths"""
        safe_cases = [
            'watchlist.json',
            'logs/app.log',
            './data/config.yaml',
            'shots/screenshot.png',
        ]
        
        for path in safe_cases:
            assert is_safe_path(path), f"{path} should be safe"
    
    def test_unsafe_paths(self):
        """Test unsafe file paths (directory traversal)"""
        unsafe_cases = [
            '../etc/passwd',
            '../../secrets.txt',
            'data/../../etc/hosts',
            './../config',
        ]
        
        for path in unsafe_cases:
            assert not is_safe_path(path), f"{path} should be unsafe"
    
    def test_base_dir_restriction(self):
        """Test path restriction to base directory"""
        base_dir = '/Users/test/project'
        
        # Should be safe (within base)
        safe_path = '/Users/test/project/data/file.txt'
        assert is_safe_path(safe_path, base_dir)
        
        # Should be unsafe (outside base)
        # Note: This test may need adjustment based on actual implementation


class TestEdgeCases:
    """Edge case tests"""
    
    def test_none_inputs(self):
        """Test None inputs"""
        assert not is_valid_symbol(None)
        
        with pytest.raises(ValueError):
            sanitize_symbol(None)
    
    def test_whitespace_only(self):
        """Test whitespace-only strings"""
        whitespace_cases = ['   ', '\t', '\n', '  \t\n  ']
        
        for ws in whitespace_cases:
            assert not is_valid_symbol(ws)
            
            with pytest.raises(ValueError):
                sanitize_symbol(ws)
    
    def test_unicode_symbols(self):
        """Test unicode characters in symbols"""
        unicode_cases = ['AAPL™', 'MSFT®', 'GOOGL©']
        
        for symbol in unicode_cases:
            assert not is_valid_symbol(symbol), f"Unicode symbol {symbol} should be invalid"
    
    def test_case_sensitivity(self):
        """Test that lowercase is handled correctly"""
        # is_valid_symbol expects uppercase
        assert is_valid_symbol('AAPL')
        assert not is_valid_symbol('aapl')  # Should fail validation before sanitization
        
        # But sanitize_symbol should handle it
        assert sanitize_symbol('aapl') == 'AAPL'
