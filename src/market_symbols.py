"""
S&P 500 hisse sembol listesi.
Market scanner için kullanılır.
"""

import logging

from .constants import MARKET_CAP_THRESHOLD

logger = logging.getLogger(__name__)


def get_sp500_symbols() -> list[str]:
    """
    S&P 500 endeksindeki hisse sembollerini döndürür.
    
    Not: Bu liste periyodik olarak güncellenmelidir (yılda 1-2 kez).
    Kaynak: S&P 500 endeksi resmi bileşenleri.
    
    Returns:
        List[str]: S&P 500 hisse sembolleri
    """
    # S&P 500 hisse sembolleri (Kasım 2024 itibariyle)
    # Alfabetik sırada, bakımı kolay olması için
    symbols = [
        "A", "AAL", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI",
        "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG",
        "AKAM", "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN",
        "AMP", "AMT", "AMZN", "ANET", "AON", "AOS", "APA", "APD", "APH",
        "APTV", "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK", "AXON", "AXP", "AZO",
        "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF-B", "BG",
        "BIIB", "BIO", "BK", "BKNG", "BKR", "BLDR", "BLK", "BMY", "BR", "BRK-B",
        "BRO", "BSX", "BWA", "BX", "BXP", "C", "CAG", "CAH", "CARR", "CAT",
        "CB", "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CE", "CEG", "CF",
        "CFG", "CHD", "CHRW", "CHTR", "CI", "CINF", "CL", "CLX", "CMCSA", "CME",
        "CMG", "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP", "COR", "COST",
        "CPAY", "CPB", "CPRT", "CPT", "CRL", "CRM", "CSCO", "CSGP", "CSX", "CTAS",
        "CTLT", "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", "D", "DAL", "DAY",
        "DD", "DE", "DECK", "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DLR",
        "DLTR", "DOC", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN",
        "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EG", "EIX", "EL", "ELV",
        "EMN", "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ES", "ESS",
        "ETN", "ETR", "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", "F",
        "FANG", "FAST", "FCX", "FDS", "FDX", "FE", "FFIV", "FI", "FICO", "FIS",
        "FITB", "FLT", "FMC", "FOX", "FOXA", "FRT", "FSLR", "FTNT", "FTV", "GD",
        "GDDY", "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL", "GLW", "GM",
        "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW", "HAL", "HAS",
        "HBAN", "HCA", "HD", "HES", "HIG", "HII", "HLT", "HOLX", "HON", "HPE",
        "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM", "IBM", "ICE",
        "IDXX", "IEX", "IFF", "INCY", "INTC", "INTU", "INVH", "IP", "IPG", "IQV",
        "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT", "JBL", "JCI",
        "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP", "KEY", "KEYS", "KHC", "KIM",
        "KKR", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "KVUE", "L", "LDOS",
        "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT", "LNT", "LOGI", "LOW",
        "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR",
        "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM",
        "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS",
        "MPC", "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB",
        "MTCH", "MTD", "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI",
        "NKE", "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR",
        "NWS", "NWSA", "NXPI", "O", "ODFL", "OKE", "OMC", "ON", "ORCL", "ORLY",
        "OTIS", "OXY", "PANW", "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEG", "PEP",
        "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PLD", "PM", "PNC",
        "PNR", "PNW", "PODD", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC",
        "PWR", "PYPL", "QCOM", "QRVO", "RCL", "RE", "REG", "REGN", "RF", "RHI",
        "RJF", "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG", "RTX", "RVTY",
        "SBAC", "SBUX", "SCHW", "SHW", "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO",
        "SPG", "SPGI", "SRE", "STE", "STLD", "STT", "STX", "STZ", "SWK", "SWKS",
        "SYF", "SYK", "SYY", "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER",
        "TFC", "TFX", "TGT", "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW",
        "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL",
        "UBER", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V",
        "VICI", "VLO", "VLTO", "VMC", "VRSK", "VRSN", "VRTX", "VST", "VTR", "VTRS",
        "VZ", "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WM",
        "WMB", "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN", "XEL", "XOM",
        "XYL", "YUM", "ZBH", "ZBRA", "ZTS"
    ]

    logger.info(f"S&P 500 listesi yüklendi: {len(symbols)} sembol")
    return symbols


def get_market_cap_threshold() -> float:
    """
    Market scanner için minimum market cap eşiği (USD).
    
    Returns:
        float: Minimum market cap (50 milyar USD)
    """
    return MARKET_CAP_THRESHOLD
