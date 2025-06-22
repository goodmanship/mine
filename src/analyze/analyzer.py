import logging

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from plotly.subplots import make_subplots

from src.core.app_config import config
from src.core.database import get_db_session, get_price_data

plt.style.use("seaborn-v0_8")
sns.set_palette("husl")

logger = logging.getLogger(__name__)


class CryptoAnalyzer:
    def get_data_as_dataframe(self, symbol, start_date=None, end_date=None, timeframe="1h", limit=None):
        with get_db_session() as db:
            data = get_price_data(db, symbol, start_date, end_date, timeframe, limit)

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame([
            {
                "timestamp": row.timestamp,
                "open": row.open_price,
                "high": row.high_price,
                "low": row.low_price,
                "close": row.close_price,
                "volume": row.volume,
            }
            for row in data
        ])

        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)

        return df

    def calculate_technical_indicators(self, df):
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

    def calculate_correlation_matrix(self, symbols, start_date=None, end_date=None, timeframe="1h"):
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
        symbol,
        start_date=None,
        end_date=None,
        timeframe="1h",
        include_indicators=True,
        save_path=None,
    ):
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
            go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="Price"),
            row=1,
            col=1,
        )

        if include_indicators:
            fig.add_trace(
                go.Scatter(x=df.index, y=df["sma_20"], mode="lines", name="SMA 20", line={"color": "orange", "width": 1}),
                row=1,
                col=1,
            )

            fig.add_trace(
                go.Scatter(x=df.index, y=df["sma_50"], mode="lines", name="SMA 50", line={"color": "blue", "width": 1}),
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

        fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=colors), row=2, col=1)

        if include_indicators:
            fig.add_trace(
                go.Scatter(x=df.index, y=df["rsi"], mode="lines", name="RSI", line={"color": "purple", "width": 1}),
                row=3,
                col=1,
            )

            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        fig.update_layout(
            title=f"{symbol} Price Chart ({timeframe})",
            xaxis_title="Date",
            yaxis_title="Price",
            height=800,
            showlegend=True,
        )

        if save_path:
            fig.write_html(save_path)
        else:
            fig.show()

    def plot_correlation_heatmap(self, symbols, start_date=None, end_date=None, timeframe="1h", save_path=None):
        correlation_matrix = self.calculate_correlation_matrix(symbols, start_date, end_date, timeframe)

        if correlation_matrix.empty:
            logger.warning("No data available for correlation analysis")
            return

        fig = go.Figure(
            data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.index,
                colorscale="RdBu",
                zmid=0,
                text=correlation_matrix.round(3).values,
                texttemplate="%{text}",
                textfont={"size": 10},
            )
        )

        fig.update_layout(title=f"Correlation Matrix ({timeframe})", xaxis_title="Symbols", yaxis_title="Symbols", height=600)

        if save_path:
            fig.write_html(save_path)
        else:
            fig.show()

    def generate_summary_statistics(self, symbol, start_date=None, end_date=None, timeframe="1h"):
        df = self.get_data_as_dataframe(symbol, start_date, end_date, timeframe)

        if df.empty:
            return {}

        df = self.calculate_technical_indicators(df)

        latest_price = df["close"].iloc[-1]
        first_price = df["close"].iloc[0]
        price_change = latest_price - first_price
        price_change_pct = (price_change / first_price) * 100

        volatility = df["price_change"].std() * 100
        volume_24h = df["volume"].iloc[-24:].sum() if len(df) >= 24 else df["volume"].sum()

        return {
            "symbol": symbol,
            "latest_price": latest_price,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "volatility": volatility,
            "24h_volume": volume_24h,
            "rsi": df["rsi"].iloc[-1] if "rsi" in df.columns else None,
            "sma_20": df["sma_20"].iloc[-1] if "sma_20" in df.columns else None,
            "sma_50": df["sma_50"].iloc[-1] if "sma_50" in df.columns else None,
        }

    def compare_symbols(self, symbols, start_date=None, end_date=None, timeframe="1h"):
        comparison_data = []

        for symbol in symbols:
            stats = self.generate_summary_statistics(symbol, start_date, end_date, timeframe)
            if stats:
                comparison_data.append(stats)

        if not comparison_data:
            return pd.DataFrame()

        return pd.DataFrame(comparison_data).set_index("symbol")


def main():
    analyzer = CryptoAnalyzer()

    symbols = config.DEFAULT_SYMBOLS[:3]

    print("Generating summary statistics...")
    for symbol in symbols:
        stats = analyzer.generate_summary_statistics(symbol)
        if stats:
            print(f"\n{symbol}:")
            print(f"  Latest Price: ${stats['latest_price']:,.2f}")
            print(f"  Price Change: {stats['price_change_pct']:+.2f}%")
            print(f"  Volatility: {stats['volatility']:.2f}%")
            print(f"  24h Volume: {stats['24h_volume']:,.0f}")


if __name__ == "__main__":
    main()
