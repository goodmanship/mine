import logging
from datetime import datetime, timedelta

import pandas as pd

from src.analyze.analyzer import CryptoAnalyzer

logger = logging.getLogger(__name__)


class PairTradingBacktester:
    def __init__(self, initial_capital=100):
        self.initial_capital = initial_capital
        self.analyzer = CryptoAnalyzer()

    def get_pair_data(self, symbol1, symbol2, start_date=None, end_date=None, timeframe="1h"):
        """Get price data for both symbols and calculate the ratio."""
        df1 = self.analyzer.get_data_as_dataframe(symbol1, start_date, end_date, timeframe)
        df2 = self.analyzer.get_data_as_dataframe(symbol2, start_date, end_date, timeframe)

        if df1.empty or df2.empty:
            return pd.DataFrame()

        # Align the dataframes by timestamp
        combined = pd.DataFrame({f"{symbol1}_price": df1["close"], f"{symbol2}_price": df2["close"]})

        # Calculate the price ratio (SOL/ADA)
        combined["price_ratio"] = combined[f"{symbol1}_price"] / combined[f"{symbol2}_price"]

        # Calculate rolling statistics for the ratio
        combined["ratio_mean"] = combined["price_ratio"].rolling(window=20).mean()
        combined["ratio_std"] = combined["price_ratio"].rolling(window=20).std()

        # Calculate z-score (how many standard deviations from mean)
        combined["z_score"] = (combined["price_ratio"] - combined["ratio_mean"]) / combined["ratio_std"]

        return combined

    def calculate_position_sizes(self, symbol1_price, symbol2_price, capital=50):
        """Calculate how many units of each asset to buy with given capital."""
        # Simple equal weight allocation
        units_symbol1 = capital / symbol1_price
        units_symbol2 = capital / symbol2_price
        return units_symbol1, units_symbol2

    def backtest_mean_reversion(
        self, symbol1, symbol2, start_date=None, end_date=None, timeframe="1h", z_score_threshold=1.5, trade_size_pct=0.25
    ):
        """Backtest a mean reversion pair trading strategy."""

        # Get the pair data
        df = self.get_pair_data(symbol1, symbol2, start_date, end_date, timeframe)

        if df.empty:
            logger.error("No data available for backtesting")
            return {}

        # Initialize portfolio
        portfolio = {"cash": self.initial_capital, f"{symbol1}_units": 0, f"{symbol2}_units": 0, "trades": [], "portfolio_values": []}

        # Initial position: buy $50 of each
        initial_symbol1_price = df[f"{symbol1}_price"].iloc[0]
        initial_symbol2_price = df[f"{symbol2}_price"].iloc[0]

        symbol1_units, symbol2_units = self.calculate_position_sizes(initial_symbol1_price, initial_symbol2_price, 50)

        portfolio[f"{symbol1}_units"] = symbol1_units
        portfolio[f"{symbol2}_units"] = symbol2_units
        portfolio["cash"] = 0  # All cash invested

        logger.info(f"Initial position: {symbol1_units:.4f} {symbol1}, {symbol2_units:.4f} {symbol2}")

        # Track portfolio value over time
        for i, (timestamp, row) in enumerate(df.iterrows()):
            symbol1_price = row[f"{symbol1}_price"]
            symbol2_price = row[f"{symbol2}_price"]
            z_score = row["z_score"]

            # Calculate current portfolio value
            portfolio_value = (
                portfolio["cash"] + portfolio[f"{symbol1}_units"] * symbol1_price + portfolio[f"{symbol2}_units"] * symbol2_price
            )

            portfolio["portfolio_values"].append({
                "timestamp": timestamp,
                "value": portfolio_value,
                "z_score": z_score,
                f"{symbol1}_price": symbol1_price,
                f"{symbol2}_price": symbol2_price,
            })

            # Skip first 20 periods to let rolling stats stabilize
            if i < 20 or pd.isna(z_score):
                continue

            # Trading logic
            if z_score > z_score_threshold:  # Ratio is high - sell SOL, buy ADA
                trade_amount = portfolio[f"{symbol1}_units"] * trade_size_pct
                if trade_amount > 0:
                    # Sell SOL
                    portfolio[f"{symbol1}_units"] -= trade_amount
                    portfolio["cash"] += trade_amount * symbol1_price

                    # Buy ADA
                    ada_units = (trade_amount * symbol1_price) / symbol2_price
                    portfolio[f"{symbol2}_units"] += ada_units
                    portfolio["cash"] -= ada_units * symbol2_price

                    portfolio["trades"].append({
                        "timestamp": timestamp,
                        "action": "sell_sol_buy_ada",
                        "z_score": z_score,
                        "sol_units": -trade_amount,
                        "ada_units": ada_units,
                        "portfolio_value": portfolio_value,
                    })

            elif z_score < -z_score_threshold:  # Ratio is low - buy SOL, sell ADA
                trade_amount = portfolio[f"{symbol2}_units"] * trade_size_pct
                if trade_amount > 0:
                    # Sell ADA
                    portfolio[f"{symbol2}_units"] -= trade_amount
                    portfolio["cash"] += trade_amount * symbol2_price

                    # Buy SOL
                    sol_units = (trade_amount * symbol2_price) / symbol1_price
                    portfolio[f"{symbol1}_units"] += sol_units
                    portfolio["cash"] -= sol_units * symbol1_price

                    portfolio["trades"].append({
                        "timestamp": timestamp,
                        "action": "buy_sol_sell_ada",
                        "z_score": z_score,
                        "sol_units": sol_units,
                        "ada_units": -trade_amount,
                        "portfolio_value": portfolio_value,
                    })

        return portfolio

    def analyze_results(self, portfolio, symbol1, symbol2):
        """Analyze the backtesting results."""
        if not portfolio["portfolio_values"]:
            return {}

        df_values = pd.DataFrame(portfolio["portfolio_values"])
        df_trades = pd.DataFrame(portfolio["trades"])

        # Calculate returns
        initial_value = self.initial_capital
        final_value = df_values["value"].iloc[-1]
        total_return = ((final_value - initial_value) / initial_value) * 100

        # Calculate buy-and-hold return for comparison
        initial_sol_price = df_values[f"{symbol1}_price"].iloc[0]
        final_sol_price = df_values[f"{symbol1}_price"].iloc[-1]
        initial_ada_price = df_values[f"{symbol2}_price"].iloc[0]
        final_ada_price = df_values[f"{symbol2}_price"].iloc[-1]

        sol_return = ((final_sol_price - initial_sol_price) / initial_sol_price) * 100
        ada_return = ((final_ada_price - initial_ada_price) / initial_ada_price) * 100
        buy_hold_return = (sol_return + ada_return) / 2  # Equal weight

        # Calculate volatility
        daily_returns = df_values["value"].pct_change().dropna()
        volatility = daily_returns.std() * (24**0.5) * 100  # Annualized

        # Calculate Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = (total_return / volatility) if volatility > 0 else 0

        results = {
            "initial_capital": initial_value,
            "final_value": final_value,
            "total_return_pct": total_return,
            "buy_hold_return_pct": buy_hold_return,
            "excess_return_pct": total_return - buy_hold_return,
            "volatility_pct": volatility,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": len(portfolio["trades"]),
            "max_drawdown_pct": self.calculate_max_drawdown(df_values["value"]),
            "win_rate_pct": self.calculate_win_rate(df_trades) if len(df_trades) > 0 else 0,
        }

        return results

    def calculate_max_drawdown(self, values):
        """Calculate maximum drawdown percentage."""
        peak = values.expanding().max()
        drawdown = (values - peak) / peak * 100
        return drawdown.min()

    def calculate_win_rate(self, trades_df):
        """Calculate percentage of profitable trades."""
        if trades_df.empty:
            return 0

        # Calculate trade returns (simplified)
        profitable_trades = 0
        for i in range(1, len(trades_df)):
            prev_value = trades_df["portfolio_value"].iloc[i - 1]
            curr_value = trades_df["portfolio_value"].iloc[i]
            if curr_value > prev_value:
                profitable_trades += 1

        return (profitable_trades / (len(trades_df) - 1)) * 100 if len(trades_df) > 1 else 0


def main():
    """Example usage of the pair trading backtester."""
    backtester = PairTradingBacktester(initial_capital=100)

    # Test SOL/ADA pair trading
    symbol1 = "SOL/USDT"
    symbol2 = "ADA/USDT"

    # Get data for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    print(f"Backtesting {symbol1} vs {symbol2} pair trading strategy...")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Run backtest
    portfolio = backtester.backtest_mean_reversion(symbol1, symbol2, start_date, end_date, z_score_threshold=1.5, trade_size_pct=0.25)

    # Analyze results
    results = backtester.analyze_results(portfolio, symbol1, symbol2)

    print("\n=== BACKTESTING RESULTS ===")
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


if __name__ == "__main__":
    main()
