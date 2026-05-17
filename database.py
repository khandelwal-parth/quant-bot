"""Database module using PostgreSQL (Supabase) for persistent storage."""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Use psycopg2 for PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    raise ImportError("psycopg2 not installed. Add 'psycopg2-binary' to requirements.txt")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")


def get_connection():
    """Get a PostgreSQL connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    predicted_direction TEXT NOT NULL,
                    price_at_prediction REAL,
                    actual_next_price REAL,
                    was_correct BOOLEAN,
                    created_at TIMESTAMP DEFAULT NOW(),
                    check_date DATE,
                    checked_at TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alert_log (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()
        logger.info("✅ PostgreSQL database initialized.")
    except Exception as e:
        logger.error(f"❌ DB init error: {e}")
        conn.rollback()
    finally:
        conn.close()


def save_prediction(symbol: str, direction: str, price: float, check_date: str):
    """Save a new prediction to the database."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO predictions (symbol, predicted_direction, price_at_prediction, check_date)
                VALUES (%s, %s, %s, %s)
            """, (symbol.upper(), direction, price, check_date))
        conn.commit()
        logger.info(f"✅ Prediction saved for {symbol}: {direction} @ ${price}")
    except Exception as e:
        logger.error(f"❌ Failed to save prediction: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_pending_predictions():
    """Get all predictions that haven't been verified yet and are due."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM predictions
                WHERE was_correct IS NULL
                AND check_date <= CURRENT_DATE
            """)
            return cur.fetchall()
    except Exception as e:
        logger.error(f"❌ Error fetching pending predictions: {e}")
        return []
    finally:
        conn.close()


def update_prediction_outcome(prediction_id: int, actual_price: float, was_correct: bool):
    """Mark a prediction as correct or incorrect."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE predictions
                SET actual_next_price = %s,
                    was_correct = %s,
                    checked_at = NOW()
                WHERE id = %s
            """, (actual_price, was_correct, prediction_id))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error updating prediction {prediction_id}: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_accuracy_stats():
    """Return overall and per-symbol accuracy stats."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Overall
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN was_correct = TRUE THEN 1 ELSE 0 END) AS correct,
                    SUM(CASE WHEN was_correct = FALSE THEN 1 ELSE 0 END) AS incorrect,
                    SUM(CASE WHEN was_correct IS NULL THEN 1 ELSE 0 END) AS pending
                FROM predictions
                WHERE was_correct IS NOT NULL
            """)
            overall = dict(cur.fetchone())
            overall["total"] = overall["total"] or 0
            overall["correct"] = overall["correct"] or 0
            overall["incorrect"] = overall["incorrect"] or 0
            overall["pending"] = overall["pending"] or 0
            overall["win_rate"] = round((overall["correct"] / overall["total"] * 100), 1) if overall["total"] > 0 else 0

            # Per symbol
            cur.execute("""
                SELECT
                    symbol,
                    COUNT(*) AS total,
                    SUM(CASE WHEN was_correct = TRUE THEN 1 ELSE 0 END) AS correct
                FROM predictions
                WHERE was_correct IS NOT NULL
                GROUP BY symbol
                ORDER BY total DESC
            """)
            per_symbol = []
            for row in cur.fetchall():
                row = dict(row)
                t = row["total"] or 0
                c = row["correct"] or 0
                row["win_rate"] = round((c / t * 100), 1) if t > 0 else 0
                per_symbol.append(row)

            # Recent predictions
            cur.execute("""
                SELECT symbol, predicted_direction, price_at_prediction,
                       actual_next_price, was_correct, created_at
                FROM predictions
                ORDER BY created_at DESC
                LIMIT 20
            """)
            recent = [dict(r) for r in cur.fetchall()]

            return {
                "overall": overall,
                "per_symbol": per_symbol,
                "recent": recent
            }
    except Exception as e:
        logger.error(f"❌ Error fetching accuracy stats: {e}")
        return {"overall": {"total": 0, "correct": 0, "incorrect": 0, "pending": 0, "win_rate": 0}, "per_symbol": [], "recent": []}
    finally:
        conn.close()


def log_alert(symbol: str, alert_type: str):
    """Log a sent alert."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alert_log (symbol, alert_type)
                VALUES (%s, %s)
            """, (symbol.upper(), alert_type))
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Error logging alert: {e}")
        conn.rollback()
    finally:
        conn.close()


def was_alert_sent_recently(symbol: str, alert_type: str, within_hours: int = 6) -> bool:
    """Check if an alert was already sent recently to avoid spam."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) AS cnt FROM alert_log
                WHERE symbol = %s
                AND alert_type = %s
                AND sent_at > NOW() - INTERVAL '%s hours'
            """, (symbol.upper(), alert_type, within_hours))
            result = cur.fetchone()
            return (result["cnt"] or 0) > 0
    except Exception as e:
        logger.error(f"❌ Error checking alert log: {e}")
        return False
    finally:
        conn.close()
# Alias for backwards compatibility
get_all_symbols_accuracy = get_accuracy_stats

# Auto-initialize on import
init_db()

# already defined above, just making sure it's importable
