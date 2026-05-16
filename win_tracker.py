"""Win Rate Tracker for Quant Bot.

How it works:
1. Every time someone analyzes a stock, we save the prediction
2. A background job runs daily and checks if predictions were correct
3. The /accuracy page shows the results
"""

import os
import threading
import time
from datetime import datetime, timedelta

import yfinance as yf

from database import (
    save_prediction,
    get_pending_predictions,
    update_prediction_outcome,
    get_accuracy_stats,
    get_all_symbols_accuracy,
)


# ─── Step 1: Save prediction after every analysis ────────────────────────────

def record_prediction(symbol, analysis_result):
    """
    Call this right after your analyze route finishes.
    Pulls the relevant fields out of your existing result dict and saves them.
    
    Usage in app.py:
        from win_tracker import record_prediction
        record_prediction(symbol, cleaned_result)
    """
    try:
        ml = analysis_result.get("ml_prediction", {})
        rec = analysis_result.get("recommendation", {})
        quote = analysis_result.get("quote", {})

        predicted_direction = ml.get("direction", "UNKNOWN")  # 'UP' or 'DOWN'
        predicted_move_pct = ml.get("expected_move")           # e.g. -1.65
        confidence = ml.get("confidence", "LOW")               # 'HIGH','MEDIUM','LOW'
        recommendation = rec.get("action", "HOLD")             # 'BUY','SELL','HOLD'
        price_at_prediction = quote.get("price", 0)

        # Check date = next trading day (we just use tomorrow, close enough)
        check_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        save_prediction(
            symbol=symbol,
            predicted_direction=predicted_direction,
            predicted_move_pct=predicted_move_pct,
            confidence=confidence,
            recommendation=recommendation,
            price_at_prediction=price_at_prediction,
            check_date=check_date,
        )
        print(f"✅ Prediction saved for {symbol}: {predicted_direction} @ ${price_at_prediction}")

    except Exception as e:
        print(f"⚠️ Could not save prediction for {symbol}: {e}")


# ─── Step 2: Background job that checks outcomes daily ───────────────────────

def check_pending_outcomes():
    """
    Runs in background. Checks all unresolved predictions where check_date has passed.
    Fetches actual next-day price from yfinance and marks correct/wrong.
    """
    pending = get_pending_predictions()

    if not pending:
        print("📊 No pending predictions to check.")
        return

    print(f"📊 Checking {len(pending)} pending predictions...")

    for pred in pending:
        try:
            symbol = pred["symbol"]
            price_at_prediction = pred["price_at_prediction"]
            predicted_direction = pred["predicted_direction"]
            check_date = pred["check_date"]

            # Fetch actual price on check_date using yfinance
            check_dt = datetime.strptime(check_date, "%Y-%m-%d")
            end_dt = check_dt + timedelta(days=3)  # buffer for weekends/holidays

            ticker = yf.Ticker(symbol)
            hist = ticker.history(
                start=check_date,
                end=end_dt.strftime("%Y-%m-%d")
            )

            if hist.empty:
                print(f"⚠️ No data for {symbol} on {check_date}, skipping.")
                continue

            actual_price = float(hist["Close"].iloc[0])
            actual_direction = "UP" if actual_price >= price_at_prediction else "DOWN"
            was_correct = actual_direction == predicted_direction

            update_prediction_outcome(
                prediction_id=pred["id"],
                actual_price=actual_price,
                actual_direction=actual_direction,
                was_correct=was_correct,
            )

            result_emoji = "✅" if was_correct else "❌"
            print(f"{result_emoji} {symbol}: predicted {predicted_direction}, "
                  f"actual {actual_direction} (${price_at_prediction:.2f} → ${actual_price:.2f})")

        except Exception as e:
            print(f"⚠️ Error checking {pred['symbol']}: {e}")


def start_background_checker(interval_hours=6):
    """
    Starts a background thread that checks outcomes every N hours.
    Call this once when your Flask app starts.
    
    Usage in app.py:
        from win_tracker import start_background_checker
        start_background_checker()
    """
    def loop():
        while True:
            try:
                check_pending_outcomes()
            except Exception as e:
                print(f"⚠️ Background checker error: {e}")
            time.sleep(interval_hours * 3600)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    print(f"🔄 Background outcome checker started (every {interval_hours}h)")


# ─── Step 3: Data for the /accuracy page ─────────────────────────────────────

def get_accuracy_data():
    """
    Returns everything needed to render the /accuracy page.
    Call this in your accuracy Flask route.
    """
    overall = get_accuracy_stats()          # overall win rate
    by_symbol = get_all_symbols_accuracy()  # per-stock breakdown
    recent = overall.get("history", [])[:20]  # last 20 predictions

    # Direction breakdown
    up_preds = [r for r in overall.get("history", []) if r["predicted_direction"] == "UP"]
    down_preds = [r for r in overall.get("history", []) if r["predicted_direction"] == "DOWN"]

    up_correct = sum(1 for r in up_preds if r["was_correct"] == 1)
    down_correct = sum(1 for r in down_preds if r["was_correct"] == 1)

    return {
        "overall": {
            "total": overall["total"],
            "correct": overall["correct"],
            "win_rate": overall["win_rate"],
        },
        "by_direction": {
            "up": {
                "total": len(up_preds),
                "correct": up_correct,
                "win_rate": round(up_correct / len(up_preds) * 100, 1) if up_preds else 0,
            },
            "down": {
                "total": len(down_preds),
                "correct": down_correct,
                "win_rate": round(down_correct / len(down_preds) * 100, 1) if down_preds else 0,
            },
        },
        "by_symbol": by_symbol,
        "recent_predictions": recent,
    }
