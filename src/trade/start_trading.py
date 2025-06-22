#!/usr/bin/env python3
"""
Live Pair Trading Launcher
Simple script to start the ADA/BNB pair trading system
"""

import asyncio
import os
import time

from src.core.app_config import config
from src.trade.live_pair_trader import LivePairTrader


def print_banner():
    """Print the startup banner."""
    print("\n" + "=" * 70)
    print("🚀 LIVE PAIR TRADING SYSTEM")
    print("=" * 70)
    print(f"Trading Pair: {config.SYMBOL1} vs {config.SYMBOL2}")  # type: ignore
    print(f"Initial Capital: ${config.INITIAL_CAPITAL:,.2f}")  # type: ignore
    print(f"Paper Trading: {'✅ ENABLED' if config.PAPER_TRADING else '❌ DISABLED'}")  # type: ignore
    print(f"Update Interval: {config.UPDATE_INTERVAL} seconds")  # type: ignore
    print(f"Z-Score Threshold: {config.Z_THRESHOLD}")  # type: ignore
    print(f"Lookback Period: {config.LOOKBACK_PERIOD}")  # type: ignore
    print("=" * 70)


def check_prerequisites():
    """Check that required prerequisites are met."""
    print("\n🔍 Checking prerequisites...")

    # Check Python environment
    print("✅ Python environment: OK")

    # Check database connection
    try:
        from src.core.database import get_db_session

        with get_db_session():
            print("✅ Database connection: OK")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your DATABASE_URL configuration.")
        return False

    # Check data availability
    try:
        from src.core.database import get_db_session, get_price_data

        with get_db_session() as db:
            ada_data = get_price_data(db, "ADA/USDT", limit=10)
            bnb_data = get_price_data(db, "BNB/USDT", limit=10)

        if not ada_data or not bnb_data:
            print("❌ Insufficient price data for trading pairs")
            print("Please run data collection first using 'make collect-data'")
            return False

        print("✅ Price data availability: OK")
    except Exception as e:
        print(f"❌ Error checking price data: {e}")
        return False

    # Check if API keys are set (for real trading)
    if not config.PAPER_TRADING:  # type: ignore
        if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_SECRET"):
            print("❌ API keys not set for real trading")
            print("Please set BINANCE_API_KEY and BINANCE_SECRET environment variables")
            return False
        print("✅ API credentials: OK")
    else:
        print("✅ Paper trading mode: No API keys required")

    return True


def get_user_confirmation():
    """Get user confirmation before starting trading."""
    print("\n⚠️  IMPORTANT DISCLAIMERS:")
    print("   • This is experimental software")
    print("   • Past performance does not guarantee future results")
    print("   • You could lose money, even in paper trading mode")
    print("   • Please review the code and test thoroughly before using real money")

    # Show current mode
    if config.PAPER_TRADING:  # type: ignore
        print("\n🧪 PAPER TRADING MODE")
        print("   • No real money will be used")
        print("   • This is for testing and learning purposes")
    else:
        print("\n💰 REAL TRADING MODE")
        print("   • REAL MONEY WILL BE USED")
        print("   • TRADES WILL BE EXECUTED ON THE EXCHANGE")
        print("   • YOU COULD LOSE MONEY")

    # Confirm settings
    print("\n📋 Trading Configuration:")
    print(f"   Symbols: {config.SYMBOL1} vs {config.SYMBOL2}")  # type: ignore
    print(f"   Capital: ${config.INITIAL_CAPITAL:,.2f}")  # type: ignore
    print(f"   Mode: {'Paper Trading' if config.PAPER_TRADING else 'Real Trading'}")  # type: ignore
    print(f"   Z-Threshold: {config.Z_THRESHOLD}")  # type: ignore
    print(f"   Update Interval: {config.UPDATE_INTERVAL}s")  # type: ignore

    if config.PAPER_TRADING:  # type: ignore
        print("\n⚠️  WARNING: This is PAPER TRADING mode.")
        print("   No real money will be traded.")
        print("   Results are simulated and may not reflect real trading conditions.")
    else:
        print("\n🚨 DANGER: This is REAL TRADING mode!")
        print("   Real money will be used for trades.")
        print("   You could lose significant amounts of money.")
        print("   Make sure you understand the risks!")

    # Get confirmation
    response = input("\n❓ Do you want to continue? (yes/no): ").strip().lower()
    return response in ["yes", "y"]


def main():
    """Main entry point for live pair trading."""
    print_banner()

    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above.")
        return

    if not get_user_confirmation():
        print("\n🛑 Trading cancelled by user.")
        return

    print("\n🚀 Initializing trader...")
    trader = LivePairTrader(
        symbol1=config.SYMBOL1,  # type: ignore
        symbol2=config.SYMBOL2,  # type: ignore
        initial_capital=config.INITIAL_CAPITAL,  # type: ignore
        lookback_period=config.LOOKBACK_PERIOD,  # type: ignore
        z_threshold=config.Z_THRESHOLD,  # type: ignore
        paper_trading=config.PAPER_TRADING,  # type: ignore
    )

    # Load previous state if exists
    print("📂 Loading previous trading state...")
    trader.load_state()

    print("\n🎯 Starting trading loop...")
    print("   Press Ctrl+C to stop trading")
    print("   Trading state is automatically saved")

    time.sleep(2)  # Give user time to read

    # Run trading loop
    try:
        asyncio.run(trader.run_trading_loop(update_interval=config.UPDATE_INTERVAL))  # type: ignore
    except KeyboardInterrupt:
        print("\n\n🛑 Trading stopped by user")
        trader.save_state()
        print("💾 Trading state saved")
    except Exception as e:
        print(f"\n\n💥 Error during trading: {e}")
        trader.save_state()
        print("💾 Trading state saved")
        raise

    print("\n👋 Trading session ended")


if __name__ == "__main__":
    main()
