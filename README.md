# Crypto Data Analysis Tool

A comprehensive Python application for downloading, storing, and analyzing historical cryptocurrency data from Binance. Built with pandas, PostgreSQL, and interactive visualizations.

## Features

- **Data Collection**: Download historical OHLCV data from Binance using ccxt
- **Database Storage**: Store data in PostgreSQL with efficient indexing
- **Technical Analysis**: Calculate moving averages, RSI, MACD, Bollinger Bands, and more
- **Interactive Charts**: Generate beautiful charts with Plotly
- **Correlation Analysis**: Analyze relationships between different cryptocurrencies
- **CLI Interface**: User-friendly command-line interface with rich output
- **Performance Metrics**: Comprehensive statistics and performance comparisons

## Prerequisites

- Python 3.12+
- PostgreSQL database
- Binance API credentials (optional, for higher rate limits)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd mine
   ```

2. **Install dependencies**:
   ```bash
   make install-dev
   ```

3. **Set up PostgreSQL**:
   - Install PostgreSQL on your system
   - Create a database named `crypto_data`
   - Update the database connection in your environment

4. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your database and API credentials
   ```

## Quick Start with Make Commands

The easiest way to use this application is with the provided Make commands:

1. **Initial setup**:
   ```bash
   make setup
   ```

2. **Collect data**:
   ```bash
   make collect
   ```

3. **Generate charts**:
   ```bash
   make chart SYMBOL=BTC/USDT
   ```

4. **Analyze data**:
   ```bash
   make analyze
   ```

5. **Check status**:
   ```bash
   make status
   ```

## Make Commands Reference

### Basic Commands

```bash
make help                    # Show all available commands
make setup                   # Initial setup for the application
make collect                 # Collect crypto data from Binance
make analyze                 # Analyze collected data
make chart SYMBOL=BTC/USDT   # Generate price charts
make correlation             # Generate correlation heatmap
make status                  # Show application status
```

### Data Collection Options

```bash
# Collect specific symbols
make collect-symbols SYMBOLS="BTC/USDT,ETH/USDT,ADA/USDT"

# Collect for specific number of days
make collect-days DAYS=30

# Collect with specific timeframe
make collect-timeframe TIMEFRAME=1h
```

### Chart Generation Options

```bash
# Generate and save chart to file
make chart-save SYMBOL=ETH/USDT SAVE=eth_chart.html

# Generate chart without technical indicators
make chart-no-indicators SYMBOL=ETH/USDT
```

### Analysis Options

```bash
# Analyze specific symbols
make analyze-symbols SYMBOLS="BTC/USDT,ETH/USDT"

# Analyze data for specific number of days
make analyze-days DAYS=30
```

### Development Commands

```bash
make install                 # Install production dependencies
make install-dev             # Install all dependencies (including dev)
make lint                    # Run ruff linter
make format                  # Format code with ruff
make check                   # Run all code quality checks
make fix                     # Fix code with ruff
make test                    # Run tests
make clean                   # Clean up cache and temporary files
```

### Database Operations

```bash
make db-init                 # Initialize database tables
make db-status               # Check database connection and status
make db-create               # Create PostgreSQL database
```

### Quick Workflows

```bash
make quick-start             # Setup, collect data, and analyze
make dev-setup               # Complete development setup
make dev-check               # Run all development checks
```

## Python Commands (Advanced Usage)

For advanced usage or when you need more control, you can use the Python commands directly:

### Data Collection

```bash
# Collect default symbols (BTC/USDT, ETH/USDT, etc.)
uv run python main.py collect

# Collect specific symbols
uv run python main.py collect --symbols "BTC/USDT,ETH/USDT,ADA/USDT" --days 30

# Collect 1 year of hourly data for Bitcoin
uv run python main.py collect --symbols "BTC/USDT" --days 365 --timeframe 1h
```

### Analysis

```bash
# Analyze all symbols in database
uv run python main.py analyze

# Analyze specific symbols
uv run python main.py analyze --symbols "BTC/USDT,ETH/USDT" --days 7

# Compare performance of top cryptocurrencies
uv run python main.py analyze --days 90
```

### Visualization

```bash
# Interactive chart with technical indicators
uv run python main.py chart --symbol BTC/USDT --days 30

# Save chart to file
uv run python main.py chart --symbol BTC/USDT --save btc_chart.html

# Simple price chart without indicators
uv run python main.py chart --symbol ETH/USDT --days 7 --no-indicators
```

