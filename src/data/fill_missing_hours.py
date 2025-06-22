import time
from datetime import datetime, timedelta

from sqlalchemy import text

from src.core.database import get_db_session
from src.data.data_collector import BinanceDataCollector

SYMBOLS = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "BNB/USDT", "SOL/USDT"]
RATE_LIMIT_SLEEP = 0.1  # 10 requests/sec

# Set your desired range here
START = datetime(2024, 6, 21, 22)
END = datetime(2025, 6, 12, 21)

collector = BinanceDataCollector()

with get_db_session() as session:
    current = START
    total_missing = 0
    while current <= END:
        missing_symbols = []
        for symbol in SYMBOLS:
            result = session.execute(
                text("SELECT 1 FROM crypto_prices WHERE symbol = :symbol AND timestamp = :timestamp LIMIT 1"),
                {"symbol": symbol, "timestamp": current},
            )
            if not result.first():
                missing_symbols.append(symbol)
        if missing_symbols:
            print(f"{current}: Missing {missing_symbols}")
            for symbol in missing_symbols:
                try:
                    df = collector.fetch_ohlcv(symbol, timeframe="1h", since=current, limit=1)
                    if not df.empty:
                        # Only keep the row for the exact hour
                        df = df[df["timestamp"] == current]
                        if not df.empty:
                            collector.save_to_database(symbol, df, timeframe="1h")
                            print(f"  ✓ Filled {symbol} for {current}")
                            total_missing += 1
                        else:
                            print(f"  No data returned for {symbol} at {current}")
                    else:
                        print(f"  No data returned for {symbol} at {current}")
                except Exception as e:
                    print(f"  Error fetching {symbol} at {current}: {e}")
                time.sleep(RATE_LIMIT_SLEEP)
        current += timedelta(hours=1)
print(f"\nDone! Filled {total_missing} missing data points.")
