#!/usr/bin/env python3
"""
Example script demonstrating the crypto data analysis application.

This script shows how to:
1. Collect historical data from Binance
2. Store data in PostgreSQL
3. Analyze trends and correlations
4. Generate visualizations
"""

import logging

from analyzer import CryptoAnalyzer
from data_collector import BinanceDataCollector
from database import get_db, get_symbols, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_database():
    """Initialize the database."""
    logger.info("Setting up database...")
    init_db()
    logger.info("Database setup complete")


def collect_sample_data():
    """Collect sample data for demonstration."""
    logger.info("Collecting sample data...")

    # Initialize collector
    collector = BinanceDataCollector()

    # Sample symbols to collect
    symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]

    # Collect 7 days of hourly data
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
    """Analyze the collected data."""
    logger.info("Analyzing data...")

    # Initialize analyzer
    analyzer = CryptoAnalyzer()

    # Get symbols from database
    db = next(get_db())
    symbols = get_symbols(db)
    db.close()

    if not symbols:
        logger.warning("No symbols found in database")
        return

    # Generate summary statistics
    logger.info("Generating summary statistics...")
    for symbol in symbols[:3]:  # Analyze first 3 symbols
        stats = analyzer.generate_summary_statistics(symbol, days_back=7)
        if stats:
            print(f"\n{symbol} Statistics:")
            print(f"  Current Price: ${stats['current_price']:,.2f}")
            print(f"  Total Change: {stats['price_change_total']:+.2f}%")
            print(f"  Volatility: {stats['price_change_std']:.2f}%")
            print(f"  Total Volume: {stats['total_volume']:,.0f}")

    # Generate correlation matrix
    logger.info("Calculating correlations...")
    correlation_matrix = analyzer.calculate_correlation_matrix(symbols[:5], days_back=7)
    if not correlation_matrix.empty:
        print("\nCorrelation Matrix:")
        print(correlation_matrix.round(3))

    # Compare performance
    logger.info("Comparing performance...")
    comparison_df = analyzer.compare_symbols(symbols[:5], days_back=7)
    if not comparison_df.empty:
        print("\nPerformance Comparison:")
        print(
            comparison_df[
                ["price_change_total", "price_change_std", "average_volume"]
            ].round(2)
        )


def generate_charts():
    """Generate sample charts."""
    logger.info("Generating charts...")

    # Initialize analyzer
    analyzer = CryptoAnalyzer()

    # Generate chart for Bitcoin
    try:
        logger.info("Generating BTC/USDT chart...")
        analyzer.plot_price_chart(
            symbol="BTC/USDT",
            days_back=7,
            timeframe="1h",
            include_indicators=True,
            save_path="btc_sample_chart.html",
        )
        logger.info("✓ BTC chart saved to btc_sample_chart.html")
    except Exception as e:
        logger.error(f"Error generating BTC chart: {e}")

    # Generate correlation heatmap
    try:
        logger.info("Generating correlation heatmap...")
        symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "BNB/USDT"]
        analyzer.plot_correlation_heatmap(
            symbols=symbols,
            days_back=7,
            timeframe="1h",
            save_path="correlation_sample.html",
        )
        logger.info("✓ Correlation heatmap saved to correlation_sample.html")
    except Exception as e:
        logger.error(f"Error generating correlation heatmap: {e}")


def main():
    """Main function to run the complete example."""
    print("🚀 Crypto Data Analysis Example")
    print("=" * 50)

    try:
        # Step 1: Setup
        setup_database()

        # Step 2: Collect data
        collect_sample_data()

        # Step 3: Analyze data
        analyze_data()

        # Step 4: Generate charts
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
