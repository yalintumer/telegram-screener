"""Tests for CLI module."""

import pytest
from unittest.mock import Mock, patch

from src.cli import create_parser, run_cli


class TestCreateParser:
    """Tests for argument parser creation."""
    
    def test_parser_has_config_argument(self):
        """Parser should have --config argument."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.config == "config.yaml"
    
    def test_parser_config_custom_value(self):
        """Parser should accept custom config path."""
        parser = create_parser()
        args = parser.parse_args(["--config", "custom.yaml"])
        assert args.config == "custom.yaml"
    
    def test_parser_has_interval_argument(self):
        """Parser should have --interval argument with default 3600."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.interval == 3600
    
    def test_parser_interval_custom_value(self):
        """Parser should accept custom interval."""
        parser = create_parser()
        args = parser.parse_args(["--interval", "1800"])
        assert args.interval == 1800
    
    def test_parser_has_once_flag(self):
        """Parser should have --once flag."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.once is False
        
        args_with_flag = parser.parse_args(["--once"])
        assert args_with_flag.once is True
    
    def test_parser_has_market_scan_flag(self):
        """Parser should have --market-scan flag."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.market_scan is False
        
        args_with_flag = parser.parse_args(["--market-scan"])
        assert args_with_flag.market_scan is True
    
    def test_parser_has_wavetrend_flag(self):
        """Parser should have --wavetrend flag."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.wavetrend is False
        
        args_with_flag = parser.parse_args(["--wavetrend"])
        assert args_with_flag.wavetrend is True
    
    def test_parser_description(self):
        """Parser should have proper description."""
        parser = create_parser()
        assert "Telegram Stock Screener" in parser.description
        assert "2-stage" in parser.description


class TestRunCli:
    """Tests for CLI dispatch logic."""
    
    @pytest.fixture
    def mock_functions(self):
        """Create mock functions for testing."""
        return {
            "market_scan_fn": Mock(),
            "wavetrend_scan_fn": Mock(),
            "continuous_fn": Mock(),
        }
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        return Mock()
    
    def test_market_scan_flag_calls_market_scan(self, mock_functions, mock_config):
        """--market-scan should call market_scan_fn."""
        with patch("src.cli.Config.load", return_value=mock_config):
            exit_code = run_cli(["--market-scan"], **mock_functions)
        
        assert exit_code == 0
        mock_functions["market_scan_fn"].assert_called_once_with(mock_config)
        mock_functions["wavetrend_scan_fn"].assert_not_called()
        mock_functions["continuous_fn"].assert_not_called()
    
    def test_wavetrend_flag_calls_wavetrend_scan(self, mock_functions, mock_config):
        """--wavetrend should call wavetrend_scan_fn."""
        with patch("src.cli.Config.load", return_value=mock_config):
            exit_code = run_cli(["--wavetrend"], **mock_functions)
        
        assert exit_code == 0
        mock_functions["wavetrend_scan_fn"].assert_called_once_with(mock_config)
        mock_functions["market_scan_fn"].assert_not_called()
        mock_functions["continuous_fn"].assert_not_called()
    
    def test_once_flag_calls_both_stages(self, mock_functions, mock_config):
        """--once should call both market_scan_fn and wavetrend_scan_fn."""
        with patch("src.cli.Config.load", return_value=mock_config):
            exit_code = run_cli(["--once"], **mock_functions)
        
        assert exit_code == 0
        mock_functions["market_scan_fn"].assert_called_once_with(mock_config)
        mock_functions["wavetrend_scan_fn"].assert_called_once_with(mock_config)
        mock_functions["continuous_fn"].assert_not_called()
    
    def test_default_calls_continuous(self, mock_functions, mock_config):
        """No flags should call continuous_fn."""
        with patch("src.cli.Config.load", return_value=mock_config):
            exit_code = run_cli([], **mock_functions)
        
        assert exit_code == 0
        mock_functions["continuous_fn"].assert_called_once_with(mock_config, 3600)
        mock_functions["market_scan_fn"].assert_not_called()
        mock_functions["wavetrend_scan_fn"].assert_not_called()
    
    def test_custom_interval_passed_to_continuous(self, mock_functions, mock_config):
        """Custom interval should be passed to continuous_fn."""
        with patch("src.cli.Config.load", return_value=mock_config):
            exit_code = run_cli(["--interval", "1800"], **mock_functions)
        
        assert exit_code == 0
        mock_functions["continuous_fn"].assert_called_once_with(mock_config, 1800)
    
    def test_keyboard_interrupt_returns_130(self, mock_functions, mock_config):
        """KeyboardInterrupt should return exit code 130."""
        mock_functions["market_scan_fn"].side_effect = KeyboardInterrupt()
        
        with patch("src.cli.Config.load", return_value=mock_config):
            exit_code = run_cli(["--market-scan"], **mock_functions)
        
        assert exit_code == 130
    
    def test_exception_returns_1(self, mock_functions, mock_config):
        """Generic exception should return exit code 1."""
        mock_functions["market_scan_fn"].side_effect = RuntimeError("Test error")
        
        with patch("src.cli.Config.load", return_value=mock_config):
            exit_code = run_cli(["--market-scan"], **mock_functions)
        
        assert exit_code == 1
    
    def test_config_load_error_returns_1(self, mock_functions):
        """Config load error should return exit code 1."""
        with patch("src.cli.Config.load", side_effect=FileNotFoundError("config.yaml not found")):
            exit_code = run_cli(["--once"], **mock_functions)
        
        assert exit_code == 1
    
    def test_custom_config_path(self, mock_functions, mock_config):
        """Custom config path should be used."""
        with patch("src.cli.Config.load", return_value=mock_config) as mock_load:
            run_cli(["--config", "custom.yaml", "--once"], **mock_functions)
        
        mock_load.assert_called_once_with("custom.yaml")
