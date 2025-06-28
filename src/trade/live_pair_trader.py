import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime

import ccxt
import numpy as np
from ccxt.base.types import ConstructorArgs

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("pair_trading.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class LiveChartDisplay:
    """Real-time chart display for trading algorithm."""

    def __init__(self, symbol1: str, symbol2: str, z_threshold: float, max_points: int = 100):
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.z_threshold = z_threshold
        self.max_points = max_points

        # Data storage
        self.timestamps = deque(maxlen=max_points)
        self.z_scores = deque(maxlen=max_points)
        self.z_timestamps = deque(maxlen=max_points)  # Separate timestamps for z-scores
        self.positions = deque(maxlen=max_points)
        self.prices_symbol1 = deque(maxlen=max_points)  # Raw prices for calculations
        self.prices_symbol2 = deque(maxlen=max_points)  # Raw prices for calculations
        self.normalized_prices_symbol1 = deque(maxlen=max_points)  # Normalized for display
        self.normalized_prices_symbol2 = deque(maxlen=max_points)  # Normalized for display
        self.trades = []  # Store trade events

        # Baseline prices for normalization (set when first data point is added)
        self.baseline_price1 = None
        self.baseline_price2 = None

        # Chart components (single subplot now)
        self.fig = None
        self.ax = None
        self.line_zscore = None
        self.line_threshold_upper = None
        self.line_threshold_lower = None
        self.line_price1_norm = None
        self.line_price2_norm = None
        self.trade_markers = None

        # Try to import matplotlib
        try:
            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt
            from matplotlib.animation import FuncAnimation

            self.plt = plt
            self.mdates = mdates
            self.FuncAnimation = FuncAnimation
            self.available = True

            # Set up the chart
            self._setup_chart()

        except ImportError:
            logger.warning("Matplotlib not available. Live chart disabled.")
            logger.info("Install matplotlib to enable live charting: pip install matplotlib")
            self.available = False

    def _setup_chart(self):
        """Initialize the matplotlib chart with dark wombat theme."""
        if not self.available:
            return

        # Set dark theme style
        self.plt.style.use("dark_background")

        # Create figure with single subplot
        self.fig, self.ax = self.plt.subplots(1, 1, figsize=(14, 8))

        # Dark wombat color scheme
        bg_color = "#2c2e34"  # Dark gray background
        grid_color = "#3e4044"  # Slightly lighter gray for grid
        text_color = "#d4b87c"  # Warm beige for text

        # Set figure and axis background colors
        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)

        # Title with wombat styling
        self.fig.suptitle(f"Live Pair Trading: {self.symbol1} vs {self.symbol2}", fontsize=16, fontweight="bold", color=text_color)

        # Set up the main chart with enhanced styling
        self.ax.set_title("Z-Score & Cumulative Price Changes (from start)", fontsize=12, color=text_color, pad=15)
        self.ax.set_xlabel("Time", color=text_color, fontsize=11)
        self.ax.set_ylabel("Z-Score / Percentage Change (%)", color=text_color, fontsize=11)

        # Enhanced grid styling
        self.ax.grid(True, alpha=0.2, color=grid_color, linewidth=0.8)
        self.ax.set_axisbelow(True)  # Grid behind plot elements

        # Wombat color palette for lines
        z_score_color = "#8ac6f2"  # Cool blue for z-score
        threshold_color = "#e5786d"  # Warm red for thresholds
        symbol1_color = "#95e454"  # Bright green for first symbol
        symbol2_color = "#cae682"  # Lighter green for second symbol

        # Initialize z-score lines with enhanced styling
        (self.line_zscore,) = self.ax.plot([], [], color=z_score_color, linewidth=2.5, label="Z-Score", alpha=0.9)
        (self.line_threshold_upper,) = self.ax.plot(
            [], [], color=threshold_color, linestyle="--", linewidth=1.5, alpha=0.8, label=f"Threshold (+{self.z_threshold})"
        )
        (self.line_threshold_lower,) = self.ax.plot(
            [], [], color=threshold_color, linestyle="--", linewidth=1.5, alpha=0.8, label=f"Threshold (-{self.z_threshold})"
        )

        # Initialize cumulative percentage change lines with enhanced styling
        symbol1_name = self.symbol1.split("/")[0]
        symbol2_name = self.symbol2.split("/")[0]
        (self.line_price1_norm,) = self.ax.plot([], [], color=symbol1_color, linewidth=2.2, alpha=0.9, label=f"{symbol1_name} % Change")
        (self.line_price2_norm,) = self.ax.plot([], [], color=symbol2_color, linewidth=2.2, alpha=0.9, label=f"{symbol2_name} % Change")

        # Enhanced legend with dark theme styling
        legend = self.ax.legend(
            loc="upper right",
            frameon=True,
            fancybox=True,
            shadow=True,
            facecolor="#1a1c20",  # Dark legend background
            edgecolor=grid_color,
            fontsize=10,
        )
        legend.get_frame().set_alpha(0.9)

        # Style legend text
        for text in legend.get_texts():
            text.set_color(text_color)

        # Format x-axis for time with dark theme
        self.ax.xaxis.set_major_formatter(self.mdates.DateFormatter("%H:%M"))
        self.ax.xaxis.set_major_locator(self.mdates.MinuteLocator(interval=5))

        # Style axis ticks and labels
        self.ax.tick_params(axis="both", colors=text_color, labelsize=9)
        self.ax.spines["bottom"].set_color(grid_color)
        self.ax.spines["top"].set_color(grid_color)
        self.ax.spines["left"].set_color(grid_color)
        self.ax.spines["right"].set_color(grid_color)

        # Set initial y-axis limits to reasonable range
        self.ax.set_ylim(-4, 4)

        # Enable interactive mode
        self.plt.ion()
        self.plt.tight_layout()
        self.plt.show()

    def _normalize_price(self, price: float, baseline: float) -> float:
        """Calculate cumulative percentage change from baseline (time=0)."""
        if baseline is None or baseline == 0:
            return 0.0

        # Calculate percentage change from baseline (first data point)
        pct_change = (price - baseline) / baseline

        # Convert to percentage points for better visual scaling
        # 1% change = 1.0 on chart, 2% change = 2.0, etc.
        return pct_change * 100

    def add_data_point(self, timestamp: datetime, z_score: float, position: int, prices: dict[str, float]):
        """Add a new data point to the chart."""
        if not self.available:
            return

        # Set baseline prices on first data point (this becomes our time=0 reference)
        if self.baseline_price1 is None:
            self.baseline_price1 = prices.get(self.symbol1, 0.0)
            self.baseline_price2 = prices.get(self.symbol2, 0.0)
            logger.debug(f"Chart baseline set: {self.symbol1}=${self.baseline_price1:.4f}, {self.symbol2}=${self.baseline_price2:.4f}")

        # Always store timestamp, position, and price data
        self.timestamps.append(timestamp)
        self.positions.append(position)
        self.prices_symbol1.append(prices.get(self.symbol1, 0.0))
        self.prices_symbol2.append(prices.get(self.symbol2, 0.0))

        # Calculate cumulative percentage changes from baseline (time=0)
        pct_change_1 = self._normalize_price(prices.get(self.symbol1, 0.0), self.baseline_price1)
        pct_change_2 = self._normalize_price(prices.get(self.symbol2, 0.0), self.baseline_price2)

        self.normalized_prices_symbol1.append(pct_change_1)
        self.normalized_prices_symbol2.append(pct_change_2)

        # Only store z-score data when it's meaningful (non-zero)
        if abs(z_score) > 0.001:  # Only meaningful z-scores
            self.z_scores.append(z_score)
            self.z_timestamps.append(timestamp)

    def add_trade_marker(self, timestamp: datetime, z_score: float, signal: int, trade_type: str):
        """Add a trade marker to the chart."""
        if not self.available:
            return

        # Store trade for plotting with wombat theme colors
        if signal == 1:  # Long trade
            color = "#95e454"  # Bright green (matches symbol1 color)
            marker = "^"
        elif signal == -1:  # Short trade
            color = "#e5786d"  # Warm red (matches threshold color)
            marker = "v"
        else:  # Close trade
            color = "#d4b87c"  # Warm beige (matches text color)
            marker = "o"

        self.trades.append({
            "timestamp": timestamp,
            "z_score": z_score,
            "signal": signal,
            "color": color,
            "marker": marker,
            "label": trade_type,
        })

        # Keep only last 20 trades for performance
        if len(self.trades) > 20:
            self.trades = self.trades[-20:]

    def update_chart(self):
        """Update the chart with current data."""
        if not self.available or len(self.timestamps) == 0:
            return

        try:
            # Convert timestamps to matplotlib format
            times = [self.mdates.date2num(ts) for ts in self.timestamps]

            # Update z-score line only if we have meaningful z-score data
            if len(self.z_scores) > 0 and len(self.z_timestamps) > 0:
                z_times = [self.mdates.date2num(ts) for ts in self.z_timestamps]
                self.line_zscore.set_data(z_times, list(self.z_scores))

                # Update threshold lines to span the z-score data range
                if len(z_times) > 0:
                    self.line_threshold_upper.set_data([z_times[0], z_times[-1]], [self.z_threshold, self.z_threshold])
                    self.line_threshold_lower.set_data([z_times[0], z_times[-1]], [-self.z_threshold, -self.z_threshold])
            else:
                # Clear z-score line if no meaningful data
                self.line_zscore.set_data([], [])
                self.line_threshold_upper.set_data([], [])
                self.line_threshold_lower.set_data([], [])

            # Update normalized price lines (always available)
            self.line_price1_norm.set_data(times, list(self.normalized_prices_symbol1))
            self.line_price2_norm.set_data(times, list(self.normalized_prices_symbol2))

            # Clear old trade markers and add new ones
            for artist in self.ax.collections:
                artist.remove()

            # Plot trade markers with enhanced styling for dark theme
            for trade in self.trades:
                trade_time = self.mdates.date2num(trade["timestamp"])
                self.ax.scatter(
                    trade_time,
                    trade["z_score"],
                    c=trade["color"],
                    marker=trade["marker"],
                    s=140,  # Slightly larger markers
                    alpha=0.9,
                    edgecolors="#1a1c20",  # Dark edge color matching legend background
                    linewidth=1.5,
                    zorder=10,  # Higher z-order to appear above lines
                )

            # Adjust axis limits dynamically
            if len(self.z_scores) > 0 or len(self.normalized_prices_symbol1) > 0:
                all_values = list(self.z_scores) + list(self.normalized_prices_symbol1) + list(self.normalized_prices_symbol2)
                all_values = [v for v in all_values if abs(v) > 0.001]  # Remove near-zero values

                if all_values:
                    min_val = min(all_values)
                    max_val = max(all_values)

                    # Ensure we show at least ±2.5 range to accommodate z-score thresholds
                    min_display = min(min_val - 0.5, -2.5)
                    max_display = max(max_val + 0.5, 2.5)

                    # Add extra margin for better visibility
                    range_size = max_display - min_display
                    margin = range_size * 0.1

                    self.ax.set_ylim(min_display - margin, max_display + margin)
                else:
                    # Default range if no meaningful data yet
                    self.ax.set_ylim(-3, 3)

            # Set x-axis limits to show all data
            if len(times) > 0:
                self.ax.set_xlim(times[0], times[-1])

            # Refresh the plot
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()

        except Exception as e:
            logger.debug(f"Chart update error: {e}")

    def close(self):
        """Close the chart window."""
        if self.available and self.fig:
            self.plt.close(self.fig)


