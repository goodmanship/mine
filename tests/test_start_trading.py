import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Mock modules before importing
sys.modules["ccxt"] = MagicMock()
sys.modules["ccxt.base"] = MagicMock()
sys.modules["ccxt.base.types"] = MagicMock()
sys.modules["src.core.database"] = MagicMock()

from src.trade.start_trading import check_prerequisites, get_user_confirmation, main, print_banner  # noqa: E402


class TestStartTrading(unittest.TestCase):
    """Test cases for start_trading.py functionality."""

    @patch("src.trade.start_trading.config")
    @patch("builtins.print")
    def test_print_banner(self, mock_print, mock_config):
        """Test banner printing functionality."""
        mock_config.SYMBOL1 = "ADA/USDT"
        mock_config.SYMBOL2 = "BNB/USDT"
        mock_config.INITIAL_CAPITAL = 1000.0
        mock_config.PAPER_TRADING = True
        mock_config.UPDATE_INTERVAL = 60
        mock_config.Z_THRESHOLD = 2.0
        mock_config.LOOKBACK_PERIOD = 20

        print_banner()

        # Verify print was called multiple times for banner
        self.assertGreater(mock_print.call_count, 5)

        # Check that configuration values are included in output
        printed_output = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
        self.assertIn("ADA/USDT", printed_output)
        self.assertIn("BNB/USDT", printed_output)
        self.assertIn("1,000.00", printed_output)

    @patch("src.core.database.get_price_data")
    @patch("src.core.database.get_db_session")
    @patch("builtins.print")
    def test_check_prerequisites_success(self, mock_print, mock_get_db_session, mock_get_price_data):
        """Test successful prerequisite checking."""
        # Mock database session
        mock_session = Mock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        # Mock price data
        mock_get_price_data.side_effect = [
            [{"timestamp": "2023-01-01", "close": 0.5}],  # ADA data
            [{"timestamp": "2023-01-01", "close": 500.0}],  # BNB data
        ]

        result = check_prerequisites()

        self.assertTrue(result)
        # Called twice: connection check + data check
        self.assertEqual(mock_get_db_session.call_count, 2)

    @patch("src.core.database.get_db_session")
    @patch("builtins.print")
    def test_check_prerequisites_database_error(self, mock_print, mock_get_db_session):
        """Test prerequisite checking with database connection error."""
        # Mock database connection failure
        mock_get_db_session.side_effect = Exception("Connection failed")

        result = check_prerequisites()

        self.assertFalse(result)
        # Verify error message was printed
        printed_output = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
        self.assertIn("Database connection failed", printed_output)

    @patch("src.trade.start_trading.config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_get_user_confirmation_paper_trading_auto_proceed(self, mock_print, mock_input, mock_config):
        """Test that paper trading auto-proceeds without user input."""
        mock_config.SYMBOL1 = "ADA/USDT"
        mock_config.SYMBOL2 = "BNB/USDT"
        mock_config.INITIAL_CAPITAL = 1000.0
        mock_config.PAPER_TRADING = True  # Paper trading
        mock_config.Z_THRESHOLD = 2.0
        mock_config.UPDATE_INTERVAL = 60

        result = get_user_confirmation()

        # Should auto-proceed for paper trading
        self.assertTrue(result)
        # Should NOT prompt for input in paper trading mode
        mock_input.assert_not_called()

        # Verify paper trading message was displayed
        printed_output = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
        self.assertIn("PAPER TRADING MODE", printed_output)
        self.assertIn("Auto-proceeding (paper trading is safe)", printed_output)
        self.assertIn("Proceeding with paper trading", printed_output)

    @patch("src.trade.start_trading.config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_get_user_confirmation_real_trading_yes(self, mock_print, mock_input, mock_config):
        """Test user confirmation with 'yes' response for real trading."""
        mock_config.SYMBOL1 = "ADA/USDT"
        mock_config.SYMBOL2 = "BNB/USDT"
        mock_config.INITIAL_CAPITAL = 1000.0
        mock_config.PAPER_TRADING = False  # Real trading
        mock_config.Z_THRESHOLD = 2.0
        mock_config.UPDATE_INTERVAL = 60

        mock_input.return_value = "yes"

        result = get_user_confirmation()

        self.assertTrue(result)
        # Should prompt for real trading confirmation
        mock_input.assert_called_once()

        # Check the prompt text
        call_args = mock_input.call_args[0][0]
        self.assertIn("Are you sure you want to trade with real money?", call_args)

        # Verify real trading warnings were displayed
        printed_output = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
        self.assertIn("REAL TRADING MODE", printed_output)
        self.assertIn("REAL MONEY WILL BE USED", printed_output)

    @patch("src.trade.start_trading.config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_get_user_confirmation_real_trading_no(self, mock_print, mock_input, mock_config):
        """Test user confirmation with 'no' response for real trading."""
        mock_config.SYMBOL1 = "ADA/USDT"
        mock_config.SYMBOL2 = "BNB/USDT"
        mock_config.INITIAL_CAPITAL = 1000.0
        mock_config.PAPER_TRADING = False  # Real trading
        mock_config.Z_THRESHOLD = 2.0
        mock_config.UPDATE_INTERVAL = 60

        mock_input.return_value = "no"

        result = get_user_confirmation()

        self.assertFalse(result)
        # Should prompt for real trading confirmation
        mock_input.assert_called_once()

    @patch("src.trade.start_trading.config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_get_user_confirmation_real_trading_various_responses(self, mock_print, mock_input, mock_config):
        """Test various user responses for real trading confirmation."""
        mock_config.SYMBOL1 = "ADA/USDT"
        mock_config.SYMBOL2 = "BNB/USDT"
        mock_config.INITIAL_CAPITAL = 1000.0
        mock_config.PAPER_TRADING = False  # Real trading
        mock_config.Z_THRESHOLD = 2.0
        mock_config.UPDATE_INTERVAL = 60

        # Test various positive responses
        for response in ["yes", "y", "YES", "Y"]:
            with self.subTest(response=response):
                mock_input.return_value = response
                result = get_user_confirmation()
                self.assertTrue(result, f"Should return True for response: {response}")

        # Test various negative responses
        for response in ["no", "n", "NO", "N", "maybe", "", "quit"]:
            with self.subTest(response=response):
                mock_input.return_value = response
                result = get_user_confirmation()
                self.assertFalse(result, f"Should return False for response: {response}")

    @patch("src.trade.start_trading.asyncio")
    @patch("src.trade.start_trading.time.sleep")
    @patch("src.trade.start_trading.LivePairTrader")
    @patch("src.trade.start_trading.get_user_confirmation")
    @patch("src.trade.start_trading.check_prerequisites")
    @patch("src.trade.start_trading.print_banner")
    @patch("src.trade.start_trading.config")
    @patch("builtins.print")
    def test_main_success(
        self,
        mock_print,
        mock_config,
        mock_print_banner,
        mock_check_prereq,
        mock_get_confirmation,
        mock_trader_class,
        mock_sleep,
        mock_asyncio,
    ):
        """Test successful main function execution."""
        # Setup mocks
        mock_config.SYMBOL1 = "ADA/USDT"
        mock_config.SYMBOL2 = "BNB/USDT"
        mock_config.INITIAL_CAPITAL = 1000.0
        mock_config.PAPER_TRADING = True
        mock_config.LOOKBACK_PERIOD = 20
        mock_config.Z_THRESHOLD = 2.0
        mock_config.UPDATE_INTERVAL = 60

        mock_check_prereq.return_value = True
        mock_get_confirmation.return_value = True

        mock_trader = Mock()
        mock_trader_class.return_value = mock_trader

        main()

        # Verify function calls
        mock_print_banner.assert_called_once()
        mock_check_prereq.assert_called_once()
        mock_get_confirmation.assert_called_once()
        mock_trader_class.assert_called_once()
        mock_trader.load_state.assert_called_once()
        mock_asyncio.run.assert_called_once()

    @patch("src.trade.start_trading.check_prerequisites")
    @patch("src.trade.start_trading.print_banner")
    @patch("builtins.print")
    def test_main_prerequisites_failed(self, mock_print, mock_print_banner, mock_check_prereq):
        """Test main function when prerequisites fail."""
        mock_check_prereq.return_value = False

        main()

        # Verify early return
        mock_print_banner.assert_called_once()
        mock_check_prereq.assert_called_once()

        # Check error message
        printed_output = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
        self.assertIn("Prerequisites not met", printed_output)


if __name__ == "__main__":
    unittest.main()
