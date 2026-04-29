"""Technical and Fundamental Analysis Module."""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add comprehensive technical indicators to the dataframe."""
    df = df.copy()

    # Moving Averages
    df["sma_20"] = df["close"].rolling(window=20).mean()
    df["sma_50"] = df["close"].rolling(window=50).mean()
    df["sma_200"] = df["close"].rolling(window=200).mean()
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()

    # MACD
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df["bb_middle"] = df["close"].rolling(window=20).mean()
    bb_std = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
    df["bb_lower"] = df["bb_middle"] - (bb_std * 2)
    df["bb_pct"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    # Stochastic Oscillator
    low_14 = df["low"].rolling(window=14).min()
    high_14 = df["high"].rolling(window=14).max()
    df["stoch_k"] = 100 * (df["close"] - low_14) / (high_14 - low_14)
    df["stoch_d"] = df["stoch_k"].rolling(window=3).mean()

    # ATR (Average True Range)
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df["atr"] = true_range.rolling(window=14).mean()

    # Volume indicators
    df["volume_sma"] = df["volume"].rolling(window=20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_sma"]

    # Price momentum
    df["momentum"] = df["close"] - df["close"].shift(14)
    df["roc"] = ((df["close"] - df["close"].shift(14)) / df["close"].shift(14)) * 100

    return df


def generate_signals(df: pd.DataFrame) -> dict:
    """Generate buy/sell signals based on technical indicators."""
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    signals = {
        "trend": [],
        "momentum": [],
        "volatility": [],
        "volume": [],
    }

    # Trend Signals
    if latest["close"] > latest["sma_20"] > latest["sma_50"]:
        signals["trend"].append(("BULLISH", "Price above SMA20 and SMA50 - uptrend"))
    elif latest["close"] < latest["sma_20"] < latest["sma_50"]:
        signals["trend"].append(("BEARISH", "Price below SMA20 and SMA50 - downtrend"))

    # Golden/Death Cross
    if latest["sma_20"] > latest["sma_50"] and prev["sma_20"] <= prev["sma_50"]:
        signals["trend"].append(("STRONG BUY", "Golden Cross detected!"))
    elif latest["sma_20"] < latest["sma_50"] and prev["sma_20"] >= prev["sma_50"]:
        signals["trend"].append(("STRONG SELL", "Death Cross detected!"))

    # MACD Signals
    if latest["macd"] > latest["macd_signal"] and prev["macd"] <= prev["macd_signal"]:
        signals["momentum"].append(("BUY", "MACD crossed above signal line"))
    elif latest["macd"] < latest["macd_signal"] and prev["macd"] >= prev["macd_signal"]:
        signals["momentum"].append(("SELL", "MACD crossed below signal line"))

    # RSI Signals
    if latest["rsi"] < 30:
        signals["momentum"].append(("OVERSOLD", f"RSI at {latest['rsi']:.1f} - potential bounce"))
    elif latest["rsi"] > 70:
        signals["momentum"].append(("OVERBOUGHT", f"RSI at {latest['rsi']:.1f} - potential pullback"))

    # Bollinger Band Signals
    if latest["bb_pct"] < 0.1:
        signals["volatility"].append(("BUY", "Price near lower Bollinger Band - potential reversal"))
    elif latest["bb_pct"] > 0.9:
        signals["volatility"].append(("SELL", "Price near upper Bollinger Band - potential reversal"))

    # Stochastic Signals
    if latest["stoch_k"] < 20 and latest["stoch_k"] > latest["stoch_d"]:
        signals["momentum"].append(("BUY", "Stochastic oversold with bullish cross"))
    elif latest["stoch_k"] > 80 and latest["stoch_k"] < latest["stoch_d"]:
        signals["momentum"].append(("SELL", "Stochastic overbought with bearish cross"))

    # Volume Signals
    if latest["volume_ratio"] > 2:
        signals["volume"].append(("HIGH_VOLUME", f"Volume {latest['volume_ratio']:.1f}x average"))
    elif latest["volume_ratio"] < 0.5:
        signals["volume"].append(("LOW_VOLUME", f"Volume {latest['volume_ratio']:.1f}x average"))

    return signals


def create_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create features for ML model."""
    df = df.copy()

    # Lag features
    for i in range(1, 6):
        df[f"close_lag_{i}"] = df["close"].shift(i)

    # Return features
    df["return_1d"] = df["close"].pct_change(1)
    df["return_5d"] = df["close"].pct_change(5)
    df["return_10d"] = df["close"].pct_change(10)

    # Volatility features
    df["volatility_5d"] = df["return_1d"].rolling(window=5).std()
    df["volatility_10d"] = df["return_1d"].rolling(window=10).std()

    # Target: next day return
    df["target"] = df["close"].shift(-1).pct_change()

    return df


