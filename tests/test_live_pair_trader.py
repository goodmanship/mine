import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, mock_open, patch

import numpy as np

# Mock ccxt before importing the trader
sys.modules["ccxt"] = MagicMock()
sys.modules["ccxt.base"] = MagicMock()
sys.modules["ccxt.base.types"] = MagicMock()

from src.trade.live_pair_trader import LivePairTrader  # noqa: E402


class TestLivePairTrader(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        os.environ["BINANCE_API_KEY"] = "test_key"
        os.environ["BINANCE_SECRET"] = "test_secret"

        # Create trader instance
        self.trader = LivePairTrader(symbol1="ADA/USDT", symbol2="BNB/USDT", initial_capital=1000.0, z_threshold=2.0, paper_trading=True)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_initial_portfolio_state(self, mock_ccxt):
        """Test that portfolio is correctly initialized."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = True
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)

        self.assertEqual(trader.portfolio["cash"], 1000.0)
        self.assertEqual(trader.portfolio["total_value"], 1000.0)
        self.assertEqual(trader.portfolio["pnl"], 0.0)
        self.assertEqual(trader.portfolio["positions"]["ADA/USDT"], 0.0)
        self.assertEqual(trader.portfolio["positions"]["BNB/USDT"], 0.0)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_position_sizing_preserves_capital(self, mock_ccxt):
        """Test that position sizing uses meaningful amounts consistently."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = True
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)

        # Test prices
        prices = {"ADA/USDT": 0.5, "BNB/USDT": 500.0}

        # First trade - should use 10% of portfolio (conservative sizing)
        trader.execute_paper_trade(1, prices)  # Long spread

        # Position sizes should be meaningful, not microscopic
        ada_position = abs(trader.portfolio["positions"]["ADA/USDT"])
        bnb_position = abs(trader.portfolio["positions"]["BNB/USDT"])

        # With 10% allocation: $1000 * 0.10 = $100, split $50 each
        # ADA: $50 / $0.5 = 100 ADA, BNB: $50 / $500 = 0.1 BNB
        self.assertAlmostEqual(ada_position, 100.0, places=1)  # Should be ~100 ADA
        self.assertAlmostEqual(bnb_position, 0.1, places=2)  # Should be ~0.1 BNB

        # But when prices change, we should see profit/loss
        new_prices = {"ADA/USDT": 0.55, "BNB/USDT": 495.0}  # ADA up, BNB down
        portfolio_value_new_prices = trader.calculate_portfolio_value(new_prices)

        # Should show a profit since we're long ADA (up) and short BNB (down)
        self.assertGreater(portfolio_value_new_prices, 1005.0)  # Should be profitable

    @patch("src.trade.live_pair_trader.ccxt")
    def test_calculate_position_sizes_uses_initial_capital(self, mock_ccxt):
        """Test that position sizing calculates correctly based on current portfolio value."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = True
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)

        # Simulate a state where cash is 0 but positions have value (total portfolio = $500)
        trader.portfolio["cash"] = 0.0
        trader.portfolio["positions"]["ADA/USDT"] = 1000.0  # 1000 ADA at $0.5 = $500
        trader.portfolio["positions"]["BNB/USDT"] = -1.0  # -1 BNB at $500 = -$500 (net = $0)

        prices = {"ADA/USDT": 0.5, "BNB/USDT": 500.0}

        # With portfolio value of $0, position sizing should return 0 (portfolio too small)
        position_sizes = trader.calculate_position_sizes(prices)

        # Position sizes should be 0 since portfolio is too small to trade
        self.assertEqual(position_sizes["ADA/USDT"], 0.0)
        self.assertEqual(position_sizes["BNB/USDT"], 0.0)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_multiple_trades_maintain_position_sizing(self, mock_ccxt):
        """Test that multiple trades maintain meaningful position sizes."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = True
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)

        # Simulate multiple trades with changing prices
        prices_sequence = [
            {"ADA/USDT": 0.50, "BNB/USDT": 500.0},
            {"ADA/USDT": 0.52, "BNB/USDT": 498.0},
            {"ADA/USDT": 0.48, "BNB/USDT": 505.0},
            {"ADA/USDT": 0.51, "BNB/USDT": 502.0},
        ]

        signals = [1, -1, 1, -1]  # Alternating signals

        for i, (prices, signal) in enumerate(zip(prices_sequence, signals, strict=False)):
            trader.execute_paper_trade(signal, prices)

            # Positions should remain meaningful with conservative 10% sizing
            ada_pos = abs(trader.portfolio["positions"]["ADA/USDT"])
            bnb_pos = abs(trader.portfolio["positions"]["BNB/USDT"])

            # With 10% allocation, positions should be around 100 ADA and 0.1 BNB
            self.assertGreater(ada_pos, 90.0, f"ADA position too small after trade {i + 1}: {ada_pos}")
            self.assertGreater(bnb_pos, 0.09, f"BNB position too small after trade {i + 1}: {bnb_pos}")

    @patch("src.trade.live_pair_trader.ccxt")
    def test_portfolio_value_calculation(self, mock_ccxt):
        """Test that portfolio value is calculated correctly."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = True
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)

        # Set up a known portfolio state
        trader.portfolio["cash"] = 100.0
        trader.portfolio["positions"]["ADA/USDT"] = 1000.0  # 1000 ADA
        trader.portfolio["positions"]["BNB/USDT"] = -0.5  # -0.5 BNB (short)

        prices = {"ADA/USDT": 0.6, "BNB/USDT": 600.0}

        # Expected value: 100 + (1000 * 0.6) + (-0.5 * 600) = 100 + 600 - 300 = 400
        expected_value = 100.0 + (1000.0 * 0.6) + (-0.5 * 600.0)
        calculated_value = trader.calculate_portfolio_value(prices)

        self.assertAlmostEqual(calculated_value, expected_value, places=2)

    # NEW TESTS FOR BETTER COVERAGE

    @patch("src.trade.live_pair_trader.ccxt")
    def test_get_current_prices_success(self, mock_ccxt):
        """Test successful price fetching."""
        mock_exchange = Mock()
        mock_exchange.fetch_ticker.side_effect = [{"last": 0.5}, {"last": 500.0}]
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader()
        # Replace the exchange instance with our mock
        trader.exchange = mock_exchange

        prices = trader.get_current_prices()

        self.assertEqual(prices["ADA/USDT"], 0.5)
        self.assertEqual(prices["BNB/USDT"], 500.0)
        self.assertEqual(mock_exchange.fetch_ticker.call_count, 2)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_get_current_prices_error(self, mock_ccxt):
        """Test price fetching with exchange error."""
        mock_exchange = Mock()
        mock_exchange.fetch_ticker.side_effect = Exception("Network error")
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader()
        # Replace the exchange instance with our mock
        trader.exchange = mock_exchange

        prices = trader.get_current_prices()

        self.assertEqual(prices, {})

    def test_calculate_spread(self):
        """Test spread calculation."""
        trader = LivePairTrader()

        # Normal case
        prices = {"ADA/USDT": 0.5, "BNB/USDT": 500.0}
        spread = trader.calculate_spread(prices)
        expected = np.log(0.5) - np.log(500.0)
        self.assertAlmostEqual(spread, expected, places=6)

        # Empty prices
        self.assertEqual(trader.calculate_spread({}), 0.0)

        # Insufficient prices
        self.assertEqual(trader.calculate_spread({"ADA/USDT": 0.5}), 0.0)

    def test_calculate_z_score(self):
        """Test z-score calculation."""
        trader = LivePairTrader(lookback_period=5)

        # Add some price history
        trader.price_history["ADA/USDT"] = [0.4, 0.45, 0.5, 0.55, 0.6]
        trader.price_history["BNB/USDT"] = [400, 450, 500, 550, 600]

        current_spread = np.log(0.65) - np.log(650)
        z_score = trader.calculate_z_score(current_spread)

        # Should return a finite number
        self.assertIsInstance(z_score, float)
        self.assertFalse(np.isnan(z_score))

        # Test with insufficient history
        trader.price_history["ADA/USDT"] = [0.5]
        trader.price_history["BNB/USDT"] = [500]
        self.assertEqual(trader.calculate_z_score(0.1), 0.0)

        # Test with zero std deviation
        trader.price_history["ADA/USDT"] = [0.5] * 10
        trader.price_history["BNB/USDT"] = [500] * 10
        self.assertEqual(trader.calculate_z_score(0.1), 0.0)

    def test_generate_signal(self):
        """Test signal generation."""
        trader = LivePairTrader(z_threshold=2.0)

        # Test long signal
        self.assertEqual(trader.generate_signal(-2.5), 1)

        # Test short signal
        self.assertEqual(trader.generate_signal(2.5), -1)

        # Test no signal
        self.assertEqual(trader.generate_signal(1.5), 0)
        self.assertEqual(trader.generate_signal(-1.5), 0)
        self.assertEqual(trader.generate_signal(0), 0)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_close_positions(self, mock_ccxt):
        """Test position closing functionality."""
        mock_exchange = Mock()
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)

        # Set up positions
        trader.portfolio["cash"] = 200.0
        trader.portfolio["positions"]["ADA/USDT"] = 100.0
        trader.portfolio["positions"]["BNB/USDT"] = -0.2
        trader.current_position = 1

        prices = {"ADA/USDT": 0.6, "BNB/USDT": 600.0}

        # Close positions
        trader.close_positions(prices)

        # Check that positions are cleared
        self.assertEqual(trader.portfolio["positions"]["ADA/USDT"], 0.0)
        self.assertEqual(trader.portfolio["positions"]["BNB/USDT"], 0.0)
        self.assertEqual(trader.current_position, 0)

        # Check cash calculation: 200 + (100 * 0.6) + (-0.2 * 600) = 200 + 60 - 120 = 140
        expected_cash = 200.0 + (100.0 * 0.6) + (-0.2 * 600.0)
        self.assertEqual(trader.portfolio["cash"], expected_cash)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_close_positions_empty_prices(self, mock_ccxt):
        """Test closing positions with empty prices."""
        mock_exchange = Mock()
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader()
        initial_cash = trader.portfolio["cash"]

        trader.close_positions({})

        # Should not crash and should not change cash
        self.assertEqual(trader.portfolio["cash"], initial_cash)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_update_performance(self, mock_ccxt):
        """Test performance metrics updating."""
        mock_exchange = Mock()
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)
        trader.trade_count = 5

        # Add some mock trades
        trader.portfolio["trades"] = [{"pnl": 10}, {"pnl": -5}, {"pnl": 15}, {"pnl": -2}, {"pnl": 8}]

        trader.update_performance(1100.0)

        self.assertEqual(trader.portfolio["total_value"], 1100.0)
        self.assertEqual(trader.portfolio["pnl"], 100.0)
        self.assertAlmostEqual(trader.performance["total_return"], 10.0, places=5)  # Use assertAlmostEqual for floating point
        self.assertEqual(trader.performance["total_trades"], 5)
        self.assertEqual(trader.performance["win_rate"], 60.0)  # 3 winning trades out of 5

    @patch("src.trade.live_pair_trader.ccxt")
    def test_portfolio_value_with_empty_prices(self, mock_ccxt):
        """Test portfolio value calculation with empty prices."""
        mock_exchange = Mock()
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)
        trader.portfolio["cash"] = 800.0

        # With empty prices, should return only cash
        value = trader.calculate_portfolio_value({})
        self.assertEqual(value, 800.0)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_execute_paper_trade_no_signal(self, mock_ccxt):
        """Test that no trade is executed with signal = 0."""
        mock_exchange = Mock()
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader()
        prices = {"ADA/USDT": 0.5, "BNB/USDT": 500.0}

        result = trader.execute_paper_trade(0, prices)

        self.assertFalse(result)
        self.assertEqual(trader.current_position, 0)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_execute_paper_trade_error_handling(self, mock_ccxt):
        """Test error handling in trade execution."""
        mock_exchange = Mock()
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader()

        # Mock calculate_position_sizes to raise an exception
        with patch.object(trader, "calculate_position_sizes", side_effect=Exception("Test error")):
            result = trader.execute_paper_trade(1, {"ADA/USDT": 0.5, "BNB/USDT": 500.0})
            self.assertFalse(result)

    def test_save_and_load_state(self):
        """Test state saving and loading."""
        trader = LivePairTrader(initial_capital=1000.0)

        # Modify some state
        trader.portfolio["cash"] = 800.0
        trader.current_position = 1
        trader.trade_count = 3
        trader.performance["total_return"] = 15.0

        # Use temporary file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_filename = f.name

        try:
            # Mock the filename
            with patch("builtins.open", mock_open()) as mock_file:
                trader.save_state()

                # Verify save was called
                mock_file.assert_called_once_with("trading_state.json", "w")

            # Test loading state
            mock_state = {
                "portfolio": {"cash": 800.0, "total_value": 1000.0},
                "performance": {"total_return": 15.0},
                "current_position": 1,
                "trade_count": 3,
            }

            with patch("builtins.open", mock_open(read_data=json.dumps(mock_state))):
                trader.load_state()

                self.assertEqual(trader.portfolio["cash"], 800.0)
                self.assertEqual(trader.current_position, 1)
                self.assertEqual(trader.trade_count, 3)

        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_load_state_file_not_found(self):
        """Test loading state when file doesn't exist."""
        trader = LivePairTrader()

        with patch("builtins.open", side_effect=FileNotFoundError):
            trader.load_state()  # Should not crash

        # State should remain unchanged
        self.assertEqual(trader.portfolio["cash"], 1000.0)

    def test_load_state_json_error(self):
        """Test loading state with JSON error."""
        trader = LivePairTrader()

        with patch("builtins.open", mock_open(read_data="invalid json")):
            trader.load_state()  # Should not crash

        # State should remain unchanged
        self.assertEqual(trader.portfolio["cash"], 1000.0)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_position_sizes_small_portfolio(self, mock_ccxt):
        """Test position sizing with very small portfolio."""
        mock_exchange = Mock()
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader(initial_capital=1000.0)
        trader.portfolio["cash"] = 30.0  # Below $50 threshold

        prices = {"ADA/USDT": 0.5, "BNB/USDT": 500.0}

        position_sizes = trader.calculate_position_sizes(prices, 30.0)

        # Should return zero positions for small portfolio
        self.assertEqual(position_sizes["ADA/USDT"], 0.0)
        self.assertEqual(position_sizes["BNB/USDT"], 0.0)

    @patch("src.trade.live_pair_trader.ccxt")
    def test_position_sizes_zero_prices(self, mock_ccxt):
        """Test position sizing with zero prices."""
        mock_exchange = Mock()
        mock_ccxt.binanceus.return_value = mock_exchange

        trader = LivePairTrader()

        prices = {"ADA/USDT": 0.0, "BNB/USDT": 500.0}
        position_sizes = trader.calculate_position_sizes(prices, 1000.0)

        # Should handle zero price gracefully
        self.assertEqual(position_sizes["ADA/USDT"], 0.0)
        self.assertGreater(position_sizes["BNB/USDT"], 0.0)


if __name__ == "__main__":
    unittest.main()
