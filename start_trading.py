#!/usr/bin/env python3
"""
Live Pair Trading Launcher
Simple script to start the ADA/BNB pair trading system
"""

import asyncio
import os
import sys

import trading_config as config
from live_pair_trader import LivePairTrader


def print_banner():
    """Print startup banner."""
    print("=" * 70)
    print("🚀 LIVE PAIR TRADING SYSTEM")
    print("=" * 70)
    print(f"Trading Pair: {config.SYMBOL1} vs {config.SYMBOL2}")
    print(f"Initial Capital: ${config.INITIAL_CAPITAL:,.2f}")
    print(f"Paper Trading: {'✅ ENABLED' if config.PAPER_TRADING else '❌ DISABLED'}")
    print(f"Update Interval: {config.UPDATE_INTERVAL} seconds")
    print(f"Z-Score Threshold: {config.Z_THRESHOLD}")
    print(f"Lookback Period: {config.LOOKBACK_PERIOD}")
    print("=" * 70)


def check_environment():
    """Check if environment is properly set up."""
    print("🔍 Checking environment...")

    # Check if required packages are installed
    try:
        import importlib.util

        packages = ["ccxt", "numpy", "pandas"]
        for package in packages:
            if importlib.util.find_spec(package) is None:
                print(f"❌ Missing package: {package}")
                return False
        print("✅ Required packages installed")
    except Exception as e:
        print(f"❌ Error checking packages: {e}")
        return False

    # Check if API keys are set (for real trading)
    if not config.PAPER_TRADING:
        if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_SECRET"):
            print("❌ API keys not set for real trading")
            print("   Set BINANCE_API_KEY and BINANCE_SECRET environment variables")
            return False
        else:
            print("✅ API keys configured")
    else:
        print("✅ Paper trading mode - no API keys required")

    return True


def main():
    """Main launcher function."""
    print_banner()

    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)

    # Confirm settings
    print("\n📋 Trading Configuration:")
    print(f"   Symbols: {config.SYMBOL1} vs {config.SYMBOL2}")
    print(f"   Capital: ${config.INITIAL_CAPITAL:,.2f}")
    print(f"   Mode: {'Paper Trading' if config.PAPER_TRADING else 'Real Trading'}")
    print(f"   Z-Threshold: {config.Z_THRESHOLD}")
    print(f"   Update Interval: {config.UPDATE_INTERVAL}s")

    if config.PAPER_TRADING:
        print("\n⚠️  WARNING: This is PAPER TRADING mode.")
        print("   No real money will be traded.")
    else:
        print("\n⚠️  WARNING: This is REAL TRADING mode.")
        print("   Real money will be traded!")
        confirm = input("\nAre you sure you want to proceed with real trading? (yes/no): ")
        if confirm.lower() != "yes":
            print("Trading cancelled.")
            sys.exit(0)

    # Initialize trader
    print("\n🚀 Initializing trader...")
    trader = LivePairTrader(
        symbol1=config.SYMBOL1,
        symbol2=config.SYMBOL2,
        initial_capital=config.INITIAL_CAPITAL,
        lookback_period=config.LOOKBACK_PERIOD,
        z_threshold=config.Z_THRESHOLD,
        paper_trading=config.PAPER_TRADING,
    )

    # Load previous state if exists
    trader.load_state()

    print("\n✅ Trader initialized successfully!")
    print("📊 Starting trading loop...")
    print("   Press Ctrl+C to stop trading")
    print("=" * 70)

    # Run trading loop
    try:
        asyncio.run(trader.run_trading_loop(update_interval=config.UPDATE_INTERVAL))
    except KeyboardInterrupt:
        print("\n\n🛑 Trading stopped by user")
        trader.save_state()
        print("💾 Trading state saved")
    except Exception as e:
        print(f"\n❌ Error in trading loop: {e}")
        trader.save_state()
        print("💾 Trading state saved")
        sys.exit(1)


if __name__ == "__main__":
    main()
