import time
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import text

from data_collector import BinanceDataCollector
from database import get_db_session

SYMBOLS = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "BNB/USDT", "SOL/USDT"]
CHUNK_DAYS = 31  # Monthly chunks
RATE_LIMIT_SLEEP = 0.1  # 10 requests/sec

collector = BinanceDataCollector()

with get_db_session() as session:
    for symbol in SYMBOLS:
        print(f"\nChecking gaps for {symbol}...")
        result = session.execute(
            text("""
            SELECT timestamp FROM crypto_prices
            WHERE symbol = :symbol
            ORDER BY timestamp
        """),
            {"symbol": symbol},
        )
        timestamps = [row.timestamp for row in result]
        if not timestamps:
            print("  No data found! Will backfill entire year.")
            # If no data, set a default range (adjust as needed)
            start = datetime(2024, 6, 21, 22)
            end = datetime(2025, 6, 12, 21)
            gaps = [(start, end)]
        else:
            df = pd.DataFrame({"timestamp": timestamps})
            df = df.sort_values("timestamp")
            df["diff"] = df["timestamp"].diff()
            # Find gaps greater than 1 hour
            gaps = []
            for idx, row in df[df["diff"] > timedelta(hours=1)].iterrows():
                prev_time = df.loc[idx - 1, "timestamp"]
                gap_start = prev_time + timedelta(hours=1)
                gap_end = row["timestamp"] - timedelta(hours=1)
                gaps.append((gap_start, gap_end))
            # Also check for missing data at the start
            first = df["timestamp"].iloc[0]
            if first > datetime(2024, 6, 21, 22):
                gaps.insert(0, (datetime(2024, 6, 21, 22), first - timedelta(hours=1)))
            # And at the end
            last = df["timestamp"].iloc[-1]
            if last < datetime(2025, 6, 12, 21):
                gaps.append((last + timedelta(hours=1), datetime(2025, 6, 12, 21)))
        if not gaps:
            print("  No gaps found!")
            continue
        for gap_start, gap_end in gaps:
            print(f"  Backfilling {symbol}: {gap_start} to {gap_end}")
            chunk_start = gap_start
            while chunk_start <= gap_end:
                # Fix: Ensure chunks overlap properly to avoid gaps
                chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS - 1, hours=23), gap_end)
                print(f"    Fetching {chunk_start} to {chunk_end}...")
                try:
                    df = collector.fetch_ohlcv(symbol, timeframe="1h", since=chunk_start, limit=None)
                    if not df.empty:
                        # Only keep rows within chunk_start and chunk_end
                        df = df[(df["timestamp"] >= chunk_start) & (df["timestamp"] <= chunk_end)]
                        collector.save_to_database(symbol, df, timeframe="1h")
                        print(f"    ✓ Saved {len(df)} records.")
                    else:
                        print("    No data returned.")
                except Exception as e:
                    print(f"    Error: {e}")
                time.sleep(RATE_LIMIT_SLEEP)
                # Fix: Move to next chunk with proper overlap
                chunk_start = chunk_end + timedelta(hours=1)
print("\nBackfill complete!")
