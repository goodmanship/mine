from datetime import timedelta

import pandas as pd
from sqlalchemy import text

from database import get_db_session

SYMBOLS = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "BNB/USDT", "SOL/USDT"]

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
            print("  No data found!")
            continue
        df = pd.DataFrame({"timestamp": timestamps})
        df = df.sort_values("timestamp")
        df["diff"] = df["timestamp"].diff()
        # Find gaps greater than 1 hour
        gaps = df[df["diff"] > timedelta(hours=1)]
        if gaps.empty:
            print("  No gaps found!")
        else:
            for idx, row in gaps.iterrows():
                prev_time = df.loc[idx - 1, "timestamp"]
                gap_start = prev_time + timedelta(hours=1)
                gap_end = row["timestamp"] - timedelta(hours=1)
                print(f"  Gap: {gap_start} to {gap_end} (missing {int((gap_end - gap_start).total_seconds() // 3600 + 1)} hours)")
        # Also check for missing data at the start or end
        first = df["timestamp"].iloc[0]
        last = df["timestamp"].iloc[-1]
        print(f"  Data range: {first} to {last}")
