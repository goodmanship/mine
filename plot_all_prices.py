import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import text

from database import get_db_session


def get_all_price_data():
    """Get all price data for all symbols from the database."""
    with get_db_session() as session:
        # Get all data ordered by timestamp
        result = session.execute(text("SELECT symbol, timestamp, close_price FROM crypto_prices ORDER BY timestamp"))

        # Convert to DataFrame
        data = []
        for row in result:
            data.append({"symbol": row.symbol, "timestamp": row.timestamp, "close_price": row.close_price})

    return pd.DataFrame(data)


def plot_all_prices():
    """Create a comprehensive price chart for all cryptocurrencies."""
    print("Loading price data...")
    df = get_all_price_data()

    if df.empty:
        print("No data found!")
        return

    print(f"Loaded {len(df)} price records")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Create subplots for each cryptocurrency
    symbols = df["symbol"].unique()
    n_symbols = len(symbols)

    fig = make_subplots(
        rows=n_symbols, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=symbols, row_heights=[1] * n_symbols
    )

    # Color palette for different cryptocurrencies
    colors = ["#F7931A", "#627EEA", "#0033AD", "#F3BA2F", "#14F195"]  # BTC, ETH, ADA, BNB, SOL

    print("Creating price charts...")
    for i, symbol in enumerate(symbols):
        symbol_data = df[df["symbol"] == symbol].copy()
        symbol_data = symbol_data.sort_values("timestamp")

        # Calculate percentage change from start
        start_price = symbol_data["close_price"].iloc[0]
        symbol_data["pct_change"] = ((symbol_data["close_price"] - start_price) / start_price) * 100

        # Add price line
        fig.add_trace(
            go.Scatter(
                x=symbol_data["timestamp"],
                y=symbol_data["close_price"],
                mode="lines",
                name=symbol,
                line={"color": colors[i % len(colors)], "width": 2},
            ),
            row=i + 1,
            col=1,
        )

        # Add percentage change line on secondary y-axis
        fig.add_trace(
            go.Scatter(
                x=symbol_data["timestamp"],
                y=symbol_data["pct_change"],
                mode="lines",
                name=f"{symbol} % Change",
                line={"color": colors[i % len(colors)], "width": 1, "dash": "dot"},
                yaxis=f"y{i + 2}",
                showlegend=False,
            ),
            row=i + 1,
            col=1,
        )

        # Update y-axis labels
        fig.update_yaxes(title_text=f"{symbol} Price ($)", row=i + 1, col=1)

        # Add secondary y-axis for percentage change
        fig.add_trace(
            go.Scatter(
                x=symbol_data["timestamp"],
                y=symbol_data["pct_change"],
                mode="lines",
                line={"color": colors[i % len(colors)], "width": 1, "dash": "dot"},
                yaxis=f"y{i + 2}",
                showlegend=False,
            ),
            row=i + 1,
            col=1,
        )

        # Configure secondary y-axis
        fig.update_layout({f"yaxis{i + 2}": {"title": f"{symbol} % Change", "overlaying": f"y{i + 1}", "side": "right", "showgrid": False}})

    # Update layout
    fig.update_layout(
        title=f"Price Comparison - {', '.join(symbols)}",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        height=300 * n_symbols,
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )

    # Update x-axis
    fig.update_xaxes(title_text="Date", row=n_symbols, col=1)

    print("Displaying chart...")
    fig.show()

    # Also create a normalized comparison chart
    print("Creating normalized comparison chart...")
    create_normalized_chart(df)


def create_normalized_chart(df):
    """Create a normalized chart showing relative performance."""
    fig = go.Figure()

    colors = ["#F7931A", "#627EEA", "#0033AD", "#F3BA2F", "#14F195"]

    for i, symbol in enumerate(df["symbol"].unique()):
        symbol_data = df[df["symbol"] == symbol].copy()
        symbol_data = symbol_data.sort_values("timestamp")

        # Normalize to start at 100
        start_price = symbol_data["close_price"].iloc[0]
        symbol_data["normalized"] = (symbol_data["close_price"] / start_price) * 100

        fig.add_trace(
            go.Scatter(
                x=symbol_data["timestamp"],
                y=symbol_data["normalized"],
                mode="lines",
                name=symbol,
                line={"color": colors[i % len(colors)], "width": 2},
            )
        )

    fig.update_layout(
        title="Cryptocurrency Performance Comparison (Normalized to 100)",
        xaxis_title="Date",
        yaxis_title="Normalized Price (Base = 100)",
        height=600,
        showlegend=True,
    )

    fig.show()


if __name__ == "__main__":
    plot_all_prices()
