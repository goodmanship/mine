#!/usr/bin/env python3
import logging
from datetime import datetime, timedelta

from src.analyze.analyzer import CryptoAnalyzer
from src.core.database import get_db_session, get_symbols, init_db
from src.data.data_collector import BinanceDataCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_database():
    logger.info("Setting up database...")
    init_db()
    logger.info("Database setup complete")


def collect_sample_data():
    logger.info("Collecting sample data...")

    collector = BinanceDataCollector()

    symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]

    for symbol in symbols:
        logger.info(f"Collecting data for {symbol}...")
        try:
            df = collector.fetch_historical_data(symbol, "1h", 7)
            if not df.empty:
                collector.save_to_database(symbol, df, "1h")
                logger.info(f"✓ Collected {len(df)} records for {symbol}")
            else:
                logger.warning(f"No data found for {symbol}")
        except Exception as e:
            logger.error(f"Error collecting data for {symbol}: {e}")


def analyze_data():
    logger.info("Analyzing data...")

    analyzer = CryptoAnalyzer()

    with get_db_session() as db:
        symbols = get_symbols(db)

    if not symbols:
        logger.warning("No symbols found in database")
        return

    # Calculate date range for 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    logger.info("Generating summary statistics...")
    for symbol in symbols[:3]:
        stats = analyzer.generate_summary_statistics(symbol, start_date, end_date)
        if stats:
            print(f"\n{symbol} Statistics:")
            print(f"  Current Price: ${stats['latest_price']:,.2f}")
            print(f"  Total Change: {stats['price_change_pct']:+.2f}%")
            print(f"  Volatility: {stats['volatility']:.2f}%")
            print(f"  Total Volume: {stats['24h_volume']:,.0f}")

    logger.info("Calculating correlations...")
    correlation_matrix = analyzer.calculate_correlation_matrix(symbols[:5], start_date, end_date)
    if not correlation_matrix.empty:
        print("\nCorrelation Matrix:")
        print(correlation_matrix.round(3))

    logger.info("Comparing performance...")
    comparison_df = analyzer.compare_symbols(symbols[:5], start_date, end_date)
    if not comparison_df.empty:
        print("\nPerformance Comparison:")
        print(comparison_df[["price_change_pct", "volatility", "24h_volume"]].round(2))


def generate_charts():
    logger.info("Generating charts...")

    analyzer = CryptoAnalyzer()

    # Calculate date range for 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    try:
        logger.info("Generating BTC/USDT chart...")
        analyzer.plot_price_chart(
            symbol="BTC/USDT",
            start_date=start_date,
            end_date=end_date,
            timeframe="1h",
            include_indicators=True,
            save_path="btc_sample_chart.html",
        )
        logger.info("✓ BTC chart saved to btc_sample_chart.html")
    except Exception as e:
        logger.error(f"Error generating BTC chart: {e}")

    try:
        logger.info("Generating correlation heatmap...")
        symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "BNB/USDT"]
        analyzer.plot_correlation_heatmap(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe="1h",
            save_path="correlation_sample.html",
        )
        logger.info("✓ Correlation heatmap saved to correlation_sample.html")
    except Exception as e:
        logger.error(f"Error generating correlation heatmap: {e}")


def main():
    print("🚀 Crypto Data Analysis Example")
    print("=" * 50)

    try:
        setup_database()
        collect_sample_data()
        analyze_data()
        generate_charts()

        print("\n✅ Example completed successfully!")
        print("\nGenerated files:")
        print("  - btc_sample_chart.html (Bitcoin price chart)")
        print("  - correlation_sample.html (Correlation heatmap)")
        print("\nNext steps:")
        print("  - Open the HTML files in your browser to view charts")
        print("  - Run 'python main.py analyze' for more detailed analysis")
        print("  - Run 'python main.py chart --symbol BTC/USDT' for interactive charts")

    except Exception as e:
        logger.error(f"Example failed: {e}")
        print(f"\n❌ Example failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PostgreSQL is running")
        print("  2. Check database connection in config.py")
        print("  3. Verify internet connection for Binance API")
        print("  4. Run 'python main.py setup' to initialize the application")


if __name__ == "__main__":
    main()
