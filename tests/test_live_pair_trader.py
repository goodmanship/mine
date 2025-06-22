import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

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


if __name__ == "__main__":
    unittest.main()
