class TVScreenerError(Exception):
    """Base exception for screener errors"""
    pass


class OCRError(TVScreenerError):
    pass


class DataSourceError(TVScreenerError):
    pass


class TelegramError(TVScreenerError):
    pass


class ConfigError(TVScreenerError):
    pass
