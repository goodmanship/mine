from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from src.backtest.backtester import PairTradingBacktester


@pytest.fixture
def backtester():
    """Pytest fixture to create a PairTradingBacktester instance."""
    with patch("src.backtest.backtester.CryptoAnalyzer") as mock_analyzer:
        instance = PairTradingBacktester(initial_capital=1000)
        instance.analyzer = mock_analyzer.return_value
        return instance


def create_mock_pair_data(len=30):
    """Helper function to create mock pair data for testing."""
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=len))
    # Add more volatility to trigger trades
    price1 = [100 + i + (i % 3) * 15 * (-1) ** i for i in range(len)]
    price2 = [100 + i for i in range(len)]
    df1 = pd.DataFrame({"close": price1}, index=dates)
    df2 = pd.DataFrame({"close": price2}, index=dates)
    return df1, df2


def test_backtester_initialization(backtester):
    """Test that the PairTradingBacktester initializes correctly."""
    assert backtester is not None
    assert backtester.initial_capital == 1000


def test_get_pair_data(backtester):
    """Test the fetching and processing of paired data."""
    df1, df2 = create_mock_pair_data()
    backtester.analyzer.get_data_as_dataframe.side_effect = [df1, df2]

    combined = backtester.get_pair_data("SYM1/USDT", "SYM2/USDT")

    assert not combined.empty
    assert "price_ratio" in combined.columns
    assert "z_score" in combined.columns
    assert backtester.analyzer.get_data_as_dataframe.call_count == 2


def test_backtest_mean_reversion_executes_trades(backtester):
    """Test the core mean reversion backtesting logic with predictable data."""
    # Create a dataset where z-score will definitely cross the threshold
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=50))
    price1 = [100] * 25 + [150] * 25  # A sudden jump to force a trade
    price2 = [100] * 50
    df1 = pd.DataFrame({"close": price1}, index=dates)
    df2 = pd.DataFrame({"close": price2}, index=dates)
    backtester.analyzer.get_data_as_dataframe.side_effect = [df1, df2]

    portfolio = backtester.backtest_mean_reversion("SYM1/USDT", "SYM2/USDT", z_score_threshold=1.5)

    assert len(portfolio["trades"]) > 0


def test_analyze_results(backtester):
    """Test the analysis of backtest results."""
    # Create a dummy portfolio to analyze
    portfolio = {
        "portfolio_values": [
            {"timestamp": datetime(2023, 1, 1), "value": 1000, "z_score": 0, "SYM1/USDT_price": 100, "SYM2/USDT_price": 100},
            {"timestamp": datetime(2023, 1, 2), "value": 1050, "z_score": 1, "SYM1/USDT_price": 105, "SYM2/USDT_price": 100},
            {"timestamp": datetime(2023, 1, 3), "value": 1020, "z_score": -1, "SYM1/USDT_price": 102, "SYM2/USDT_price": 100},
        ],
        "trades": [
            {"portfolio_value": 1000},
            {"portfolio_value": 1050},
        ],
    }

    results = backtester.analyze_results(portfolio, "SYM1/USDT", "SYM2/USDT")

    assert "total_return_pct" in results
    assert "sharpe_ratio" in results
    assert "max_drawdown_pct" in results
    assert results["total_return_pct"] == 2.0  # (1020 - 1000) / 1000
