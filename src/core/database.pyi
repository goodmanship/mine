from contextlib import AbstractContextManager
from datetime import datetime

from sqlalchemy.orm import Session

class CryptoPrice:
    id: int
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    timeframe: str
    created_at: datetime

def get_db_session() -> AbstractContextManager[Session]: ...
def init_db() -> None: ...
def save_price_data(
    db: Session,
    symbol: str,
    timestamp: datetime,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    timeframe: str = "1h",
) -> None: ...
def get_price_data(
    db: Session,
    symbol: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    timeframe: str = "1h",
    limit: int | None = None,
) -> list[CryptoPrice]: ...
def get_latest_price(db: Session, symbol: str, timeframe: str = "1h") -> CryptoPrice | None: ...
def get_symbols(db: Session) -> list[str]: ...
