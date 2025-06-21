"""Configuration management for the crypto data analysis application."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://localhost:5432/crypto_data"
    )

    # Binance API (optional - for higher rate limits)
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")

    # Application settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "./cache"))

    # Default symbols to track
    DEFAULT_SYMBOLS: list[str] = os.getenv(
        "DEFAULT_SYMBOLS", "BTC/USDT,ETH/USDT,ADA/USDT,BNB/USDT,SOL/USDT"
    ).split(",")

    # Data collection settings
    DEFAULT_TIMEFRAME: str = "1h"  # 1 hour candles
    MAX_HISTORICAL_DAYS: int = 365  # Maximum days of historical data to fetch

    @classmethod
    def create_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)


# Global config instance
config = Config()
