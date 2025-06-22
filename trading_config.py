# Live Pair Trading Configuration

# Trading pairs
SYMBOL1 = "ADA/USDT"
SYMBOL2 = "BNB/USDT"

# Capital and risk management
INITIAL_CAPITAL = 1000.0  # Starting capital in USDT
MAX_POSITION_SIZE = 0.5  # Maximum 50% of capital per position

# Strategy parameters
LOOKBACK_PERIOD = 20  # Period for calculating z-score
Z_THRESHOLD = 2.0  # Z-score threshold for trading signals
MIN_SPREAD_STD = 0.001  # Minimum spread standard deviation to trade

# Trading settings
PAPER_TRADING = True  # Set to False for real trading (BE CAREFUL!)
UPDATE_INTERVAL = 60  # Update interval in seconds
MAX_TRADES_PER_DAY = 10  # Maximum trades per day to avoid overtrading

# Exchange settings
EXCHANGE = "binanceus"  # Exchange to use
SANDBOX = True  # Use sandbox/testnet

# Logging
LOG_LEVEL = "INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_FILE = "pair_trading.log"

# Performance tracking
TRACK_PERFORMANCE = True
SAVE_TRADES = True
GENERATE_REPORTS = True

# Risk management
STOP_LOSS_PCT = 0.05  # 5% stop loss
TAKE_PROFIT_PCT = 0.10  # 10% take profit
MAX_DRAWDOWN_PCT = 0.20  # 20% maximum drawdown

# Notification settings
ENABLE_NOTIFICATIONS = False
NOTIFICATION_EMAIL = ""
NOTIFICATION_WEBHOOK = ""

# Advanced settings
USE_DYNAMIC_THRESHOLD = False  # Adjust z-threshold based on volatility
VOLATILITY_LOOKBACK = 30  # Period for volatility calculation
CORRELATION_THRESHOLD = 0.7  # Minimum correlation to trade
