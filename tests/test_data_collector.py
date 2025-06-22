from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd

from src.data.data_collector import BinanceDataCollector


@patch("src.data.data_collector.ccxt.binanceus")
def test_collector_initialization(mock_ccxt_binanceus):
    """Test that the BinanceDataCollector initializes correctly."""
    mock_exchange = Mock()
    mock_exchange.load_markets.return_value = True
    mock_ccxt_binanceus.return_value = mock_exchange

    with (
        patch("src.data.data_collector.config.BINANCE_API_KEY", "test_key"),
        patch("src.data.data_collector.config.BINANCE_SECRET_KEY", "test_secret"),
    ):
        collector = BinanceDataCollector()
        assert collector is not None
        assert collector.exchange.load_markets.called  # type: ignore


@patch("src.data.data_collector.ccxt.binanceus")
def test_fetch_ohlcv(mock_ccxt_binanceus):
    """Test fetching and parsing of OHLCV data."""
    mock_exchange = Mock()
    mock_exchange.load_markets.return_value = True
    # Sample raw response from ccxt
    raw_ohlcv = [
        [1672531200000, 100, 105, 95, 102, 1000],  # 2023-01-01 00:00:00
        [1672534800000, 102, 108, 100, 105, 1200],  # 2023-01-01 01:00:00
    ]
    mock_exchange.fetch_ohlcv.return_value = raw_ohlcv
    mock_ccxt_binanceus.return_value = mock_exchange

    with (
        patch("src.data.data_collector.config.BINANCE_API_KEY", "test_key"),
        patch("src.data.data_collector.config.BINANCE_SECRET_KEY", "test_secret"),
    ):
        collector = BinanceDataCollector()
        df = collector.fetch_ohlcv("BTC/USDT", "1h")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "timestamp" in df.columns
        assert df["timestamp"].iloc[0] == pd.to_datetime("2023-01-01 00:00:00")
        assert df["close"].iloc[1] == 105


@patch("src.data.data_collector.save_price_data")
@patch("src.data.data_collector.get_db_session")
@patch("src.data.data_collector.ccxt.binanceus")
def test_save_to_database(mock_ccxt_binanceus, mock_get_db_session, mock_save):
    """Test saving DataFrame to the database."""
    mock_exchange = Mock()
    mock_exchange.load_markets.return_value = True
    mock_ccxt_binanceus.return_value = mock_exchange

    mock_session = Mock()
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with (
        patch("src.data.data_collector.config.BINANCE_API_KEY", "test_key"),
        patch("src.data.data_collector.config.BINANCE_SECRET_KEY", "test_secret"),
    ):
        collector = BinanceDataCollector()

        data = {
            "timestamp": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
            "open": [100, 102],
            "high": [105, 108],
            "low": [95, 100],
            "close": [102, 105],
            "volume": [1000, 1200],
        }
        df = pd.DataFrame(data)

        collector.save_to_database("BTC/USDT", df)

        assert mock_save.call_count == 2
        # Check the second call
        args, kwargs = mock_save.call_args
        assert kwargs["symbol"] == "BTC/USDT"
        assert kwargs["close_price"] == 105
