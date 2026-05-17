"""Win Rate Tracker for Quant Bot."""

import threading
import time
from datetime import datetime, timedelta

import yfinance as yf
from database import (
    save_prediction,
    get_pending_predictions,
    update_prediction_outcome,
    get_accuracy_stats,
    get_connection,
)


def record_prediction(symbol, analysis_result):
    """Call this right after your analyze route finishes."""
    try:
        ml = analysis_result.get("ml_prediction", {})
        quote = analysis_result.get("quote", {})

        predicted_direction = ml.get("direction", "UNKNOWN")
        price_at_prediction = quote.get("price", 0)

        # +2 days to avoid same-day and weekend issues
        check_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

        save_prediction(
            symbol=symbol,
            direction=predicted_direction,
            price=price_at_prediction,
            check_date=check_date,
        )
        print(f"✅ Prediction saved for {symbol}: {predicted_direction} @ ${price_at_prediction}")
    except Exception as e:
        print(f"⚠️ Could not save prediction for {symbol}: {e}")


def reschedule_prediction(pred_id, check_date):
    """Push check date forward by 2 days (for weekends/holidays)."""
    check_dt = datetime.strptime(check_date, "%Y-%m-%d")
    new_check = (check_dt + timedelta(days=2)).strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE predictions SET check_date = %s WHERE id = %s",
                (new_check, pred_id)
            )
        conn.commit()
        print(f"📅 Rescheduled prediction {pred_id} from {check_date} to {new_check}")
    except Exception as e:
        print(f"⚠️ Failed to reschedule prediction {pred_id}: {e}")
        conn.rollback()
    finally:
        conn.close()


def check_pending_outcomes():
    """Check all unresolved predictions and mark them correct/wrong."""
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
            check_date = str(pred["check_date"])
            pred_id = pred["id"]

            check_dt = datetime.strptime(check_date, "%Y-%m-%d")
            end_dt = check_dt + timedelta(days=4)

            ticker = yf.Ticker(symbol)
            hist = ticker.history(
                start=check_date,
                end=end_dt.strftime("%Y-%m-%d")
            )

            if hist.empty:
                # No data = weekend or holiday, push forward
                reschedule_prediction(pred_id, check_date)
                continue

            actual_price = float(hist["Close"].iloc[0])
            actual_direction = "UP" if actual_price >= price_at_prediction else "DOWN"
            was_correct = actual_direction == predicted_direction

            update_prediction_outcome(
                prediction_id=pred_id,
                actual_price=actual_price,
                was_correct=was_correct,
            )

            emoji = "✅" if was_correct else "❌"
            print(
                f"{emoji} {symbol}: predicted {predicted_direction}, "
                f"actual {actual_direction} "
                f"(${price_at_prediction:.2f} → ${actual_price:.2f})"
            )

        except Exception as e:
            print(f"⚠️ Error checking {pred.get('symbol', '?')}: {e}")


def start_background_checker(interval_hours=6):
    """Start background thread that checks outcomes every N hours."""
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


def get_accuracy_data():
    """Returns everything needed to render the /accuracy page."""
    stats = get_accuracy_stats()
    overall = stats.get("overall", {})
    by_symbol = stats.get("per_symbol", [])
    recent = stats.get("recent", [])

    history = [r for r in recent if r.get("was_correct") is not None]
    up_preds = [r for r in history if r.get("predicted_direction") == "UP"]
    down_preds = [r for r in history if r.get("predicted_direction") == "DOWN"]
    up_correct = sum(1 for r in up_preds if r.get("was_correct"))
    down_correct = sum(1 for r in down_preds if r.get("was_correct"))

    return {
        "overall": {
            "total": overall.get("total", 0) or 0,
            "correct": overall.get("correct", 0) or 0,
            "win_rate": overall.get("win_rate", 0) or 0,
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
