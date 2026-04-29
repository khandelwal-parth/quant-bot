# Quant Bot - AI-Powered Stock Analysis System

A comprehensive stock analysis tool that combines technical indicators, fundamental analysis, and machine learning to generate trading signals and recommendations.

## Features

- **Technical Analysis**: RSI, MACD, Moving Averages, Bollinger Bands, Stochastic Oscillator, ATR
- **Fundamental Analysis**: P/E, PEG, Profit Margins, ROE, Growth metrics, Debt levels
- **ML Predictions**: Random Forest model for next-day price movement prediction
- **Trading Signals**: Buy/Sell signals based on multiple indicators
- **Entry/Exit Points**: Suggested entry zones, take-profit targets, and stop-loss levels
- **Dual Interface**: CLI for quick analysis + Web dashboard for deep dives

## Setup

### 1. Get API Key
Get a free Alpha Vantage API key: https://www.alphavantage.co/support/#api-key

### 2. Install Dependencies
```bash
cd quant-bot
pip install -r requirements.txt
```

### 3. Configure API Key
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API key
ALPHAVANTAGE_API_KEY=your_actual_api_key_here
```

## Usage

### CLI Mode
```bash
# Analyze a stock
python -m src.cli AAPL

# Examples
python -m src.cli TSLA
python -m src.cli MSFT
python -m src.cli GOOGL
```

### Web Dashboard
```bash
# Start the web server
python app.py

# Open browser to http://localhost:5000
```

## Output Examples

### CLI Output includes:
- Company overview
- Technical indicators with values
- Trading signals (Buy/Sell/Hold)
- Fundamental analysis
- ML prediction with confidence
- Overall recommendation
- Entry/Exit price levels

### Web Dashboard shows:
- Interactive price chart
- Real-time quote data
- Technical indicator panel
- Signal tags (color-coded)
- Fundamental metrics
- ML prediction details
- Key reasons for recommendation
- Entry/Exit points table

## Project Structure

```
quant-bot/
├── src/
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point
│   ├── cli.py           # CLI interface
│   ├── data_fetcher.py  # Alpha Vantage API client
│   └── analyzer.py      # Technical/Fundamental/ML analysis
├── templates/
│   └── index.html       # Web dashboard
├── static/              # Static assets (if needed)
├── data/                # Cached data (if needed)
├── app.py               # Flask web server
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
└── README.md
```

## Indicators & Signals

### Technical Indicators
| Indicator | Description |
|-----------|-------------|
| SMA 20/50/200 | Simple moving averages for trend |
| EMA 12/26 | Exponential moving averages |
| MACD | Momentum indicator |
| RSI | Overbought/Oversold detector |
| Bollinger Bands | Volatility bands |
| Stochastic | Momentum comparison |
| ATR | Volatility measure |

### Signal Types
- **Trend**: Golden Cross, Death Cross, Price vs SMA
- **Momentum**: MACD crossovers, RSI levels, Stochastic
- **Volatility**: Bollinger Band touches
- **Volume**: Unusual volume detection

### ML Model
- Random Forest Regressor
- Predicts next-day return
- Features: price, volume, indicators, lags, returns
- Reports R² and feature importance

## Disclaimer

This tool is for **educational purposes only**. It is not financial advice. Always do your own research and consult with a qualified financial advisor before making investment decisions.

## License

MIT License - feel free to use and modify.
