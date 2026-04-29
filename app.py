"""Flask Web Dashboard for Quant Bot."""

import os
import json
import math
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()


def clean_for_json(obj):
    """Recursively clean an object to handle NaN, Infinity, etc. for JSON serialization."""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj):
            return None
        elif math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (int, str, bool, type(None))):
        return obj
    else:
        return str(obj)

# Add src to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import data_fetcher, analyzer

app = Flask(__name__)


@app.route("/")
def index():
    """Main dashboard page."""
    return render_template("index.html")


@app.route("/analyze/<symbol>")
def analyze_symbol(symbol):
    """Analyze a stock symbol and return results."""
    symbol = symbol.upper()

    try:
        # Fetch data
        daily_data = data_fetcher.get_daily_data(symbol)
        company_info = data_fetcher.get_company_info(symbol)
        quote = data_fetcher.get_quote(symbol)

        # Process data
        df = data_fetcher.parse_to_dataframe(daily_data)
        df = analyzer.add_technical_indicators(df)

        # Generate analysis
        signals = analyzer.generate_signals(df)
        fundamental_analysis = analyzer.analyze_fundamentals(company_info, {})

        # ML prediction
        model, metrics = analyzer.train_price_predictor(df)
        prediction = analyzer.predict_next_day(model, df)

        # Overall recommendation
        recommendation = analyzer.generate_overall_recommendation(
            signals,
            fundamental_analysis,
            prediction
        )

        # Get latest data
        latest = df.iloc[-1].to_dict()
        prev_close = df.iloc[-2]["close"] if len(df) > 1 else latest["close"]
        price_change = latest["close"] - prev_close
        price_change_pct = (price_change / prev_close) * 100

        # Format response
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "quote": {
                "price": latest["close"],
                "change": price_change,
                "change_pct": price_change_pct,
                "volume": latest["volume"],
                "name": company_info.get("Name", symbol),
                "sector": company_info.get("Sector", "N/A"),
                "market_cap": company_info.get("MarketCapitalization", "N/A")
            },
            "technicals": {
                "sma_20": latest.get("sma_20"),
                "sma_50": latest.get("sma_50"),
                "sma_200": latest.get("sma_200"),
                "rsi": latest.get("rsi"),
                "macd": latest.get("macd"),
                "macd_signal": latest.get("macd_signal"),
                "stoch_k": latest.get("stoch_k"),
                "stoch_d": latest.get("stoch_d"),
                "bb_pct": latest.get("bb_pct"),
                "atr": latest.get("atr"),
            },
            "signals": signals,
            "fundamentals": fundamental_analysis,
            "ml_prediction": prediction,
            "model_metrics": {
                "r2": metrics["r2"],
                "mse": metrics["mse"],
                "feature_importance": metrics["importance"].to_dict()
            },
            "recommendation": recommendation,
            "price_levels": {
                "entry_zones": [
                    {"label": "Aggressive", "price": round(latest["close"] * 0.98, 2)},
                    {"label": "Conservative", "price": round(latest.get("sma_20", latest["close"] * 0.95), 2)},
                    {"label": "Deep Value", "price": round(latest.get("sma_50", latest["close"] * 0.90), 2)},
                ],
                "targets": [
                    {"label": "Target 1", "price": round(latest["close"] * 1.05, 2)},
                    {"label": "Target 2", "price": round(latest["close"] * 1.10, 2)},
                    {"label": "Target 3", "price": round(latest["close"] * 1.15, 2)},
                ],
                "stop_losses": [
                    {"label": "Tight", "price": round(latest["close"] * 0.95, 2)},
                    {"label": "Standard", "price": round(latest["close"] * 0.90, 2)},
                    {"label": "ATR-based", "price": round(latest["close"] - 2 * latest.get("atr", latest["close"] * 0.05), 2)},
                ]
            }
        }

        # Clean data for JSON serialization (handle NaN, Infinity)
        cleaned_result = clean_for_json(result)
        return jsonify({"success": True, "data": cleaned_result})

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route("/historical/<symbol>")
def get_historical(symbol):
    """Get historical price data for charting."""
    try:
        daily_data = data_fetcher.get_daily_data(symbol, output_size="compact")
        df = data_fetcher.parse_to_dataframe(daily_data)

        # Return last 90 days for charting
        df = df.tail(90)

        chart_data = {
            "dates": df.index.strftime("%Y-%m-%d").tolist(),
            "close": df["close"].tolist(),
            "volume": df["volume"].tolist(),
        }

        # Add SMA lines
        df = analyzer.add_technical_indicators(df)
        chart_data["sma_20"] = df["sma_20"].tolist()
        chart_data["sma_50"] = df["sma_50"].tolist()

        # Clean data for JSON serialization
        cleaned_chart = clean_for_json(chart_data)
        return jsonify({"success": True, "data": cleaned_chart})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    print("\n  Quant Bot Web Dashboard")
    print("  " + "-" * 21)
    print("  Starting server at http://localhost:5000")
    print("  Press Ctrl+C to stop\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
