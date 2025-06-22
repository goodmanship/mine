# 🚀 Live Pair Trading System

A real-time pair trading system for crypto assets, specifically optimized for ADA/BNB pair trading based on our backtesting results.

## 📊 Backtesting Results

Our comprehensive backtesting showed:
- **ADA/BNB**: +94.74% return vs +43.25% buy & hold (**+51.48% excess return!**)
- **BTC/BNB**: +54.65% return vs +38.51% buy & hold (+16.14% excess return)
- **BTC/ADA**: +66.16% return vs +69.80% buy & hold (-3.64% excess return)
- **ETH/BTC**: +11.29% return vs +19.89% buy & hold (-8.60% excess return)

## 🎯 Features

- **Real-time price monitoring** from Binance US
- **Paper trading mode** (safe testing)
- **Mean reversion strategy** based on z-score
- **Automatic position management**
- **Performance tracking** and logging
- **State persistence** (resume after interruption)
- **Risk management** features
- **Live chart display**

## 🛠️ Setup

### 1. Install Dependencies

```bash
# Install required packages
uv add ccxt pandas numpy asyncio
```

### 2. Configure API Keys (Optional for Paper Trading)

For paper trading, no API keys are needed. For real trading:

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_SECRET="your_secret_key_here"
```

### 3. Configure Trading Parameters

Edit `trading_config.py` to customize:

```python
# Trading pairs
SYMBOL1 = 'ADA/USDT'
SYMBOL2 = 'BNB/USDT'

# Capital and risk management
INITIAL_CAPITAL = 1000.0  # Starting capital
Z_THRESHOLD = 2.0         # Z-score threshold
LOOKBACK_PERIOD = 20      # Period for z-score calculation

