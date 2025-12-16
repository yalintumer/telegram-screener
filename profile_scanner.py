#!/usr/bin/env python3
"""
Performance profiling script for the scanner.

Uses pyinstrument for sampling-based profiling.
Analyzes symbol processing times and identifies slow functions.
"""
import time
import json
from datetime import datetime
from pathlib import Path

from pyinstrument import Profiler

# Import scanner components
from src.data_source_yfinance import daily_ohlc
from src.indicators import rsi, stochastic_rsi, mfi, wavetrend
from src.market_symbols import get_sp500_symbols


def profile_symbol(symbol: str) -> dict:
    """Profile a single symbol processing time."""
    result = {
        "symbol": symbol,
        "fetch_time": 0,
        "indicator_time": 0,
        "total_time": 0,
        "success": False,
        "error": None,
    }
    
    start_total = time.perf_counter()
    
    try:
        # Fetch data
        start_fetch = time.perf_counter()
        df = daily_ohlc(symbol, days=100)
        result["fetch_time"] = time.perf_counter() - start_fetch
        
        if df is None or len(df) < 30:
            result["error"] = "Insufficient data"
            result["total_time"] = time.perf_counter() - start_total
            return result
        
        # Calculate indicators
        start_indicators = time.perf_counter()
        
        rsi_series = rsi(df['Close'])
        stoch_df = stochastic_rsi(df['Close'])
        mfi_series = mfi(df)
        wt_df = wavetrend(df)
        
        result["indicator_time"] = time.perf_counter() - start_indicators
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)[:100]
    
    result["total_time"] = time.perf_counter() - start_total
    return result


def run_profiling(max_symbols: int = 50):
    """
    Run profiling on a subset of S&P 500 symbols.
    
    Args:
        max_symbols: Maximum number of symbols to profile
    """
    print("=" * 60)
    print("📊 PERFORMANCE PROFILING")
    print("=" * 60)
    print(f"\nProfiling {max_symbols} symbols...\n")
    
    symbols = get_sp500_symbols()[:max_symbols]
    results = []
    
    # Profile with pyinstrument
    profiler = Profiler()
    profiler.start()
    
    for i, symbol in enumerate(symbols):
        result = profile_symbol(symbol)
        results.append(result)
        
        status = "✅" if result["success"] else "❌"
        print(f"[{i+1:3}/{max_symbols}] {symbol:5} {status} "
              f"fetch={result['fetch_time']:.2f}s "
              f"calc={result['indicator_time']:.2f}s "
              f"total={result['total_time']:.2f}s")
    
    profiler.stop()
    
    # Analyze results
    print("\n" + "=" * 60)
    print("📈 ANALYSIS RESULTS")
    print("=" * 60)
    
    # Sort by total time
    sorted_results = sorted(results, key=lambda x: x["total_time"], reverse=True)
    
    # Top 20 slowest symbols
    print("\n🐢 TOP 20 SLOWEST SYMBOLS:")
    print("-" * 55)
    print(f"{'Rank':<5} {'Symbol':<8} {'Fetch':>8} {'Calc':>8} {'Total':>8} {'Status':<10}")
    print("-" * 55)
    
    for i, r in enumerate(sorted_results[:20], 1):
        status = "OK" if r["success"] else r["error"][:15] if r["error"] else "FAIL"
        print(f"{i:<5} {r['symbol']:<8} {r['fetch_time']:>7.2f}s {r['indicator_time']:>7.2f}s "
              f"{r['total_time']:>7.2f}s {status:<10}")
    
    # Statistics
    successful = [r for r in results if r["success"]]
    if successful:
        avg_fetch = sum(r["fetch_time"] for r in successful) / len(successful)
        avg_calc = sum(r["indicator_time"] for r in successful) / len(successful)
        avg_total = sum(r["total_time"] for r in successful) / len(successful)
        
        print("\n📊 STATISTICS:")
        print("-" * 40)
        print(f"  Successful symbols: {len(successful)}/{len(results)}")
        print(f"  Average fetch time: {avg_fetch:.3f}s")
        print(f"  Average calc time:  {avg_calc:.3f}s")
        print(f"  Average total time: {avg_total:.3f}s")
        print(f"  Total time:         {sum(r['total_time'] for r in results):.1f}s")
    
    # Print pyinstrument output
    print("\n" + "=" * 60)
    print("🔬 FUNCTION-LEVEL PROFILING (pyinstrument)")
    print("=" * 60)
    print(profiler.output_text(unicode=True, color=False, show_all=False))
    
    # Save results
    output_file = Path("profiling_results.json")
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "symbols_profiled": max_symbols,
            "results": sorted_results,
        }, f, indent=2)
    
    print(f"\n📁 Results saved to: {output_file}")
    
    return sorted_results, profiler


if __name__ == "__main__":
    import sys
    
    max_symbols = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_profiling(max_symbols)
