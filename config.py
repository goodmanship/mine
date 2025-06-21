import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/crypto_data")

    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
    CACHE_DIR = Path(os.getenv("CACHE_DIR", "./cache"))

    DEFAULT_SYMBOLS = os.getenv("DEFAULT_SYMBOLS", "BTC/USDT,ETH/USDT,ADA/USDT,BNB/USDT,SOL/USDT").split(",")

    DEFAULT_TIMEFRAME = "1h"
    MAX_HISTORICAL_DAYS = 365

    @classmethod
    def create_directories(cls):
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)


config = Config()
