import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration settings."""

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/crypto_data")

    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "./cache"))

    DEFAULT_SYMBOLS: list[str] = os.getenv("DEFAULT_SYMBOLS", "BTC/USDT,ETH/USDT,ADA/USDT,BNB/USDT,SOL/USDT").split(",")

    DEFAULT_TIMEFRAME: str = "1h"
    MAX_HISTORICAL_DAYS: int = 365

    # Live Pair Trading Configuration

    # Trading pairs
    SYMBOL1: str = "ADA/USDT"
    SYMBOL2: str = "BNB/USDT"

    # Capital and risk management
    INITIAL_CAPITAL: float = 1000.0  # Starting capital in USDT
    MAX_POSITION_SIZE: float = 0.5  # Maximum 50% of capital per position

    # Strategy parameters
    LOOKBACK_PERIOD: int = 20  # Period for calculating z-score (20 minutes)
    Z_THRESHOLD: float = 2.0  # Z-score threshold for trading signals
    MIN_SPREAD_STD: float = 0.001  # Minimum spread standard deviation to trade

    # Trading settings
    PAPER_TRADING: bool = True  # Safe mode: no real trading
    UPDATE_INTERVAL: int = 60  # Update every 60 seconds
    MAX_TRADES_PER_DAY: int = 10  # Maximum trades per day to avoid overtrading

    # Exchange settings
    EXCHANGE: str = "binanceus"  # Exchange to use
    SANDBOX: bool = True  # Use sandbox/testnet

    # Logging
    LOG_FILE: str = "pair_trading.log"

    # Performance tracking
    TRACK_PERFORMANCE: bool = True
    SAVE_TRADES: bool = True
    GENERATE_REPORTS: bool = True

    # Risk management
    STOP_LOSS_PCT: float = 0.05  # 5% stop loss
    TAKE_PROFIT_PCT: float = 0.10  # 10% take profit
    MAX_DRAWDOWN_PCT: float = 0.20  # 20% maximum drawdown

    # Notification settings
    ENABLE_NOTIFICATIONS: bool = False
    NOTIFICATION_EMAIL: str = ""
    NOTIFICATION_WEBHOOK: str = ""

    # Advanced settings
    USE_DYNAMIC_THRESHOLD: bool = False  # Adjust z-threshold based on volatility
    VOLATILITY_LOOKBACK: int = 30  # Period for volatility calculation
    CORRELATION_THRESHOLD: float = 0.7  # Minimum correlation to trade

    @classmethod
    def create_directories(cls):
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)


config = Config()
