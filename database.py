import logging
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import config

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CryptoPrice(Base):
    __tablename__ = "crypto_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timeframe = Column(String, nullable=False, default="1h")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_symbol_timestamp", "symbol", "timestamp"),)


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def save_price_data(db, symbol, timestamp, open_price, high_price, low_price, close_price, volume, timeframe="1h"):
    try:
        existing = (
            db.query(CryptoPrice)
            .filter(CryptoPrice.symbol == symbol, CryptoPrice.timestamp == timestamp, CryptoPrice.timeframe == timeframe)
            .first()
        )

        if existing:
            existing.open_price = open_price
            existing.high_price = high_price
            existing.low_price = low_price
            existing.close_price = close_price
            existing.volume = volume
        else:
            price_data = CryptoPrice(
                symbol=symbol,
                timestamp=timestamp,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                timeframe=timeframe,
            )
            db.add(price_data)

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error saving price data: {e}")
        raise


def get_price_data(db, symbol, start_date=None, end_date=None, timeframe="1h", limit=None):
    query = db.query(CryptoPrice).filter(CryptoPrice.symbol == symbol, CryptoPrice.timeframe == timeframe)

    if start_date:
        query = query.filter(CryptoPrice.timestamp >= start_date)
    if end_date:
        query = query.filter(CryptoPrice.timestamp <= end_date)

    query = query.order_by(CryptoPrice.timestamp.desc())

    if limit:
        query = query.limit(limit)

    return query.all()


def get_latest_price(db, symbol, timeframe="1h"):
    return (
        db.query(CryptoPrice)
        .filter(CryptoPrice.symbol == symbol, CryptoPrice.timeframe == timeframe)
        .order_by(CryptoPrice.timestamp.desc())
        .first()
    )


def get_symbols(db):
    return [row[0] for row in db.query(CryptoPrice.symbol).distinct()]
