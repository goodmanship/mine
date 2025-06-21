"""Data analysis and visualization for cryptocurrency data."""

import logging
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from plotly.subplots import make_subplots

from config import config
from database import get_db, get_price_data

# Set up plotting style
plt.style.use("seaborn-v0_8")
sns.set_palette("husl")

logger = logging.getLogger(__name__)


class CryptoAnalyzer:
    """Analyzer for cryptocurrency data."""

    def __init__(self):
        """Initialize the analyzer."""
        self.db = next(get_db())

    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, "db"):
            self.db.close()

    def get_data_as_dataframe(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Get price data as pandas DataFrame."""
        data = get_price_data(self.db, symbol, start_date, end_date, timeframe, limit)

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(
            [
                {
                    "timestamp": row.timestamp,
                    "open": row.open_price,
                    "high": row.high_price,
                    "low": row.low_price,
                    "close": row.close_price,
                    "volume": row.volume,
                }
                for row in data
            ]
        )

        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)

        return df

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the DataFrame."""
        if df.empty:
            return df

        # Moving averages
        df["sma_20"] = df["close"].rolling(window=20).mean()
        df["sma_50"] = df["close"].rolling(window=50).mean()
        df["ema_12"] = df["close"].ewm(span=12).mean()
        df["ema_26"] = df["close"].ewm(span=26).mean()

        # MACD
        df["macd"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df["bb_middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
        df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

        # Volume indicators
        df["volume_sma"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"]

        # Price changes
        df["price_change"] = df["close"].pct_change()
        df["price_change_24h"] = df["close"].pct_change(periods=24)

        return df

    def calculate_correlation_matrix(
        self,
        symbols: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
    ) -> pd.DataFrame:
        """Calculate correlation matrix between multiple symbols."""
        price_data = {}

        for symbol in symbols:
            df = self.get_data_as_dataframe(symbol, start_date, end_date, timeframe)
            if not df.empty:
                price_data[symbol] = df["close"]

        if not price_data:
            return pd.DataFrame()

        # Create DataFrame with all price data
        combined_df = pd.DataFrame(price_data)

        # Calculate correlation matrix
        correlation_matrix = combined_df.corr()

        return correlation_matrix

    def plot_price_chart(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
        include_indicators: bool = True,
        save_path: str | None = None,
    ) -> None:
        """Create a comprehensive price chart with indicators."""
        df = self.get_data_as_dataframe(symbol, start_date, end_date, timeframe)

        if df.empty:
            logger.warning(f"No data found for {symbol}")
            return

        if include_indicators:
            df = self.calculate_technical_indicators(df)

        # Create subplots
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(f"{symbol} Price Chart", "Volume", "RSI"),
            row_heights=[0.6, 0.2, 0.2],
        )

        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="Price",
            ),
            row=1,
            col=1,
        )

        # Moving averages
        if include_indicators:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["sma_20"],
                    mode="lines",
                    name="SMA 20",
                    line={"color": "orange", "width": 1},
                ),
                row=1,
                col=1,
            )

            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["sma_50"],
                    mode="lines",
                    name="SMA 50",
                    line={"color": "blue", "width": 1},
                ),
                row=1,
                col=1,
            )

            # Bollinger Bands
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["bb_upper"],
                    mode="lines",
                    name="BB Upper",
                    line={"color": "gray", "width": 1, "dash": "dash"},
                ),
                row=1,
                col=1,
            )

            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["bb_lower"],
                    mode="lines",
                    name="BB Lower",
                    line={"color": "gray", "width": 1, "dash": "dash"},
                    fill="tonexty",
                ),
                row=1,
                col=1,
            )

        # Volume
        colors = [
            "red" if close < open else "green"
            for close, open in zip(df["close"], df["open"], strict=False)
        ]

        fig.add_trace(
            go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=colors),
            row=2,
            col=1,
        )

        # RSI
        if include_indicators:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["rsi"],
                    mode="lines",
                    name="RSI",
                    line={"color": "purple", "width": 1},
                ),
                row=3,
                col=1,
            )

            # RSI overbought/oversold lines
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        # Update layout
        fig.update_layout(
            title=f"{symbol} Analysis", xaxis_rangeslider_visible=False, height=800
        )

        # Show or save
        if save_path:
            fig.write_html(save_path)
            logger.info(f"Chart saved to {save_path}")
        else:
            fig.show()

    def plot_correlation_heatmap(
        self,
        symbols: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
        save_path: str | None = None,
    ) -> None:
        """Create a correlation heatmap for multiple symbols."""
        correlation_matrix = self.calculate_correlation_matrix(
            symbols, start_date, end_date, timeframe
        )

        if correlation_matrix.empty:
            logger.warning("No correlation data available")
            return

        fig = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="Cryptocurrency Correlation Matrix",
        )

        if save_path:
            fig.write_html(save_path)
            logger.info(f"Correlation heatmap saved to {save_path}")
        else:
            fig.show()

    def generate_summary_statistics(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
    ) -> dict:
        """Generate summary statistics for a symbol."""
        df = self.get_data_as_dataframe(symbol, start_date, end_date, timeframe)

        if df.empty:
            return {}

        # Calculate statistics
        stats = {
            "symbol": symbol,
            "period_start": df.index.min(),
            "period_end": df.index.max(),
            "total_periods": len(df),
            "current_price": df["close"].iloc[-1],
            "price_change_total": (
                (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0]
            )
            * 100,
            "highest_price": df["high"].max(),
            "lowest_price": df["low"].min(),
            "average_price": df["close"].mean(),
            "price_volatility": df["close"].std(),
            "total_volume": df["volume"].sum(),
            "average_volume": df["volume"].mean(),
            "max_volume": df["volume"].max(),
            "price_change_std": df["price_change"].std() * 100,  # Daily volatility
            "positive_days": (df["price_change"] > 0).sum(),
            "negative_days": (df["price_change"] < 0).sum(),
        }

        return stats

    def compare_symbols(
        self,
        symbols: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
    ) -> pd.DataFrame:
        """Compare performance of multiple symbols."""
        comparison_data = []

        for symbol in symbols:
            stats = self.generate_summary_statistics(
                symbol, start_date, end_date, timeframe
            )
            if stats:
                comparison_data.append(stats)

        if not comparison_data:
            return pd.DataFrame()

        df = pd.DataFrame(comparison_data)
        df.set_index("symbol", inplace=True)

        return df


def main():
    """Main function for testing the analyzer."""
    analyzer = CryptoAnalyzer()

    # Test with a few symbols
    symbols = config.DEFAULT_SYMBOLS[:3]

    # Generate summary statistics
    print("Summary Statistics:")
    for symbol in symbols:
        stats = analyzer.generate_summary_statistics(symbol, days_back=30)
        if stats:
            print(f"\n{symbol}:")
            print(f"  Current Price: ${stats['current_price']:,.2f}")
            print(f"  Total Change: {stats['price_change_total']:.2f}%")
            print(f"  Volatility: {stats['price_change_std']:.2f}%")

    # Create correlation heatmap
    print(f"\nCreating correlation heatmap for {symbols}...")
    analyzer.plot_correlation_heatmap(symbols, days_back=30)


if __name__ == "__main__":
    main()
