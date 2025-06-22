from sqlalchemy import text

from database import get_db_session

with get_db_session() as session:
    # List tables
    result = session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
    print("Tables in database:")
    for row in result:
        print(f"  - {row.table_name}")

    # Show data range for crypto_prices
    result = session.execute(
        text("SELECT symbol, COUNT(*) as count, MIN(timestamp) as earliest, MAX(timestamp) as latest FROM crypto_prices GROUP BY symbol")
    )
    print("\nData in crypto_prices:")
    for row in result:
        print(f"{row.symbol}: {row.count} records from {row.earliest} to {row.latest}")

    # Check what years we actually have data for
    print("\nChecking what years we have data for:")
    result = session.execute(text("SELECT DISTINCT EXTRACT(YEAR FROM timestamp) as year FROM crypto_prices ORDER BY year"))
    for row in result:
        print(f"  Year: {row.year}")

    # Check data range
    cursor = session.execute(text("SELECT symbol, MIN(timestamp) as earliest, MAX(timestamp) as latest FROM crypto_prices GROUP BY symbol"))
    data_ranges = cursor.fetchall()
    print("\nData ranges by symbol:")
    for symbol, earliest, latest in data_ranges:
        print(f"  {symbol}: {earliest} to {latest}")

    # Check recent data
    print("\nRecent data (last 7 days):")
    cursor = session.execute(
        text(
            "SELECT symbol, timestamp, price FROM crypto_prices "
            "WHERE timestamp >= '2024-12-30' AND timestamp <= '2025-01-05' "
            "ORDER BY timestamp, symbol LIMIT 20"
        )
    )
    result = cursor.fetchall()
    count = 0
    for row in result:
        print(f"{row.timestamp}: {row.symbol} = ${row.price}")
        count += 1

    if count == 0:
        print("No data found for this date range!")
    else:
        print(f"\nTotal records in date range: {count}")

    # Check the actual latest timestamps
    print("\nLatest 10 timestamps in database:")
    result = session.execute(text("SELECT DISTINCT timestamp FROM crypto_prices ORDER BY timestamp DESC LIMIT 10"))
    for row in result:
        print(f"  {row.timestamp}")
