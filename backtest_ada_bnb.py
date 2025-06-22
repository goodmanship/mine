from datetime import datetime

from backtester import PairTradingBacktester

# Use the actual date range of your data
START_DATE = datetime(2024, 6, 21, 22, 0, 0)
END_DATE = datetime(2025, 6, 12, 21, 0, 0)

print("Running ADA/BNB pair trading backtest:")
print(f"Start: {START_DATE}")
print(f"End: {END_DATE}")
print("Initial Capital: $100")

# Run backtest
bt = PairTradingBacktester(100)
portfolio = bt.backtest_mean_reversion("ADA/USDT", "BNB/USDT", START_DATE, END_DATE)
results = bt.analyze_results(portfolio, "ADA/USDT", "BNB/USDT")

print("\n" + "=" * 50)
print("BACKTEST RESULTS")
print("=" * 50)

print(f"Initial Capital: ${results['initial_capital']:,.2f}")
print(f"Final Value: ${results['final_value']:,.2f}")
print(f"Total Return: {results['total_return_pct']:+.2f}%")
print(f"Buy & Hold Return: {results['buy_hold_return_pct']:+.2f}%")
print(f"Excess Return: {results['excess_return_pct']:+.2f}%")
print(f"Volatility: {results['volatility_pct']:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Total Trades: {results['total_trades']:,}")
print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
print(f"Win Rate: {results['win_rate_pct']:.1f}%")

print("\n" + "=" * 50)
print("INTERPRETATION")
print("=" * 50)

if results["excess_return_pct"] > 0:
    print("✅ Strategy outperformed buy & hold")
else:
    print("❌ Strategy underperformed buy & hold")

if results["sharpe_ratio"] > 1:
    print("✅ Good risk-adjusted returns")
else:
    print("⚠️  Poor risk-adjusted returns")

if results["total_trades"] > 1000:
    print("⚠️  High number of trades (high transaction costs)")
else:
    print("✅ Reasonable number of trades")

if results["max_drawdown_pct"] < -20:
    print("⚠️  High maximum drawdown")
else:
    print("✅ Acceptable maximum drawdown")

print("\n" + "=" * 50)
print("COMPARISON WITH OTHER PAIRS")
print("=" * 50)
print("ADA/BNB correlation: Should be high (both correlated with BTC)")
print("BTC/BNB correlation: 0.947 (very high)")
print("BTC/ADA correlation: 0.947 (very high)")
print("ETH/BTC correlation: 0.132 (very low)")
print("Should perform well if ADA/BNB correlation is high!")
