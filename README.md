# Quant Bot

An AI-powered stock analysis system that delivers institutional-grade analysis in seconds.

## What It Does

Quant Bot analyzes any US stock and provides:

- **Buy/Sell recommendations** with confidence scores
- **Entry and exit points** with specific price levels
- **Technical analysis** (RSI, MACD, Moving Averages, Bollinger Bands)
- **Fundamental analysis** (P/E, PEG, margins, ROE, debt levels)
- **ML price predictions** for next-day movement
- **Risk assessment** with stop-loss suggestions

## Quick Start

### Analyze a stock in seconds:
```bash
python -m src.cli AAPL
```

### Or use the web interface:
```bash
python app.py
# Open http://localhost:5000
```

## Features

| Feature | Description |
|---------|-------------|
| Technical Analysis | 15+ indicators including RSI, MACD, SMA, Bollinger Bands |
| Fundamental Analysis | Valuation, profitability, growth, and financial health metrics |
| ML Predictions | Random Forest model trained on 30+ years of historical data |
| Trading Signals | Clear buy/sell signals with composite scoring |
| Price Targets | Specific entry zones, take-profit levels, and stop-losses |
| Dual Interface | Fast CLI for quick checks, web UI for deep analysis |

## Examples

**CLI:**
```bash
python -m src.cli AAPL
python -m src.cli TSLA
python -m src.cli NVDA
python -m src.cli MSFT
```

**Web Dashboard:**
- Open http://localhost:5000
- Enter any stock symbol
- Get instant analysis with interactive charts

## What You Get

For any stock, Quant Bot tells you:
1. **Should you buy, sell, or hold?** - Clear recommendation
2. **At what price?** - Specific entry zones
3. **When to exit?** - Profit targets and stop-loss levels
4. **Why?** - Key reasons based on technicals, fundamentals, and ML

## Disclaimer

For educational purposes only. Not financial advice. Always do your own research.
