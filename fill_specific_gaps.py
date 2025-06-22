import time
from datetime import datetime

from data_collector import BinanceDataCollector

SYMBOLS = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "BNB/USDT", "SOL/USDT"]
RATE_LIMIT_SLEEP = 0.1  # 10 requests/sec

# Specific gaps identified (all 244 hours each)
GAPS = [
    ("2024-08-02 18:00:00", "2024-08-12 21:00:00"),
    ("2024-09-02 18:00:00", "2024-09-12 21:00:00"),
    ("2024-10-03 18:00:00", "2024-10-13 21:00:00"),
    ("2024-11-03 18:00:00", "2024-11-13 21:00:00"),
    ("2024-12-04 18:00:00", "2024-12-14 21:00:00"),
    ("2025-01-04 18:00:00", "2025-01-14 21:00:00"),
    ("2025-02-04 18:00:00", "2025-02-14 21:00:00"),
    ("2025-03-07 18:00:00", "2025-03-17 21:00:00"),
    ("2025-04-07 18:00:00", "2025-04-17 21:00:00"),
    ("2025-05-08 18:00:00", "2025-05-18 21:00:00"),
]

collector = BinanceDataCollector()

print(f"Filling {len(GAPS)} specific gaps for {len(SYMBOLS)} symbols...")

for symbol in SYMBOLS:
    print(f"\nProcessing {symbol}...")
    for gap_start_str, gap_end_str in GAPS:
        gap_start = datetime.fromisoformat(gap_start_str.replace("Z", "+00:00"))
        gap_end = datetime.fromisoformat(gap_end_str.replace("Z", "+00:00"))

        print(f"  Filling gap: {gap_start} to {gap_end}")

        try:
            df = collector.fetch_ohlcv(symbol, timeframe="1h", since=gap_start, limit=None)
            if not df.empty:
                # Only keep rows within the gap
                df = df[(df["timestamp"] >= gap_start) & (df["timestamp"] <= gap_end)]
                collector.save_to_database(symbol, df, timeframe="1h")
                print(f"    ✓ Saved {len(df)} records.")
            else:
                print("    No data returned.")
        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(RATE_LIMIT_SLEEP)

print("\nSpecific gap filling complete!")
