import logging
import time
from datetime import datetime, timedelta
from typing import Any

import ccxt
import pandas as pd
from tqdm import tqdm

from config import config
from database import get_db_session, save_price_data

logger = logging.getLogger(__name__)


class BinanceDataCollector:
    def __init__(self):
        init_dict = {
            "apiKey": config.BINANCE_API_KEY,
            "secret": config.BINANCE_SECRET_KEY,
            "sandbox": False,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
        self.exchange = ccxt.binanceus(init_dict)  # type: ignore

        try:
            self.exchange.load_markets()
            logger.info("Successfully connected to Binance")
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            raise

    def get_available_symbols(self) -> list[str]:
        return list(self.exchange.markets.keys())

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: datetime | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        try:
            since_timestamp = None
            if since:
                since_timestamp = int(since.timestamp() * 1000)

            ohlcv = self.exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=since_timestamp, limit=limit)

            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            return df

        except Exception as e:
            logger.error(f"Error fetching OHLCV data for {symbol}: {e}")
            raise

    def fetch_historical_data(self, symbol: str, timeframe: str = "1h", days_back: int = 30) -> pd.DataFrame:
        since = datetime.now() - timedelta(days=days_back)
        return self.fetch_ohlcv(symbol, timeframe, since=since)

    def save_to_database(self, symbol: str, df: pd.DataFrame, timeframe: str = "1h") -> None:
        with get_db_session() as db:
            try:
                for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Saving {symbol}"):
                    save_price_data(
                        db=db,
                        symbol=symbol,
                        timestamp=row["timestamp"],
                        open_price=row["open"],
                        high_price=row["high"],
                        low_price=row["low"],
                        close_price=row["close"],
                        volume=row["volume"],
                        timeframe=timeframe,
                    )

                logger.info(f"Successfully saved {len(df)} records for {symbol}")

            except Exception as e:
                logger.error(f"Error saving data for {symbol}: {e}")
                raise

    def collect_and_save(self, symbols: list[str], timeframe: str = "1h", days_back: int = 30) -> None:
        logger.info(f"Starting data collection for {len(symbols)} symbols")

        for symbol in symbols:
            try:
                logger.info(f"Collecting data for {symbol}")

                df = self.fetch_historical_data(symbol, timeframe, days_back)

                if df.empty:
                    logger.warning(f"No data found for {symbol}")
                    continue

                self.save_to_database(symbol, df, timeframe)

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue

    def get_latest_prices(self, symbols: list[str]) -> dict[str, float]:
        latest_prices = {}

        for symbol in symbols:
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                latest_prices[symbol] = ticker["last"]
            except Exception as e:
                logger.error(f"Error fetching latest price for {symbol}: {e}")
                latest_prices[symbol] = None

        return latest_prices

    def get_market_info(self, symbol: str) -> dict[str, Any]:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last_price": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "high_24h": ticker["high"],
                "low_24h": ticker["low"],
                "volume_24h": ticker["baseVolume"],
                "change_24h": ticker["percentage"],
                "timestamp": datetime.fromtimestamp(ticker["timestamp"] / 1000),
            }
        except Exception as e:
            logger.error(f"Error fetching market info for {symbol}: {e}")
            raise


def main():
    collector = BinanceDataCollector()

    symbols = config.DEFAULT_SYMBOLS[:3]

    print(f"Collecting data for: {symbols}")
    collector.collect_and_save(symbols, days_back=7)

    latest_prices = collector.get_latest_prices(symbols)
    print("Latest prices:")
    for symbol, price in latest_prices.items():
        print(f"  {symbol}: ${price:,.2f}" if price else f"  {symbol}: N/A")


if __name__ == "__main__":
    main()
