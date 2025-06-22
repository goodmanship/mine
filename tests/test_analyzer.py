from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from src.analyze.analyzer import CryptoAnalyzer


@pytest.fixture
def analyzer():
    """Pytest fixture to create a CryptoAnalyzer instance."""
    return CryptoAnalyzer()


def create_test_data(symbol: str, num_records: int = 100):
    """Create test crypto price data as mock objects."""
    data = []
    for i in range(num_records):
        mock_price = Mock()
        mock_price.symbol = symbol
        mock_price.timestamp = datetime(2023, 1, 1) + pd.to_timedelta(i, "h")
        mock_price.open_price = 100 + i
        mock_price.high_price = 105 + i
        mock_price.low_price = 95 + i
        mock_price.close_price = 102 + i
        mock_price.volume = 1000 + i * 10
        data.append(mock_price)
    return data


def test_analyzer_initialization(analyzer):
    """
    Tests that the CryptoAnalyzer class can be initialized.
    """
    assert analyzer is not None


@patch("src.analyze.analyzer.get_db_session")
def test_get_data_as_dataframe(mock_get_db_session, analyzer):
    """Test converting database price data to a pandas DataFrame."""
    mock_session = MagicMock()
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    # Mock the return value of get_price_data
    mock_data = create_test_data("BTC/USDT", 5)
    with patch("src.analyze.analyzer.get_price_data", return_value=mock_data):
        df = analyzer.get_data_as_dataframe("BTC/USDT")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 5
        assert "close" in df.columns
        assert df.index.name == "timestamp"


def test_calculate_technical_indicators(analyzer):
    """Test calculation of various technical indicators."""
    data = {
        "timestamp": pd.to_datetime(pd.date_range(start="2023-01-01", periods=30)),
        "open": [100 + i for i in range(30)],
        "high": [105 + i for i in range(30)],
        "low": [95 + i for i in range(30)],
        "close": [102 + i for i in range(30)],
        "volume": [1000 + i * 10 for i in range(30)],
    }
    df = pd.DataFrame(data).set_index("timestamp")

    df_indicators = analyzer.calculate_technical_indicators(df)

    assert "sma_20" in df_indicators.columns
    assert "rsi" in df_indicators.columns
    assert "macd" in df_indicators.columns
    assert "bb_upper" in df_indicators.columns
    # Check that the first 19 values of sma_20 are NaN
    assert df_indicators["sma_20"].isna().sum() == 19
