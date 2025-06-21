from pathlib import Path

class Config:
    DATABASE_URL: str
    BINANCE_API_KEY: str
    BINANCE_SECRET_KEY: str
    LOG_LEVEL: str
    DATA_DIR: Path
    CACHE_DIR: Path
    DEFAULT_SYMBOLS: list[str]
    DEFAULT_TIMEFRAME: str
    MAX_HISTORICAL_DAYS: int

    @classmethod
    def create_directories(cls) -> None: ...

config: Config
