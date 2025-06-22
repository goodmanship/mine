from datetime import datetime

from src.analyze.analyzer import CryptoAnalyzer

# Use the actual date range of your data
START_DATE = datetime(2024, 6, 21, 22, 0, 0)
END_DATE = datetime(2025, 6, 12, 21, 0, 0)

SYMBOLS = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "BNB/USDT", "SOL/USDT"]

print("Generating correlation matrix for full year:")
print(f"Start: {START_DATE}")
print(f"End: {END_DATE}")
print(f"Symbols: {SYMBOLS}")

analyzer = CryptoAnalyzer()

# Calculate correlation matrix using the actual full year range
correlation_matrix = analyzer.calculate_correlation_matrix(symbols=SYMBOLS, start_date=START_DATE, end_date=END_DATE, timeframe="1h")

print("\nCorrelation Matrix:")
print(correlation_matrix.round(3))

# Also generate the heatmap
analyzer.plot_correlation_heatmap(symbols=SYMBOLS, start_date=START_DATE, end_date=END_DATE, timeframe="1h")
