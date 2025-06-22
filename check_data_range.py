from datetime import datetime, timedelta

from analyzer import CryptoAnalyzer
from database import get_db_session, get_price_data


def check_data_range():
    """Check the date range of our collected data."""
    analyzer = CryptoAnalyzer()

    symbols = ["SOL/USDT", "ADA/USDT", "BTC/USDT", "ETH/USDT", "BNB/USDT"]

    print("Checking data ranges for each symbol:")
    print("=" * 60)

    for symbol in symbols:
        # Get all data for this symbol
        with get_db_session() as db:
            data = get_price_data(db, symbol, limit=None)

        if data:
            earliest = min(row.timestamp for row in data)
            latest = max(row.timestamp for row in data)
            count = len(data)

            print(f"{symbol}:")
            print(f"  Records: {count:,}")
            print(f"  Date range: {earliest.strftime('%Y-%m-%d %H:%M')} to {latest.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Days of data: {(latest - earliest).days}")
            print()
        else:
            print(f"{symbol}: No data found")
            print()

    # Check if we have enough data for 1-year backtest
    one_year_ago = datetime.now() - timedelta(days=365)
    print(f"One year ago: {one_year_ago.strftime('%Y-%m-%d %H:%M')}")

    # Test SOL/ADA data availability
    sol_data = analyzer.get_data_as_dataframe("SOL/USDT", one_year_ago)
    ada_data = analyzer.get_data_as_dataframe("ADA/USDT", one_year_ago)

    print(f"\nSOL/USDT data from 1 year ago: {len(sol_data)} records")
    print(f"ADA/USDT data from 1 year ago: {len(ada_data)} records")

    if len(sol_data) > 0 and len(ada_data) > 0:
        print("✅ Sufficient data for 1-year backtest!")
        return True
    else:
        print("❌ Need to collect more historical data for 1-year backtest")
        return False


if __name__ == "__main__":
    check_data_range()