def train_price_predictor(df: pd.DataFrame) -> tuple:
    """Train a Random Forest model to predict next-day price movement.

    Returns None for model and error message if insufficient data (< 60 samples).
    """
    df = create_ml_features(df).dropna()

    # Need at least 60 samples for meaningful training
    if len(df) < 60:
        return None, {"error": f"Insufficient data for ML ({len(df)} samples, need 60+)"}

    feature_cols = [
        "close", "volume", "sma_20", "sma_50", "rsi", "macd",
        "bb_pct", "stoch_k", "atr", "volume_ratio",
        "close_lag_1", "close_lag_2", "return_1d", "return_5d",
        "volatility_5d"
    ]

    # Filter to available columns
    feature_cols = [c for c in feature_cols if c in df.columns]

    X = df[feature_cols]
    y = df["target"]

    # Train/test split
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Need at least some samples in each set
    if len(X_train) < 10 or len(X_test) < 5:
        return None, {"error": "Insufficient data after train/test split"}

    # Train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Feature importance
    importance = pd.Series(
        model.feature_importances_,
        index=feature_cols
    ).sort_values(ascending=False)

    return model, {"mse": mse, "r2": r2, "importance": importance}


def predict_next_day(model, df: pd.DataFrame) -> dict:
    """Predict next day price movement."""
    latest = df.iloc[[-1]].copy()

    # Create features for prediction
    for i in range(1, 6):
        latest[f"close_lag_{i}"] = df["close"].shift(i).iloc[-1]

    latest["return_1d"] = df["close"].pct_change(1).iloc[-1]
    latest["return_5d"] = df["close"].pct_change(5).iloc[-1]
    latest["volatility_5d"] = df["close"].pct_change(1).rolling(5).std().iloc[-1]

    # Get required features
    feature_cols = [
        "close", "volume", "sma_20", "sma_50", "rsi", "macd",
        "bb_pct", "stoch_k", "atr", "volume_ratio",
        "close_lag_1", "close_lag_2", "return_1d", "return_5d",
        "volatility_5d"
    ]
    feature_cols = [c for c in feature_cols if c in latest.columns]

    prediction = model.predict(latest[feature_cols])[0]

    return {
        "predicted_return": prediction,
        "direction": "UP" if prediction > 0 else "DOWN",
        "confidence": "HIGH" if abs(prediction) > 0.02 else "MEDIUM" if abs(prediction) > 0.01 else "LOW"
    }