# Trading settings
PAPER_TRADING = True      # Set to False for real trading
UPDATE_INTERVAL = 60      # Update every 60 seconds
```

## 🚀 Usage

### Start Paper Trading

```bash
# Start the trading system
uv run python start_trading.py
```

### Monitor Trading

The system will display real-time status:

```
============================================================
LIVE PAIR TRADING STATUS - 2024-01-15 14:30:25
============================================================
Symbols: ADA/USDT vs BNB/USDT
Current Prices: ADA/USDT: $0.4523, BNB/USDT: $312.45
Z-Score: 2.156
Signal: -1 (Short)
Current Position: -1
Portfolio Value: $1,047.32
P&L: +$47.32 (+4.73%)
Total Trades: 3
Cash: $0.00
Positions: {'ADA/USDT': -2210.5, 'BNB/USDT': 3.35}
============================================================
```

### Stop Trading

Press `Ctrl+C` to stop the system. The current state will be saved automatically.

## 📈 Strategy Details

### Mean Reversion Logic

1. **Calculate Spread**: Log difference between ADA and BNB prices
2. **Z-Score**: Compare current spread to historical average
3. **Trading Signals**:
   - Z-Score > 2.0: Short spread (sell ADA, buy BNB)
   - Z-Score < -2.0: Long spread (buy ADA, sell BNB)
   - Otherwise: Neutral (no position)

### Position Management

- **Equal Capital Allocation**: 50% of capital per asset
- **Automatic Rebalancing**: Positions adjusted on each signal
- **Paper Trading**: No real money at risk

## 📊 Performance Tracking

The system tracks:
- **Total Return**: Overall performance
- **P&L**: Profit and loss
- **Trade Count**: Number of trades executed
- **Win Rate**: Percentage of profitable trades
- **Portfolio Value**: Current total value

## 🔧 Configuration Options

### Strategy Parameters

```python
LOOKBACK_PERIOD = 20      # Historical data for z-score
Z_THRESHOLD = 2.0         # Signal threshold
MIN_SPREAD_STD = 0.001    # Minimum volatility to trade
```

### Risk Management

```python
STOP_LOSS_PCT = 0.05      # 5% stop loss
TAKE_PROFIT_PCT = 0.10    # 10% take profit
MAX_DRAWDOWN_PCT = 0.20   # 20% maximum drawdown
MAX_TRADES_PER_DAY = 10   # Prevent overtrading
```

### Trading Settings

```python
PAPER_TRADING = True      # Safe testing mode
UPDATE_INTERVAL = 60      # Check every minute
EXCHANGE = 'binanceus'    # Use Binance US
```

## 📁 File Structure

```
├── live_pair_trader.py      # Main trading system
├── start_trading.py         # Launcher script
├── trading_config.py        # Configuration file
├── trading_state.json       # Saved state (auto-generated)
├── pair_trading.log         # Trading logs (auto-generated)
└── LIVE_TRADING_README.md   # This file
```

## ⚠️ Important Notes

### Paper Trading Mode
- **Default**: Paper trading is enabled
- **No Risk**: No real money is traded
- **Testing**: Perfect for strategy validation

### Real Trading Mode
- **Dangerous**: Set `PAPER_TRADING = False` in config
- **API Keys**: Must set Binance API keys
- **Confirmation**: System will ask for confirmation
- **Risk**: Real money will be traded!

### Performance Expectations
- **Historical**: ADA/BNB showed +51% excess return
- **Future**: Past performance doesn't guarantee future results
- **Volatility**: Crypto markets are highly volatile
- **Risk**: Always start with paper trading

## 🔍 Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Check internet connection
   - Verify Binance US is accessible
   - Check API key permissions

2. **No Trading Signals**
   - Increase `Z_THRESHOLD` for fewer signals
   - Decrease `LOOKBACK_PERIOD` for more sensitivity
   - Check if spread volatility is sufficient

3. **High Trade Frequency**
   - Increase `Z_THRESHOLD`
   - Increase `LOOKBACK_PERIOD`
   - Set `MAX_TRADES_PER_DAY` limit

### Logs and Debugging

- Check `pair_trading.log` for detailed logs
- Set `LOG_LEVEL = 'DEBUG'` for verbose output
- Monitor `trading_state.json` for current state

## 🎯 Next Steps

1. **Start Paper Trading**: Run the system in paper mode
2. **Monitor Performance**: Watch for consistent results
3. **Adjust Parameters**: Fine-tune based on performance
4. **Consider Real Trading**: Only after extensive paper trading success

## 📞 Support

For issues or questions:
- Check the logs in `pair_trading.log`
- Review configuration in `trading_config.py`
- Ensure all dependencies are installed

---

**Remember**: Always start with paper trading and only move to real trading after thorough testing and understanding of the risks involved!

## Live Chart Feature 📈

The system now includes a **comprehensive real-time chart display** that updates every minute alongside the trading algorithm. The chart shows both statistical analysis and underlying price movements.

### Chart Layout:
The display consists of **two synchronized subplots** sharing the same time axis:

#### 🔝 **Top Chart: Z-Score Analysis**
- **Z-Score Line**: Blue line showing the current spread z-score over time
- **Threshold Lines**: Red dashed lines at +/- z_threshold showing trading triggers
- **Trade Markers**: 
  - 🟢 **Green triangles (▲)**: Long spread trades (buy symbol1, sell symbol2)
  - 🔴 **Red triangles (▼)**: Short spread trades (sell symbol1, buy symbol2)

#### 🔽 **Bottom Chart: Price Movements**
- **Symbol1 Price**: Green line showing price movements of your first trading symbol
- **Symbol2 Price**: Orange line showing price movements of your second trading symbol
- **Shared Time Axis**: Perfectly aligned with z-score chart for correlation analysis

### 💡 What You Can See:
- **Trade Timing**: Exact correlation between z-score thresholds and trade execution
- **Price Relationships**: How individual asset prices create the spread dynamics
- **Mean Reversion**: Visual confirmation of prices returning to historical relationship
- **Market Patterns**: Identify trending vs. ranging market conditions
- **Strategy Performance**: See how price movements affect your positions

### 🎯 Key Insights:
- **Spread Convergence**: Watch prices converge/diverge in real-time
- **Volatility Patterns**: Identify high/low volatility periods
- **Correlation Breaks**: Spot when normal price relationships break down
- **Entry/Exit Timing**: See optimal trade timing in historical context

### Example Scenarios:
1. **Strong Signal**: Z-score hits -2.5 → prices show clear divergence → algorithm buys the spread
2. **Mean Reversion**: After trade, watch prices gradually return to normal relationship
3. **False Signals**: See when z-score triggers but prices continue trending (rare but important to spot)

### Technical Details:
- **Update Frequency**: Both charts refresh every 60 seconds
- **History**: Displays last 100 data points (≈ 1.7 hours of data)
- **Scaling**: Automatic scaling for optimal visibility of both price ranges
- **Performance**: Optimized for smooth real-time updates 