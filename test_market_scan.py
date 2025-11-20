#!/usr/bin/env python3
"""
Test script for market scanner - scans only first 10 S&P 500 symbols
"""

import time
from src.config import Config
from src.notion_client import NotionClient
from src.main import check_market_filter
from src.market_symbols import get_sp500_symbols

def test_market_scan():
    """Test market scanner with first 10 symbols"""
    
    print("=" * 60)
    print("🧪 MARKET SCANNER TEST (First 10 symbols)")
    print("=" * 60)
    
    # Load config
    cfg = Config.load("config.yaml")
    
    # Initialize Notion client
    notion = NotionClient(
        api_token=cfg.notion.api_token,
        database_id=cfg.notion.database_id,
        signals_database_id=cfg.notion.signals_database_id,
        buy_database_id=cfg.notion.buy_database_id
    )
    
    # Get current watchlist
    print("\n📋 Checking current watchlist...")
    existing_symbols, symbol_to_page = notion.get_watchlist()
    print(f"   Found {len(existing_symbols)} symbols in watchlist")
    if existing_symbols:
        print(f"   Existing: {', '.join(list(existing_symbols)[:5])}{'...' if len(existing_symbols) > 5 else ''}")
    
    # Get first 10 S&P 500 symbols for testing
    sp500_symbols = get_sp500_symbols()[:10]
    
    print(f"\n🔍 Testing with {len(sp500_symbols)} symbols:")
    print(f"   {', '.join(sp500_symbols)}\n")
    
    found_count = 0
    updated_count = 0
    added_count = 0
    
    for i, symbol in enumerate(sp500_symbols, 1):
        print(f"[{i}/{len(sp500_symbols)}] Checking {symbol}...", end=" ")
        
        # Check market filters
        result = check_market_filter(symbol)
        
        if result is None:
            print("❌ Data unavailable")
            continue
        
        if result.get('passed'):
            found_count += 1
            print(f"✅ MATCH!")
            print(f"    Market Cap: ${result['market_cap']/1e9:.1f}B")
            print(f"    Stoch RSI D: {result['stoch_d']:.1f}")
            print(f"    Price: ${result['price']:.2f} < BB Lower: ${result['bb_lower']:.2f}")
            print(f"    MFI: {result['mfi']:.1f}")
            
            # Check if already in watchlist
            if symbol in existing_symbols:
                print(f"    → Already in watchlist, would UPDATE date")
                # Don't actually update in test
                updated_count += 1
            else:
                print(f"    → New symbol, would ADD to watchlist")
                # Don't actually add in test
                added_count += 1
        else:
            reason = result.get('reason', 'unknown')
            print(f"⏭️  Rejected: {reason}")
        
        # Small delay to avoid rate limits
        time.sleep(0.5)
    
    # Summary
    print(f"\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print("=" * 60)
    print(f"   Symbols checked: {len(sp500_symbols)}")
    print(f"   Matches found: {found_count}")
    print(f"   Would update: {updated_count}")
    print(f"   Would add: {added_count}")
    print("=" * 60)
    
    if found_count > 0:
        print("\n✅ Test successful! Market scanner logic is working.")
        print("   Ready to run full scan with --market-scan flag")
    else:
        print("\n⚠️  No matches found in test symbols.")
        print("   This is normal - criteria are strict.")
        print("   Full S&P 500 scan will likely find more.")
    
    print("\n💡 To run full scan:")
    print("   python -m src.main --market-scan")

if __name__ == "__main__":
    test_market_scan()
