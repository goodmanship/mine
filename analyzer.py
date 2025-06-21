import logging
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from plotly.subplots import make_subplots

from config import config
from database import get_db_session, get_price_data

plt.style.use("seaborn-v0_8")
sns.set_palette("husl")

logger = logging.getLogger(__name__)


class CryptoAnalyzer:
    def get_data_as_dataframe(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
        limit: int | None = None,
    ) -> pd.DataFrame:
        with get_db_session() as db:
            data = get_price_data(db, symbol, start_date, end_date, timeframe, limit)

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
        if df.empty:
            return df

        df["sma_20"] = df["close"].rolling(window=20).mean()
        df["sma_50"] = df["close"].rolling(window=50).mean()
        df["ema_12"] = df["close"].ewm(span=12).mean()
        df["ema_26"] = df["close"].ewm(span=26).mean()

        df["macd"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        df["bb_middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
        df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

        df["volume_sma"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"]

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
        price_data = {}

        for symbol in symbols:
            df = self.get_data_as_dataframe(symbol, start_date, end_date, timeframe)
            if not df.empty:
                price_data[symbol] = df["close"]

        if not price_data:
            return pd.DataFrame()

        combined_df = pd.DataFrame(price_data)
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
        df = self.get_data_as_dataframe(symbol, start_date, end_date, timeframe)

        if df.empty:
            logger.warning(f"No data found for {symbol}")
            return

        if include_indicators:
            df = self.calculate_technical_indicators(df)

        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(f"{symbol} Price Chart", "Volume", "RSI"),
            row_heights=[0.6, 0.2, 0.2],
        )

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

        colors = ["red" if close < open else "green" for close, open in zip(df["close"], df["open"], strict=False)]

        fig.add_trace(
            go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=colors),
            row=2,
            col=1,
        )

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

            fig.add_hline(
                y=70,
                line_dash="dash",
                line_color="red",
                row=3,
                col=1,
                annotation_text="Overbought",
                annotation_position="bottom right",
            )

            fig.add_hline(
                y=30,
                line_dash="dash",
                line_color="green",
                row=3,
                col=1,
                annotation_text="Oversold",
                annotation_position="bottom right",
            )

        fig.update_layout(
            title_text=f"{symbol} Price Analysis",
            xaxis_title="Date",
            yaxis_title="Price (USDT)",
            xaxis_rangeslider_visible=False,
            showlegend=True,
            legend_title="Indicators",
        )

        if save_path:
            fig.write_html(save_path)
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
        correlation_matrix = self.calculate_correlation_matrix(symbols, start_date, end_date, timeframe)

        if correlation_matrix.empty:
            logger.warning("Could not generate correlation matrix: no data")
            return

        plt.figure(figsize=(12, 10))
        sns.heatmap(
            correlation_matrix,
            annot=True,
            cmap="coolwarm",
            fmt=".2f",
            linewidths=0.5,
        )
        plt.title("Cryptocurrency Correlation Heatmap")
        plt.xlabel("Symbols")
        plt.ylabel("Symbols")

        if save_path:
            plt.savefig(save_path)
            logger.info(f"Correlation heatmap saved to {save_path}")
        else:
            plt.show()

    def generate_summary_statistics(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
    ) -> dict:
        df = self.get_data_as_dataframe(symbol, start_date, end_date, timeframe)

        if df.empty:
            return {}

        df = self.calculate_technical_indicators(df)

        summary = {
            "symbol": symbol,
            "start_date": df.index.min(),
            "end_date": df.index.max(),
            "total_days": (df.index.max() - df.index.min()).days,
            "latest_price": df["close"].iloc[-1],
            "price_change_pct": ((df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0]) * 100,
            "24h_high": df["high"].last("24h").max(),
            "24h_low": df["low"].last("24h").min(),
            "24h_volume": df["volume"].last("24h").sum(),
            "volatility": df["close"].pct_change().std() * (365**0.5),  # Annualized
            "latest_rsi": df["rsi"].iloc[-1],
        }

        return summary

    def compare_symbols(
        self,
        symbols: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
    ) -> pd.DataFrame:
        comparison_data = []

        for symbol in symbols:
            stats = self.generate_summary_statistics(symbol, start_date, end_date, timeframe)
            if stats:
                comparison_data.append(stats)

        if not comparison_data:
            return pd.DataFrame()

        # Create DataFrame and sort by performance
        df = pd.DataFrame(comparison_data)
        df.sort_values(by="price_change_pct", ascending=False, inplace=True)

        return df


def main():
    analyzer = CryptoAnalyzer()

    # Example usage:
    symbol = config.DEFAULT_SYMBOLS[0]
    days_back = 30
    start_date = datetime.now() - pd.Timedelta(days=days_back)

    # Get data
    df = analyzer.get_data_as_dataframe(symbol, start_date)
    print(f"Data for {symbol}:\n{df.head()}\n")

    # Calculate indicators
    df_with_indicators = analyzer.calculate_technical_indicators(df)
    print(f"Data with indicators:\n{df_with_indicators.tail()}\n")

    # Generate summary
    summary = analyzer.generate_summary_statistics(symbol, start_date)
    print(f"Summary statistics:\n{summary}\n")

    # Plot chart
    analyzer.plot_price_chart(symbol, start_date, include_indicators=True)

    # Compare symbols
    comparison = analyzer.compare_symbols(config.DEFAULT_SYMBOLS, start_date)
    print(f"Symbol comparison:\n{comparison}")


if __name__ == "__main__":
    main()