### Correlation Analysis

```bash
# Generate correlation heatmap
uv run python main.py correlation --days 30

# Save correlation matrix
uv run python main.py correlation --save crypto_correlations.html
```

## Example Usage

### Basic Workflow

```bash
# 1. Setup the application
make setup

# 2. Collect data for popular cryptocurrencies
make collect

# 3. Generate a Bitcoin chart
make chart SYMBOL=BTC/USDT

# 4. Analyze the data
make analyze

# 5. Check what symbols are available
make status
```

### Advanced Workflow

```bash
# 1. Collect specific symbols for 30 days
make collect-symbols SYMBOLS="BTC/USDT,ETH/USDT,SOL/USDT" DAYS=30

# 2. Generate and save multiple charts
make chart-save SYMBOL=BTC/USDT SAVE=btc_analysis.html
make chart-save SYMBOL=ETH/USDT SAVE=eth_analysis.html

# 3. Analyze correlations
make correlation

# 4. Check database status
make db-status
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/crypto_data

# Binance API Configuration (optional)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here

# Application Configuration
LOG_LEVEL=INFO
DATA_DIR=./data
CACHE_DIR=./cache

# Default symbols to track
DEFAULT_SYMBOLS=BTC/USDT,ETH/USDT,ADA/USDT,BNB/USDT,SOL/USDT
```

### Database Setup

1. **Install PostgreSQL**:
   ```bash
   # macOS
   brew install postgresql
   
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   ```

2. **Create database**:
   ```bash
   createdb crypto_data
   ```

3. **Update connection string** in your `.env` file

## Technical Indicators

The application calculates the following technical indicators:

- **Moving Averages**: SMA (20, 50), EMA (12, 26)
- **MACD**: MACD line, signal line, histogram
- **RSI**: Relative Strength Index (14-period)
- **Bollinger Bands**: Upper, middle, lower bands
- **Volume Indicators**: Volume SMA, volume ratio
- **Price Metrics**: Price changes, volatility, performance statistics

## Data Structure

### Database Schema

```sql
CREATE TABLE crypto_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open_price FLOAT NOT NULL,
    high_price FLOAT NOT NULL,
    low_price FLOAT NOT NULL,
    close_price FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    timeframe VARCHAR NOT NULL DEFAULT '1h',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_symbol_timestamp ON crypto_prices(symbol, timestamp);
CREATE INDEX idx_symbol ON crypto_prices(symbol);
CREATE INDEX idx_timestamp ON crypto_prices(timestamp);
```

### Supported Timeframes

- `1m` - 1 minute
- `5m` - 5 minutes
- `15m` - 15 minutes
- `1h` - 1 hour
- `4h` - 4 hours
- `1d` - 1 day

## API Reference

### Data Collector

```python
from data_collector import BinanceDataCollector

collector = BinanceDataCollector()

# Fetch historical data
df = collector.fetch_historical_data("BTC/USDT", "1h", 30)

# Get latest prices
prices = collector.get_latest_prices(["BTC/USDT", "ETH/USDT"])

# Save to database
collector.save_to_database("BTC/USDT", df, "1h")
```

### Analyzer

```python
from analyzer import CryptoAnalyzer

analyzer = CryptoAnalyzer()

# Get data as DataFrame
df = analyzer.get_data_as_dataframe("BTC/USDT", days_back=30)

# Calculate technical indicators
df_with_indicators = analyzer.calculate_technical_indicators(df)

# Generate summary statistics
stats = analyzer.generate_summary_statistics("BTC/USDT", days_back=30)

# Create correlation matrix
corr_matrix = analyzer.calculate_correlation_matrix(["BTC/USDT", "ETH/USDT"])
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Ensure PostgreSQL is running
   - Check database credentials in `.env`
   - Verify database `crypto_data` exists

2. **Binance API Errors**:
   - Check internet connection
   - Verify API credentials (if using)
   - Check rate limits

3. **Missing Data**:
   - Some symbols may not have data for certain timeframes
   - Try different time periods or symbols

4. **Chart Not Displaying**:
   - Ensure you have a web browser installed
   - Check if the chart file was saved correctly

### Logging

Enable verbose logging for debugging:

```bash
python main.py --verbose collect
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and research purposes only. Cryptocurrency trading involves significant risk. Always do your own research and consider consulting with financial advisors before making investment decisions.
