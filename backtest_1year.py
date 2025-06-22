from datetime import datetime, timedelta

from backtester import PairTradingBacktester


def run_1year_backtest():
    """Run a 1-year backtest with the best parameters we found."""

    backtester = PairTradingBacktester(initial_capital=100)

    # Test SOL/ADA pair trading with 1-year lookback
    symbol1 = "SOL/USDT"
    symbol2 = "ADA/USDT"

    # Try to get 1 year of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    print(f"Attempting 1-year backtest for {symbol1} vs {symbol2}")
    print(f"Requested period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print()

    # Get the actual data range available
    df = backtester.get_pair_data(symbol1, symbol2, start_date, end_date)

    if df.empty:
        print("❌ No data available for backtesting")
        return

    actual_start = df.index.min()
    actual_end = df.index.max()
    actual_days = (actual_end - actual_start).days

    print("✅ Actual data available:")
    print(f"   Start: {actual_start.strftime('%Y-%m-%d %H:%M')}")
    print(f"   End: {actual_end.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Days: {actual_days}")
    print(f"   Records: {len(df)}")
    print()

    # Run backtest with optimal parameters from tuning
    print("Running backtest with optimal parameters (Z=1.0, Size=0.75)...")
    portfolio = backtester.backtest_mean_reversion(symbol1, symbol2, start_date, end_date, z_score_threshold=1.0, trade_size_pct=0.75)

    # Analyze results
    results = backtester.analyze_results(portfolio, symbol1, symbol2)

    print("\n" + "=" * 60)
    print("1-YEAR BACKTESTING RESULTS")
    print("=" * 60)
    print(f"Initial Capital: ${results['initial_capital']:.2f}")
    print(f"Final Value: ${results['final_value']:.2f}")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Buy & Hold Return: {results['buy_hold_return_pct']:.2f}%")
    print(f"Excess Return: {results['excess_return_pct']:.2f}%")
    print(f"Volatility: {results['volatility_pct']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.1f}%")

    # Annualized metrics
    if actual_days > 0:
        annualized_return = results["total_return_pct"] * (365 / actual_days)
        annualized_excess = results["excess_return_pct"] * (365 / actual_days)
        print(f"\nAnnualized Return: {annualized_return:.2f}%")
        print(f"Annualized Excess Return: {annualized_excess:.2f}%")

    # Compare with 30-day results
    print("\n" + "=" * 60)
    print("COMPARISON: 30-DAY vs 1-YEAR")
    print("=" * 60)
    print("30-day results (from tuning):")
    print("  Return: +2.11%, Excess: +14.06%, Sharpe: 0.58")
    print("1-year results:")
    results_str = f"  Return: {results['total_return_pct']:.2f}%, "
    results_str += f"Excess: {results['excess_return_pct']:.2f}%, "
    results_str += f"Sharpe: {results['sharpe_ratio']:.2f}"
    print(results_str)

    return results


if __name__ == "__main__":
    run_1year_backtest()
