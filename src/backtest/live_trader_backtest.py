#!/usr/bin/env python3
"""
Backtest using the actual LivePairTrader algorithm that we fixed.
This ensures our position sizing fixes work correctly in a realistic scenario.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd

# Mock ccxt before importing
sys.modules["ccxt"] = MagicMock()
sys.modules["ccxt.base"] = MagicMock()
sys.modules["ccxt.base.types"] = MagicMock()

from src.analyze.analyzer import CryptoAnalyzer  # noqa: E402
from src.trade.live_pair_trader import LivePairTrader  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveTraderBacktester:
    def __init__(self, initial_capital=1000.0):
        self.initial_capital = initial_capital
        self.analyzer = CryptoAnalyzer()

    def get_historical_prices(self, symbol1, symbol2, start_date, end_date, timeframe="1h"):
        """Get historical price data for both symbols."""
        df1 = self.analyzer.get_data_as_dataframe(symbol1, start_date, end_date, timeframe)
        df2 = self.analyzer.get_data_as_dataframe(symbol2, start_date, end_date, timeframe)

        if df1.empty or df2.empty:
            logger.error(f"No data available for {symbol1} or {symbol2}")
            return pd.DataFrame()

        # Align timestamps
        combined = pd.DataFrame({"timestamp": df1.index, f"{symbol1}_price": df1["close"].values, f"{symbol2}_price": df2["close"].values})
        combined.set_index("timestamp", inplace=True)
        combined.dropna(inplace=True)

        return combined

    def run_backtest(self, symbol1="ADA/USDT", symbol2="BNB/USDT", start_date=None, end_date=None, z_threshold=2.0, lookback_period=20):
        """Run backtest using the actual LivePairTrader algorithm."""

        if start_date is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        logger.info(f"Running backtest for {symbol1} vs {symbol2}")
        logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
        logger.info(f"Z-threshold: {z_threshold}, Lookback: {lookback_period}")

        # Get historical data
        price_data = self.get_historical_prices(symbol1, symbol2, start_date, end_date)
        if price_data.empty:
            return None

        # Initialize the trader (with mocked exchange)
        trader = LivePairTrader(
            symbol1=symbol1,
            symbol2=symbol2,
            initial_capital=self.initial_capital,
            z_threshold=z_threshold,
            lookback_period=lookback_period,
            paper_trading=True,
        )

        # Track results
        results = {"timestamps": [], "portfolio_values": [], "signals": [], "z_scores": [], "trades": [], "positions": [], "prices": []}

        # Simulate the trading process
        for timestamp, row in price_data.iterrows():
            prices = {symbol1: row[f"{symbol1}_price"], symbol2: row[f"{symbol2}_price"]}

            # Update price history (simulate the live trading loop)
            for symbol in [symbol1, symbol2]:
                trader.price_history[symbol].append(prices[symbol])
                if len(trader.price_history[symbol]) > 100:
                    trader.price_history[symbol] = trader.price_history[symbol][-100:]

            # Calculate spread and z-score
            current_spread = trader.calculate_spread(prices)
            z_score = trader.calculate_z_score(current_spread)

            # Generate signal
            signal = trader.generate_signal(z_score)

            # Execute trade if signal changes
            if signal != trader.current_position and signal != 0:
                trade_executed = trader.execute_paper_trade(signal, prices)
                if trade_executed:
                    results["trades"].append({
                        "timestamp": timestamp,
                        "signal": signal,
                        "z_score": z_score,
                        "prices": prices.copy(),
                        "portfolio_value": trader.calculate_portfolio_value(prices),
                    })

            # Update performance
            current_value = trader.calculate_portfolio_value(prices)
            trader.update_performance(current_value)

            # Record results
            results["timestamps"].append(timestamp)
            results["portfolio_values"].append(current_value)
            results["signals"].append(trader.current_position)
            results["z_scores"].append(z_score)
            results["positions"].append(trader.portfolio["positions"].copy())
            results["prices"].append(prices.copy())

        return results, trader

    def analyze_results(self, results, trader, symbol1, symbol2):
        """Analyze backtest results."""
        if not results or not results["portfolio_values"]:
            return {}

        portfolio_values = results["portfolio_values"]
        prices = results["prices"]

        # Calculate returns
        initial_value = self.initial_capital
        final_value = portfolio_values[-1]
        total_return = ((final_value - initial_value) / initial_value) * 100

        # Calculate buy-and-hold return
        initial_price1 = prices[0][symbol1]
        final_price1 = prices[-1][symbol1]
        initial_price2 = prices[0][symbol2]
        final_price2 = prices[-1][symbol2]

        # Equal weight buy and hold
        symbol1_return = ((final_price1 - initial_price1) / initial_price1) * 100
        symbol2_return = ((final_price2 - initial_price2) / initial_price2) * 100
        buy_hold_return = (symbol1_return + symbol2_return) / 2

        # Calculate portfolio statistics
        returns = pd.Series(portfolio_values).pct_change().dropna()
        volatility = returns.std() * (24**0.5) * 100 if len(returns) > 1 else 0  # Annualized for hourly data
        sharpe_ratio = (total_return / volatility) if volatility > 0 else 0

        # Calculate max drawdown
        portfolio_series = pd.Series(portfolio_values)
        rolling_max = portfolio_series.expanding().max()
        drawdown = (portfolio_series - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()

        analysis = {
            "initial_capital": initial_value,
            "final_value": final_value,
            "total_return_pct": total_return,
            "buy_hold_return_pct": buy_hold_return,
            "excess_return_pct": total_return - buy_hold_return,
            "volatility_pct": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown_pct": max_drawdown,
            "total_trades": len(results["trades"]),
            "total_periods": len(portfolio_values),
            "final_positions": trader.portfolio["positions"],
            "performance_metrics": trader.performance,
        }

        return analysis


def main():
    """Run the live trader backtest."""
    parser = argparse.ArgumentParser(description="Backtest the fixed LivePairTrader algorithm")
    parser.add_argument("--symbol1", default="ADA/USDT", help="First trading pair")
    parser.add_argument("--symbol2", default="BNB/USDT", help="Second trading pair")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backtest")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital")
    parser.add_argument("--z-threshold", type=float, default=2.0, help="Z-score threshold")
    parser.add_argument("--lookback", type=int, default=20, help="Lookback period")

    args = parser.parse_args()

    backtester = LiveTraderBacktester(initial_capital=args.capital)

    # Set up parameters
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

    # Run backtest
    results, trader = backtester.run_backtest(
        symbol1=args.symbol1,
        symbol2=args.symbol2,
        start_date=start_date,
        end_date=end_date,
        z_threshold=args.z_threshold,
        lookback_period=args.lookback,
    )

    if results is None:
        logger.error("Backtest failed - no data available")
        return

    # Analyze results
    analysis = backtester.analyze_results(results, trader, args.symbol1, args.symbol2)

    # Print results
    print("\n" + "=" * 60)
    print("LIVE TRADER BACKTEST RESULTS")
    print("=" * 60)
    print(f"Strategy: {args.symbol1} vs {args.symbol2} Pair Trading")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Parameters: Z-threshold={args.z_threshold}, Lookback={args.lookback}")
    print(f"Initial Capital: ${analysis['initial_capital']:,.2f}")
    print(f"Final Value: ${analysis['final_value']:,.2f}")
    print(f"Total Return: {analysis['total_return_pct']:+.2f}%")
    print(f"Buy & Hold Return: {analysis['buy_hold_return_pct']:+.2f}%")
    print(f"Excess Return: {analysis['excess_return_pct']:+.2f}%")
    print(f"Volatility: {analysis['volatility_pct']:.2f}%")
    print(f"Sharpe Ratio: {analysis['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {analysis['max_drawdown_pct']:.2f}%")
    print(f"Total Trades: {analysis['total_trades']}")
    print(f"Total Periods: {analysis['total_periods']}")
    print(f"Final Positions: {analysis['final_positions']}")
    print("=" * 60)

    # Verify our fixes worked
    print("\n🔍 ALGORITHM HEALTH CHECK:")
    final_pos1 = abs(analysis["final_positions"][args.symbol1])
    final_pos2 = abs(analysis["final_positions"][args.symbol2])

    print(f"   Final positions: {final_pos1:.2f} {args.symbol1.split('/')[0]}, {final_pos2:.2f} {args.symbol2.split('/')[0]}")

    # Check if positions are substantial (not microscopic like the original bug)
    if final_pos1 > 0.01 and final_pos2 > 0.01:  # Any meaningful position
        print("✅ Position sizes remain substantial - fix successful!")
        print("   No microscopic position erosion detected!")
    else:
        print("❌ Positions too small - potential bug detected")

    if analysis["total_trades"] > 0:
        print("✅ Trading algorithm executed trades successfully")
        print(f"   Executed {analysis['total_trades']} trades over {analysis['total_periods']} periods")
    else:
        print("❌ No trades executed - check z-score threshold")


if __name__ == "__main__":
    main()
