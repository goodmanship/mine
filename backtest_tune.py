import logging
from datetime import datetime, timedelta

import pandas as pd

from backtester import PairTradingBacktester

logger = logging.getLogger(__name__)


def tune_parameters(symbol1, symbol2, days=30):
    """Test different parameters to find optimal settings."""

    # Parameter ranges to test
    z_score_thresholds = [1.0, 1.5, 2.0, 2.5, 3.0]
    trade_sizes = [0.1, 0.25, 0.5, 0.75]

    results = []

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    print(f"Tuning parameters for {symbol1} vs {symbol2}")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Testing {len(z_score_thresholds)} z-score thresholds and {len(trade_sizes)} trade sizes...")
    print()

    for z_threshold in z_score_thresholds:
        for trade_size in trade_sizes:
            backtester = PairTradingBacktester(initial_capital=100)

            portfolio = backtester.backtest_mean_reversion(
                symbol1,
                symbol2,
                start_date,
                end_date,
                z_score_threshold=z_threshold,
                trade_size_pct=trade_size,
            )

            result = backtester.analyze_results(portfolio, symbol1, symbol2)

            if result:
                result.update({"z_score_threshold": z_threshold, "trade_size_pct": trade_size})
                results.append(result)

                print(
                    f"Z={z_threshold}, Size={trade_size}: "
                    f"Return={result['total_return_pct']:.2f}%, "
                    f"Trades={result['total_trades']}, "
                    f"Sharpe={result['sharpe_ratio']:.2f}"
                )

    # Find best parameters
    if results:
        df_results = pd.DataFrame(results)

        # Best by total return
        best_return = df_results.loc[df_results["total_return_pct"].idxmax()]

        # Best by Sharpe ratio
        best_sharpe = df_results.loc[df_results["sharpe_ratio"].idxmax()]

        # Best by excess return
        best_excess = df_results.loc[df_results["excess_return_pct"].idxmax()]

        print("\n" + "=" * 60)
        print("BEST PARAMETERS:")
        print("=" * 60)
        print(f"Best Total Return: Z={best_return['z_score_threshold']}, Size={best_return['trade_size_pct']}")
        print(f"  Return: {best_return['total_return_pct']:.2f}%, Sharpe: {best_return['sharpe_ratio']:.2f}")
        print()
        print(f"Best Sharpe Ratio: Z={best_sharpe['z_score_threshold']}, Size={best_sharpe['trade_size_pct']}")
        print(f"  Return: {best_sharpe['total_return_pct']:.2f}%, Sharpe: {best_sharpe['sharpe_ratio']:.2f}")
        print()
        print(f"Best Excess Return: Z={best_excess['z_score_threshold']}, Size={best_excess['trade_size_pct']}")
        print(f"  Excess: {best_excess['excess_return_pct']:.2f}%, Return: {best_excess['total_return_pct']:.2f}%")

        return df_results

    return pd.DataFrame()


def main():
    """Run parameter tuning for SOL/ADA pair trading."""
    symbol1 = "SOL/USDT"
    symbol2 = "ADA/USDT"

    results_df = tune_parameters(symbol1, symbol2, days=30)

    if not results_df.empty:
        print("\n" + "=" * 60)
        print("ALL RESULTS SUMMARY:")
        print("=" * 60)
        print(
            results_df[
                [
                    "z_score_threshold",
                    "trade_size_pct",
                    "total_return_pct",
                    "excess_return_pct",
                    "sharpe_ratio",
                    "total_trades",
                ]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
