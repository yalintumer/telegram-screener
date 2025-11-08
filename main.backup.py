"""
Backup of original main.py before workspace reorganization.
This file was created automatically.
"""

import yaml, time, os
from capture import capture
from ocr import extract_tickers
import watchlist
from telegram_client import TelegramClient
from indicators import stochastic_rsi, stoch_rsi_buy
from data_source import daily_ohlc

def load_cfg():
    with open("config.yaml") as f: return yaml.safe_load(f)

def refresh_watchlist(cfg):
    path = capture(cfg["screen"]["region"])
    tickers = extract_tickers(path)
    os.remove(path)  # ekran görüntüsü sil
    watchlist.add(tickers)
    watchlist.prune(cfg["data"]["max_watch_days"])

def scan_signals(cfg):
    tg = TelegramClient(cfg["telegram"]["bot_token"], cfg["telegram"]["chat_id"])
    api_key = cfg["api"]["token"]
    symbols = watchlist.all_symbols()
    for s in symbols:
        try:
            df = daily_ohlc(s, api_key)
            if df is None or len(df) < 30: continue
            ind = stochastic_rsi(df["close"],
                                 rsi_period=cfg["indicators"]["rsi_period"],
                                 stoch_period=cfg["indicators"]["stoch_rsi_period"],
                                 k=cfg["indicators"]["k"],
                                 d=cfg["indicators"]["d"])
            if stoch_rsi_buy(ind):
                tg.send(f"{s} Stoch RSI AL sinyali")
        except Exception as e:
            print("Err", s, e)

if __name__ == "__main__":
    cfg = load_cfg()
    refresh_watchlist(cfg)
    for _ in range(6):
        scan_signals(cfg)
        time.sleep(3600)