def analyze_fundamentals(company_info: dict, income_data: dict) -> dict:
    """Analyze fundamental data."""
    analysis = {}

    # Valuation
    pe_ratio = float(company_info.get("PERatio", 0) or 0)
    peg_ratio = float(company_info.get("PEGRatio", 0) or 0)
    pb_ratio = float(company_info.get("PriceToBookRatio", 0) or 0)

    analysis["valuation"] = {
        "pe_ratio": pe_ratio,
        "peg_ratio": peg_ratio,
        "pb_ratio": pb_ratio,
        "assessment": []
    }

    if 0 < pe_ratio < 15:
        analysis["valuation"]["assessment"].append("Undervalued based on P/E")
    elif pe_ratio > 30:
        analysis["valuation"]["assessment"].append("Potentially overvalued based on P/E")

    if 0 < peg_ratio < 1:
        analysis["valuation"]["assessment"].append("Good value considering growth (PEG < 1)")

    # Profitability
    profit_margin = float(company_info.get("ProfitMargin", 0) or 0)
    operating_margin = float(company_info.get("OperatingMarginTTM", 0) or 0)
    roe = float(company_info.get("ReturnOnEquityTTM", 0) or 0)

    analysis["profitability"] = {
        "profit_margin": profit_margin,
        "operating_margin": operating_margin,
        "roe": roe,
        "assessment": []
    }

    if profit_margin > 0.20:
        analysis["profitability"]["assessment"].append("Excellent profit margins (>20%)")
    elif profit_margin > 0.10:
        analysis["profitability"]["assessment"].append("Healthy profit margins (>10%)")

    if roe > 0.15:
        analysis["profitability"]["assessment"].append("Strong ROE (>15%)")

    # Growth
    revenue_growth = float(company_info.get("QuarterlyRevenueGrowthYOY", 0) or 0)
    earnings_growth = float(company_info.get("QuarterlyEarningsGrowthYOY", 0) or 0)

    analysis["growth"] = {
        "revenue_growth_yoy": revenue_growth,
        "earnings_growth_yoy": earnings_growth,
        "assessment": []
    }

    if revenue_growth > 0.20:
        analysis["growth"]["assessment"].append("Strong revenue growth (>20% YoY)")
    if earnings_growth > 0.20:
        analysis["growth"]["assessment"].append("Strong earnings growth (>20% YoY)")

    # Financial Health
    debt_to_equity = float(company_info.get("DebtToEquity", 0) or 0)
    current_ratio = float(company_info.get("CurrentRatio", 0) or 0)

    analysis["financial_health"] = {
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "assessment": []
    }

    if debt_to_equity < 0.5:
        analysis["financial_health"]["assessment"].append("Low debt levels")
    elif debt_to_equity > 2:
        analysis["financial_health"]["assessment"].append("High debt levels - monitor closely")

    if current_ratio > 1.5:
        analysis["financial_health"]["assessment"].append("Good liquidity")
    elif current_ratio < 1:
        analysis["financial_health"]["assessment"].append("Low liquidity - potential concern")

    return analysis


def generate_overall_recommendation(
    technical_signals: dict,
    fundamental_analysis: dict,
    ml_prediction: dict
) -> dict:
    """Generate overall buy/sell/hold recommendation."""
    score = 0
    reasons = []

    # Technical analysis scoring
    for category, signals in technical_signals.items():
        for signal_type, _ in signals:
            if "BUY" in signal_type or "BULLISH" in signal_type or "OVERSOLD" in signal_type:
                score += 1
                reasons.append(f"Technical: {signal_type}")
            elif "SELL" in signal_type or "BEARISH" in signal_type or "OVERBOUGHT" in signal_type:
                score -= 1
                reasons.append(f"Technical: {signal_type}")

    # Fundamental scoring
    for category, data in fundamental_analysis.items():
        if "assessment" in data:
            for assessment in data["assessment"]:
                if "Undervalued" in assessment or "Strong" in assessment or "Excellent" in assessment or "Good" in assessment or "Low debt" in assessment:
                    score += 0.5
                    reasons.append(f"Fundamental: {assessment}")
                elif "overvalued" in assessment or "concern" in assessment or "High debt" in assessment or "Low liquidity" in assessment:
                    score -= 0.5
                    reasons.append(f"Fundamental: {assessment}")

    # ML prediction scoring
    if ml_prediction["direction"] == "UP":
        score += 1 if ml_prediction["confidence"] == "HIGH" else 0.5
        reasons.append(f"ML predicts {ml_prediction['confidence']} confidence UP move")
    else:
        score -= 1 if ml_prediction["confidence"] == "HIGH" else 0.5
        reasons.append(f"ML predicts {ml_prediction['confidence']} confidence DOWN move")

    # Final recommendation
    if score >= 3:
        recommendation = "STRONG BUY"
    elif score >= 1:
        recommendation = "BUY"
    elif score >= -1:
        recommendation = "HOLD"
    elif score >= -3:
        recommendation = "SELL"
    else:
        recommendation = "STRONG SELL"

    return {
        "recommendation": recommendation,
        "score": score,
        "reasons": reasons[:10]  # Top 10 reasons
    }
