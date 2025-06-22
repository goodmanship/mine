import asyncio
import json
import logging
import os
from datetime import datetime

import ccxt
import numpy as np

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("pair_trading.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class LivePairTrader:
    def __init__(
        self,
        symbol1: str = "ADA/USDT",
        symbol2: str = "BNB/USDT",
        initial_capital: float = 1000.0,
        lookback_period: int = 20,
        z_threshold: float = 2.0,
        paper_trading: bool = True,
    ):
        """
        Live pair trading system for crypto assets.

        Args:
            symbol1: First trading pair (e.g., 'ADA/USDT')
            symbol2: Second trading pair (e.g., 'BNB/USDT')
            initial_capital: Starting capital in USDT
            lookback_period: Period for calculating z-score
            z_threshold: Z-score threshold for trading signals
            paper_trading: If True, only paper trades (no real execution)
        """
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.initial_capital = initial_capital
        self.lookback_period = lookback_period
        self.z_threshold = z_threshold
        self.paper_trading = paper_trading

        # Initialize exchange (Binance US)
        self.exchange = ccxt.binanceus(  # type: ignore
            {
                "apiKey": os.getenv("BINANCE_API_KEY"),
                "secret": os.getenv("BINANCE_SECRET"),
                "sandbox": paper_trading,  # Use sandbox for paper trading
                "enableRateLimit": True,
            }
        )

        # Portfolio state
        self.portfolio = {
            "cash": initial_capital,
            "positions": {symbol1: 0.0, symbol2: 0.0},
            "total_value": initial_capital,
            "trades": [],
            "pnl": 0.0,
        }

        # Trading state
        self.current_position = 0  # -1: short spread, 0: neutral, 1: long spread
        self.price_history = {symbol1: [], symbol2: []}
        self.trade_count = 0
        self.start_time = datetime.now()

        # Performance tracking
        self.performance = {"total_return": 0.0, "sharpe_ratio": 0.0, "max_drawdown": 0.0, "win_rate": 0.0, "total_trades": 0}

        logger.info(f"Initialized LivePairTrader: {symbol1} vs {symbol2}")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"Paper Trading: {paper_trading}")

    def get_current_prices(self) -> dict[str, float]:
        """Get current prices for both symbols."""
        try:
            ticker1 = self.exchange.fetch_ticker(self.symbol1)
            ticker2 = self.exchange.fetch_ticker(self.symbol2)

            prices = {self.symbol1: ticker1["last"], self.symbol2: ticker2["last"]}

            logger.debug(f"Current prices: {prices}")
            return prices

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return {}

    def calculate_spread(self, prices: dict[str, float]) -> float:
        """Calculate the spread between the two assets."""
        if not prices or len(prices) < 2:
            return 0.0

        # Use log returns for better statistical properties
        log_price1 = np.log(prices[self.symbol1])
        log_price2 = np.log(prices[self.symbol2])

        # Calculate spread as difference in log prices
        spread = log_price1 - log_price2
        return float(spread)

    def calculate_z_score(self, current_spread: float) -> float:
        """Calculate z-score of current spread based on historical data."""
        if len(self.price_history[self.symbol1]) < self.lookback_period:
            return 0.0

        # Calculate historical spreads
        spreads = []
        for i in range(len(self.price_history[self.symbol1])):
            if i < len(self.price_history[self.symbol2]):
                log_price1 = np.log(self.price_history[self.symbol1][i])
                log_price2 = np.log(self.price_history[self.symbol2][i])
                spreads.append(log_price1 - log_price2)

        if len(spreads) < self.lookback_period:
            return 0.0

        # Use recent spreads for z-score calculation
        recent_spreads = spreads[-self.lookback_period :]
        mean_spread = np.mean(recent_spreads)
        std_spread = np.std(recent_spreads)

        if std_spread == 0:
            return 0.0

        z_score = (current_spread - mean_spread) / std_spread
        return float(z_score)

    def generate_signal(self, z_score: float) -> int:
        """Generate trading signal based on z-score."""
        if z_score > self.z_threshold:
            return -1  # Short the spread (sell symbol1, buy symbol2)
        elif z_score < -self.z_threshold:
            return 1  # Long the spread (buy symbol1, sell symbol2)
        else:
            return 0  # No signal

    def calculate_position_sizes(self, prices: dict[str, float]) -> dict[str, float]:
        """Calculate position sizes for both assets."""
        if not prices:
            return {self.symbol1: 0.0, self.symbol2: 0.0}

        # Allocate capital equally between the two assets
        capital_per_asset = self.portfolio["cash"] / 2

        position_sizes = {}
        for symbol in [self.symbol1, self.symbol2]:
            if prices[symbol] > 0:
                position_sizes[symbol] = capital_per_asset / prices[symbol]
            else:
                position_sizes[symbol] = 0.0

        return position_sizes

    def execute_paper_trade(self, signal: int, prices: dict[str, float]) -> bool:
        """Execute a paper trade based on the signal."""
        if signal == 0:
            return False

        try:
            # Close existing positions first
            if self.current_position != 0:
                self.close_positions(prices)

            # Calculate new position sizes
            position_sizes = self.calculate_position_sizes(prices)

            if signal == 1:  # Long spread
                # Buy symbol1, sell symbol2
                self.portfolio["positions"][self.symbol1] = position_sizes[self.symbol1]
                self.portfolio["positions"][self.symbol2] = -position_sizes[self.symbol2]
                self.portfolio["cash"] = 0.0
                self.current_position = 1

                logger.info(f"PAPER TRADE: Long spread - Buy {self.symbol1}, Sell {self.symbol2}")

            elif signal == -1:  # Short spread
                # Sell symbol1, buy symbol2
                self.portfolio["positions"][self.symbol1] = -position_sizes[self.symbol1]
                self.portfolio["positions"][self.symbol2] = position_sizes[self.symbol2]
                self.portfolio["cash"] = 0.0
                self.current_position = -1

                logger.info(f"PAPER TRADE: Short spread - Sell {self.symbol1}, Buy {self.symbol2}")

            # Record trade
            trade = {
                "timestamp": datetime.now(),
                "signal": signal,
                "prices": prices.copy(),
                "positions": self.portfolio["positions"].copy(),
                "portfolio_value": self.calculate_portfolio_value(prices),
            }
            self.portfolio["trades"].append(trade)
            self.trade_count += 1

            return True

        except Exception as e:
            logger.error(f"Error executing paper trade: {e}")
            return False

    def close_positions(self, prices: dict[str, float]):
        """Close all positions and convert to cash."""
        if not prices:
            return

        # Calculate cash from positions
        cash_from_positions = 0.0
        for symbol, position in self.portfolio["positions"].items():
            if symbol in prices and prices[symbol] > 0:
                cash_from_positions += position * prices[symbol]

        # Reset positions
        self.portfolio["positions"] = {self.symbol1: 0.0, self.symbol2: 0.0}
        self.portfolio["cash"] = cash_from_positions
        self.current_position = 0

        logger.info(f"Closed all positions. Cash: ${cash_from_positions:,.2f}")

    def calculate_portfolio_value(self, prices: dict[str, float]) -> float:
        """Calculate total portfolio value."""
        if not prices:
            return self.portfolio["cash"]

        total_value = self.portfolio["cash"]
        for symbol, position in self.portfolio["positions"].items():
            if symbol in prices:
                total_value += position * prices[symbol]

        return total_value

    def update_performance(self, current_value: float):
        """Update performance metrics."""
        self.portfolio["total_value"] = current_value
        self.portfolio["pnl"] = current_value - self.initial_capital

        # Calculate total return
        self.performance["total_return"] = (current_value / self.initial_capital - 1) * 100

        # Update trade count
        self.performance["total_trades"] = self.trade_count

        # Calculate win rate (simplified - can be enhanced)
        if self.trade_count > 0:
            winning_trades = sum(1 for trade in self.portfolio["trades"] if trade.get("pnl", 0) > 0)
            self.performance["win_rate"] = (winning_trades / self.trade_count) * 100

    def print_status(self, prices: dict[str, float], z_score: float, signal: int):
        """Print current trading status."""
        current_value = self.calculate_portfolio_value(prices)

        print("\n" + "=" * 60)
        print(f"LIVE PAIR TRADING STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print(f"Symbols: {self.symbol1} vs {self.symbol2}")
        print(f"Current Prices: {self.symbol1}: ${prices.get(self.symbol1, 0):.4f}, {self.symbol2}: ${prices.get(self.symbol2, 0):.4f}")
        print(f"Z-Score: {z_score:.3f}")
        print(f"Signal: {signal} ({'Long' if signal == 1 else 'Short' if signal == -1 else 'Neutral'})")
        print(f"Current Position: {self.current_position}")
        print(f"Portfolio Value: ${current_value:,.2f}")
        print(f"P&L: ${self.portfolio['pnl']:+,.2f} ({self.performance['total_return']:+.2f}%)")
        print(f"Total Trades: {self.trade_count}")
        print(f"Cash: ${self.portfolio['cash']:,.2f}")
        print(f"Positions: {self.portfolio['positions']}")
        print("=" * 60)

    async def run_trading_loop(self, update_interval: int = 60):
        """Main trading loop."""
        logger.info("Starting live pair trading loop...")

        while True:
            try:
                # Get current prices
                prices = self.get_current_prices()
                if not prices:
                    logger.warning("Could not fetch prices, retrying...")
                    await asyncio.sleep(update_interval)
                    continue

                # Update price history
                for symbol in [self.symbol1, self.symbol2]:
                    if symbol in prices:
                        self.price_history[symbol].append(prices[symbol])
                        # Keep only recent history
                        if len(self.price_history[symbol]) > 100:
                            self.price_history[symbol] = self.price_history[symbol][-100:]

                # Calculate spread and z-score
                current_spread = self.calculate_spread(prices)
                z_score = self.calculate_z_score(current_spread)

                # Generate trading signal
                signal = self.generate_signal(z_score)

                # Execute trade if signal changes
                if signal != self.current_position:
                    self.execute_paper_trade(signal, prices)

                # Update performance
                current_value = self.calculate_portfolio_value(prices)
                self.update_performance(current_value)

                # Print status
                self.print_status(prices, z_score, signal)

                # Save state to file
                self.save_state()

                # Wait for next update
                await asyncio.sleep(update_interval)

            except KeyboardInterrupt:
                logger.info("Trading loop interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(update_interval)

    def save_state(self):
        """Save current state to file."""
        state = {
            "portfolio": self.portfolio,
            "performance": self.performance,
            "current_position": self.current_position,
            "trade_count": self.trade_count,
            "timestamp": datetime.now().isoformat(),
        }

        with open("trading_state.json", "w") as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self):
        """Load state from file."""
        try:
            with open("trading_state.json") as f:
                state = json.load(f)

            self.portfolio = state.get("portfolio", self.portfolio)
            self.performance = state.get("performance", self.performance)
            self.current_position = state.get("current_position", 0)
            self.trade_count = state.get("trade_count", 0)

            logger.info("Loaded previous trading state")
        except FileNotFoundError:
            logger.info("No previous state found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading state: {e}")


def main():
    """Main function to run the live pair trader."""
    # Initialize trader
    trader = LivePairTrader(
        symbol1="ADA/USDT", symbol2="BNB/USDT", initial_capital=1000.0, lookback_period=20, z_threshold=2.0, paper_trading=True
    )

    # Load previous state if exists
    trader.load_state()

    # Run trading loop
    try:
        asyncio.run(trader.run_trading_loop(update_interval=60))  # Update every minute
    except KeyboardInterrupt:
        logger.info("Trading stopped by user")
        trader.save_state()


if __name__ == "__main__":
    main()