class LivePairTrader:
    def __init__(
        self,
        symbol1: str = "ADA/USDT",
        symbol2: str = "BNB/USDT",
        initial_capital: float = 1000.0,
        lookback_period: int = 20,
        z_threshold: float = 2.0,
        paper_trading: bool = True,
        enable_chart: bool = True,
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
            enable_chart: If True, display live chart (requires matplotlib)
        """
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.initial_capital = initial_capital
        self.lookback_period = lookback_period
        self.z_threshold = z_threshold
        self.paper_trading = paper_trading
        self.enable_chart = enable_chart

        # Initialize exchange (Binance US)
        init_dict: ConstructorArgs = {  # type: ignore
            "apiKey": os.getenv("BINANCE_API_KEY", ""),
            "secret": os.getenv("BINANCE_SECRET", ""),
            "sandbox": paper_trading,  # Use sandbox for paper trading
            "enableRateLimit": True,
        }
        self.exchange = ccxt.binanceus(init_dict)

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

        # Initialize live chart
        self.chart: LiveChartDisplay | None = None
        if self.enable_chart:
            self.chart = LiveChartDisplay(symbol1, symbol2, z_threshold)
            if self.chart and self.chart.available:
                logger.info("Live chart enabled - Chart window should appear")
            else:
                logger.info("Live chart disabled - matplotlib not available")
                self.chart = None

        logger.info(f"Initialized LivePairTrader: {symbol1} vs {symbol2}")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"Paper Trading: {paper_trading}")
        logger.info(f"Live Chart: {'Enabled' if self.chart else 'Disabled'}")

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
        # Check if we have enough price history
        history_length = len(self.price_history[self.symbol1])

        if history_length < self.lookback_period:
            logger.debug(f"Insufficient history: {history_length}/{self.lookback_period} data points")
            return 0.0

        # Calculate historical spreads
        spreads = []
        for i in range(len(self.price_history[self.symbol1])):
            if i < len(self.price_history[self.symbol2]):
                log_price1 = np.log(self.price_history[self.symbol1][i])
                log_price2 = np.log(self.price_history[self.symbol2][i])
                spreads.append(log_price1 - log_price2)

        if len(spreads) < self.lookback_period:
            logger.debug(f"Insufficient spreads: {len(spreads)}/{self.lookback_period}")
            return 0.0

        # Use recent spreads for z-score calculation
        recent_spreads = spreads[-self.lookback_period :]
        mean_spread = np.mean(recent_spreads)
        std_spread = np.std(recent_spreads)

        if std_spread == 0:
            logger.warning("Standard deviation is zero - prices may not be varying")
            return 0.0

        z_score = (current_spread - mean_spread) / std_spread
        z_score_str = f"Z-score calculation: mean={mean_spread:.6f}, std={std_spread:.6f}, "
        z_score_str += f"current={current_spread:.6f}, z_score={z_score:.3f}"
        logger.debug(z_score_str)
        return float(z_score)

    def generate_signal(self, z_score: float) -> int:
        """Generate trading signal based on z-score."""
        if z_score > self.z_threshold:
            return -1  # Short the spread (sell symbol1, buy symbol2)
        elif z_score < -self.z_threshold:
            return 1  # Long the spread (buy symbol1, sell symbol2)
        else:
            return 0  # No signal

    def calculate_position_sizes(self, prices: dict[str, float], portfolio_value: float | None = None) -> dict[str, float]:
        """Calculate position sizes for both assets."""
        if not prices:
            return {self.symbol1: 0.0, self.symbol2: 0.0}

        # Use current portfolio value to scale position sizes appropriately
        if portfolio_value is None:
            current_value = self.calculate_portfolio_value(prices)
        else:
            current_value = portfolio_value

        # If portfolio value is too small, stop trading
        if abs(current_value) < 50.0:  # Don't trade with less than $50
            logger.warning(f"Portfolio too small to trade: ${current_value:.2f}")
            return {self.symbol1: 0.0, self.symbol2: 0.0}

        # Use much smaller position sizes like the original backtester
        # Allocate only 10% of portfolio value per trade (vs 80% before)
        usable_capital = abs(current_value) * 0.10  # Much more conservative
        capital_per_asset = usable_capital / 2

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

            # Get current portfolio value after closing positions
            current_portfolio_value = self.calculate_portfolio_value(prices)

            # Calculate new position sizes based on current portfolio value
            position_sizes = self.calculate_position_sizes(prices, current_portfolio_value)

            # If position sizes are zero (portfolio too small), don't trade
            if position_sizes[self.symbol1] == 0.0 and position_sizes[self.symbol2] == 0.0:
                logger.info("Position sizes are zero - stopping trading")
                return False

            # Calculate the dollar amounts for each position
            cost_symbol1 = position_sizes[self.symbol1] * prices[self.symbol1]
            cost_symbol2 = position_sizes[self.symbol2] * prices[self.symbol2]

            trade_type = ""

            if signal == 1:  # Long spread
                # Buy symbol1 (costs money), sell symbol2 (provides money)
                net_cash_change = -cost_symbol1 + cost_symbol2  # Negative cost + positive income

                self.portfolio["positions"][self.symbol1] = position_sizes[self.symbol1]
                self.portfolio["positions"][self.symbol2] = -position_sizes[self.symbol2]
                self.portfolio["cash"] += net_cash_change
                self.current_position = 1
                trade_type = "Long Spread"

                long_spread_log = f"📈 TRADE: Long spread - Buy {self.symbol1.split('/')[0]}, "
                long_spread_log += f"Sell {self.symbol2.split('/')[0]} | Cash: ${net_cash_change:+.2f}"
                print(long_spread_log)

            elif signal == -1:  # Short spread
                # Sell symbol1 (provides money), buy symbol2 (costs money)
                net_cash_change = cost_symbol1 - cost_symbol2  # Positive income - negative cost

                self.portfolio["positions"][self.symbol1] = -position_sizes[self.symbol1]
                self.portfolio["positions"][self.symbol2] = position_sizes[self.symbol2]
                self.portfolio["cash"] += net_cash_change
                self.current_position = -1
                trade_type = "Short Spread"

                short_spread_log = f"📉 TRADE: Short spread - Sell {self.symbol1.split('/')[0]}, "
                short_spread_log += f"Buy {self.symbol2.split('/')[0]} | Cash: ${net_cash_change:+.2f}"
                print(short_spread_log)

            # Record trade
            timestamp = datetime.now()
            trade = {
                "timestamp": timestamp,
                "signal": signal,
                "prices": prices.copy(),
                "positions": self.portfolio["positions"].copy(),
                "portfolio_value": self.calculate_portfolio_value(prices),
                "cash_change": net_cash_change,
            }
            self.portfolio["trades"].append(trade)
            self.trade_count += 1

            # Add trade marker to chart
            if self.chart:
                # Calculate current z-score for the marker
                current_spread = self.calculate_spread(prices)
                z_score = self.calculate_z_score(current_spread)
                self.chart.add_trade_marker(timestamp, z_score, signal, trade_type)

            return True

        except Exception as e:
            logger.error(f"Error executing paper trade: {e}")
            return False

    def close_positions(self, prices: dict[str, float]):
        """Close all positions and convert to cash."""
        if not prices:
            return

        # Calculate cash from closing positions
        cash_from_positions = 0.0
        for symbol, position in self.portfolio["positions"].items():
            if symbol in prices and prices[symbol] > 0:
                cash_from_positions += position * prices[symbol]

        # Add cash from positions to existing cash (don't replace it!)
        self.portfolio["cash"] += cash_from_positions

        # Reset positions
        self.portfolio["positions"] = {self.symbol1: 0.0, self.symbol2: 0.0}
        self.current_position = 0

        print(f"🔄 CLOSE: All positions closed | Cash recovered: ${cash_from_positions:+.2f}")

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
        """Print current trading status in a sleek, dynamic format."""
        current_value = self.calculate_portfolio_value(prices)

        # ANSI escape codes for colors and formatting
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        CYAN = "\033[96m"
        WHITE = "\033[97m"
        BOLD = "\033[1m"
        RESET = "\033[0m"
        CLEAR_LINE = "\033[2K"
        MOVE_UP = "\033[F"

        # Determine colors based on values
        pnl_color = GREEN if self.portfolio["pnl"] >= 0 else RED
        signal_color = GREEN if signal == 1 else RED if signal == -1 else YELLOW

        # Signal emoji and text
        signal_emoji = "🟢" if signal == 1 else "🔴" if signal == -1 else "⚪"
        signal_text = "LONG" if signal == 1 else "SHORT" if signal == -1 else "NEUTRAL"

        # Position emoji
        pos_emoji = "📈" if self.current_position == 1 else "📉" if self.current_position == -1 else "💤"

        # Clear previous lines (move up and clear if not first run)
        if hasattr(self, "_status_printed"):
            print(f"{MOVE_UP}{CLEAR_LINE}" * 4, end="")  # Clear 4 lines now

        # Print compact status in 4 lines
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Line 1: Prices and Z-Score
        print(
            f"{CYAN}[{timestamp}]{RESET} 💰 {BOLD}{self.symbol1.split('/')[0]}{RESET}: ${prices.get(self.symbol1, 0):.4f} | "
            f"{BOLD}{self.symbol2.split('/')[0]}{RESET}: ${prices.get(self.symbol2, 0):.4f} | "
            f"📊 Z-Score: {BLUE}{z_score:+.3f}{RESET}"
        )

        # Line 2: Z-Score status and data collection
        history_length = len(self.price_history[self.symbol1])
        if history_length >= self.lookback_period:
            # Z-score is active
            if abs(z_score) > self.z_threshold:
                threshold_status = f"{RED}⚠️  BEYOND THRESHOLD ±{self.z_threshold}{RESET}"
            else:
                threshold_status = f"{GREEN}✅ Within threshold ±{self.z_threshold}{RESET}"
            print(f"📊 Z-Score: {threshold_status} | 📈 History: {history_length} data points | 🎯 ACTIVE")
        else:
            # Still collecting data
            progress = (history_length / self.lookback_period) * 100
            remaining_time = (self.lookback_period - history_length) * 1  # 1 minute per data point
            print(
                f"📊 Collecting data: {history_length}/{self.lookback_period} points "
                f"({progress:.1f}%) | ⏱️  Est. {remaining_time} min until z-score active"
            )

        # Line 3: Signal, Position, and Portfolio
        print(
            f"{signal_emoji} Signal: {signal_color}{BOLD}{signal_text}{RESET} | "
            f"{pos_emoji} Position: {self.current_position} | "
            f"💼 Portfolio: {WHITE}${current_value:,.2f}{RESET} | "
            f"P&L: {pnl_color}{BOLD}{self.portfolio['pnl']:+.2f}{RESET} "
            f"({pnl_color}{self.performance['total_return']:+.2f}%{RESET})"
        )

        # Line 4: Trading Stats
        cash_pct = (self.portfolio["cash"] / current_value * 100) if current_value > 0 else 0
        ada_pos = self.portfolio["positions"].get(self.symbol1, 0)
        bnb_pos = self.portfolio["positions"].get(self.symbol2, 0)

        print(
            f"💵 Cash: ${self.portfolio['cash']:,.2f} ({cash_pct:.1f}%) | "
            f"🪙 {self.symbol1.split('/')[0]}: {ada_pos:+.2f} | "
            f"🟡 {self.symbol2.split('/')[0]}: {bnb_pos:+.2f} | "
            f"📋 Trades: {self.trade_count}"
        )

        # Mark that we've printed status (for clearing next time)
        self._status_printed = True

    async def bootstrap_price_history(self):
        """Bootstrap price history with recent data to enable immediate z-score calculation."""
        try:
            logger.info("🔄 Warming up z-score calculation with recent market data...")
            print("🔄 Fetching recent price data to warm up z-score calculation...")

            # Fetch more data than we need to ensure we have enough
            # Get 30 minutes of data to be safe (we need 20)
            fetch_limit = self.lookback_period + 15  # Extra buffer

            bootstrap_success = True
            historical_data = {}  # Store OHLCV data with timestamps

            for symbol in [self.symbol1, self.symbol2]:
                try:
                    # Fetch recent OHLCV data (1m timeframe)
                    print(f"   📊 Fetching {fetch_limit} minutes of data for {symbol}...")
                    ohlcv = self.exchange.fetch_ohlcv(symbol, "1m", limit=fetch_limit)

                    if len(ohlcv) < self.lookback_period:
                        logger.warning(f"Insufficient historical data for {symbol}: got {len(ohlcv)}, need {self.lookback_period}")
                        print(f"   ⚠️  Warning: Only {len(ohlcv)} data points available for {symbol}")
                        bootstrap_success = False
                        continue

                    # Store full OHLCV data for chart population
                    historical_data[symbol] = ohlcv[:-1]  # Exclude last incomplete candle

                    # Extract closing prices for z-score calculation
                    closing_prices = [float(candle[4]) for candle in ohlcv[:-1]]

                    # Clear existing history and add bootstrap data
                    self.price_history[symbol] = closing_prices

                    print(f"   ✅ Loaded {len(closing_prices)} price points for {symbol}")
                    logger.debug(f"Price range for {symbol}: ${min(closing_prices):.4f} - ${max(closing_prices):.4f}")

                except Exception as e:
                    logger.error(f"Failed to fetch historical data for {symbol}: {e}")
                    print(f"   ❌ Error fetching data for {symbol}: {e}")
                    bootstrap_success = False

            # Verify we have enough data for both symbols
            symbol1_count = len(self.price_history[self.symbol1])
            symbol2_count = len(self.price_history[self.symbol2])
            min_count = min(symbol1_count, symbol2_count)

            if min_count >= self.lookback_period and bootstrap_success:
                # Populate chart with historical data
                if self.chart and len(historical_data) == 2:
                    print(f"   📈 Populating chart with {min_count} historical data points...")

                    # Get the minimum number of data points to ensure both symbols align
                    chart_data_count = min(len(historical_data[self.symbol1]), len(historical_data[self.symbol2]))

                    for i in range(chart_data_count):
                        # Get timestamp from OHLCV data (index 0)
                        timestamp_ms = historical_data[self.symbol1][i][0]
                        timestamp = datetime.fromtimestamp(timestamp_ms / 1000)

                        # Get prices for this point
                        prices = {
                            self.symbol1: float(historical_data[self.symbol1][i][4]),  # closing price
                            self.symbol2: float(historical_data[self.symbol2][i][4]),  # closing price
                        }

                        # Calculate z-score if we have enough history
                        z_score = 0.0
                        if i >= self.lookback_period - 1:  # Need lookback_period points for z-score
                            # Use price history up to this point
                            temp_history_1 = []
                            temp_history_2 = []
                            for j in range(max(0, i - self.lookback_period + 1), i + 1):
                                temp_history_1.append(float(historical_data[self.symbol1][j][4]))
                                temp_history_2.append(float(historical_data[self.symbol2][j][4]))

                            if len(temp_history_1) >= self.lookback_period and len(temp_history_2) >= self.lookback_period:
                                # Calculate spread for this point
                                current_spread = np.log(prices[self.symbol1]) - np.log(prices[self.symbol2])

                                # Calculate z-score using the recent history
                                spreads = []
                                for k in range(len(temp_history_1)):
                                    if k < len(temp_history_2):
                                        spread = np.log(temp_history_1[k]) - np.log(temp_history_2[k])
                                        spreads.append(spread)

                                if len(spreads) >= self.lookback_period:
                                    recent_spreads = spreads[-self.lookback_period :]
                                    mean_spread = np.mean(recent_spreads)
                                    std_spread = np.std(recent_spreads)

                                    if std_spread > 0:
                                        z_score = (current_spread - mean_spread) / std_spread

                        # Add data point to chart
                        # Note: add_data_point will only store z-score if it's meaningful (non-zero)
                        self.chart.add_data_point(timestamp, z_score, 0, prices)

                    print("   📈 Chart populated with historical market data")

                    # Update the chart to show all the historical data
                    if hasattr(self.chart, "update_chart"):
                        self.chart.update_chart()

                # Test z-score calculation with current market prices
                current_prices = self.get_current_prices()
                if current_prices:
                    current_spread = self.calculate_spread(current_prices)
                    test_z_score = self.calculate_z_score(current_spread)

                    print(f"   🎯 Bootstrap complete! Z-score ready with {min_count} data points")
                    print(f"   📊 Current z-score: {test_z_score:+.3f} (threshold: ±{self.z_threshold})")
                    logger.info(f"Bootstrap successful: z-score calculation ready with {min_count} data points")

                    if abs(test_z_score) > self.z_threshold:
                        signal_text = "LONG" if test_z_score < -self.z_threshold else "SHORT"
                        print(f"   🚨 Immediate signal detected: {signal_text} (z-score: {test_z_score:+.3f})")
                    else:
                        print(f"   💤 Market in neutral zone (z-score: {test_z_score:+.3f})")
                else:
                    print("   ⚠️  Bootstrap data loaded but current prices unavailable")
            else:
                warn_str = f"Bootstrap incomplete: {symbol1_count}/{self.lookback_period} "
                warn_str += f"and {symbol2_count}/{self.lookback_period} data points"
                logger.warning(warn_str)
                remaining_time = max(0, self.lookback_period - min_count)
                print(f"   📊 Partial bootstrap: {min_count}/{self.lookback_period} points loaded")
                if remaining_time > 0:
                    print(f"   ⏱️  Will need {remaining_time} more minutes of live data for full z-score")

        except Exception as e:
            logger.error(f"Bootstrap failed: {e}")
            print(f"   ❌ Bootstrap failed: {e}")
            print(f"   📊 Will collect data normally - z-score ready in ~{self.lookback_period} minutes")

    async def run_trading_loop(self, update_interval: int = 60):
        """Main trading loop."""
        logger.info("Starting live pair trading loop...")

        # Print initial header
        print(f"\n🚀 {self.symbol1} vs {self.symbol2} LIVE PAPER TRADING")
        print("=" * 60)
        print("📊 Updates every 60 seconds | Press Ctrl+C to stop")
        if self.chart:
            print("📈 Live chart window should be visible")
        print("=" * 60)

        # Bootstrap price history for faster startup
        await self.bootstrap_price_history()

        try:
            while True:
                try:
                    # Get current prices
                    prices = self.get_current_prices()
                    if not prices:
                        print("⚠️  Could not fetch prices, retrying...")
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

                    # Add data point to chart
                    if self.chart:
                        timestamp = datetime.now()
                        self.chart.add_data_point(timestamp, z_score, self.current_position, prices)

                    # Generate trading signal
                    signal = self.generate_signal(z_score)

                    # Execute trade if signal changes
                    if signal != self.current_position:
                        trade_executed = self.execute_paper_trade(signal, prices)
                        if trade_executed:
                            # Add a newline after trade execution to separate from status updates
                            print()

                    # Update performance
                    current_value = self.calculate_portfolio_value(prices)
                    self.update_performance(current_value)

                    # Update chart display
                    if self.chart:
                        self.chart.update_chart()

                    # Print status
                    self.print_status(prices, z_score, signal)

                    # Save state to file
                    self.save_state()

                    # Wait for next update
                    await asyncio.sleep(update_interval)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"\n💥 Error: {e}")
                    logger.error(f"Error in trading loop: {e}")
                    await asyncio.sleep(update_interval)

        finally:
            print("\n\n🛑 Trading stopped by user")
            logger.info("Trading loop interrupted by user")

            # Close chart if it exists
            if self.chart:
                print("📈 Closing chart window...")
                self.chart.close()

            print("💾 Trading state saved")
            self.save_state()

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
    # Initialize trader with chart enabled
    trader = LivePairTrader(
        symbol1="ADA/USDT",
        symbol2="BNB/USDT",
        initial_capital=1000.0,
        lookback_period=20,
        z_threshold=2.0,
        paper_trading=True,
        enable_chart=True,
    )

    # Load previous state if exists
    trader.load_state()

    # Run trading loop
    try:
        asyncio.run(trader.run_trading_loop(update_interval=60))  # Update every minute
    except KeyboardInterrupt:
        logger.info("Trading stopped by user")
        if trader.chart:
            trader.chart.close()
        trader.save_state()
    finally:
        # Ensure cleanup
        if trader.chart:
            trader.chart.close()


if __name__ == "__main__":
    main()
