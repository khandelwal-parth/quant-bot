"""Database setup and helpers for Quant Bot."""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quant_bot.db")

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn

def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()

    # --- Win Rate Tracking ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            predicted_direction TEXT NOT NULL,       -- 'UP' or 'DOWN'
            predicted_move_pct REAL,                 -- e.g. -1.65
            confidence TEXT,                         -- 'HIGH', 'MEDIUM', 'LOW'
            recommendation TEXT,                     -- 'BUY', 'SELL', 'HOLD'
            price_at_prediction REAL NOT NULL,
            predicted_at TEXT NOT NULL,              -- ISO datetime
            check_date TEXT,                         -- date to check outcome (next trading day)
            actual_price REAL,                       -- filled in later
            actual_direction TEXT,                   -- 'UP' or 'DOWN' (filled later)
            was_correct INTEGER,                     -- 1 = correct, 0 = wrong (filled later)
            checked_at TEXT                          -- when we checked the outcome
        )
    """)

    # --- Discord Alert Log (so we dont spam the same alert) ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            alert_type TEXT NOT NULL,               -- 'PRICE_TARGET', 'OVERBOUGHT', 'OVERSOLD'
            message TEXT NOT NULL,
            sent_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized at:", DB_PATH)


# ─── Prediction Helpers ───────────────────────────────────────────────────────

def save_prediction(symbol, predicted_direction, predicted_move_pct,
                    confidence, recommendation, price_at_prediction, check_date):
    """Save a new prediction when analysis is run."""
    conn = get_db()
    conn.execute("""
        INSERT INTO predictions 
        (symbol, predicted_direction, predicted_move_pct, confidence, 
         recommendation, price_at_prediction, predicted_at, check_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        symbol.upper(),
        predicted_direction,
        predicted_move_pct,
        confidence,
        recommendation,
        price_at_prediction,
        datetime.now().isoformat(),
        check_date
    ))
    conn.commit()
    conn.close()


def get_pending_predictions():
    """Get all predictions that haven't been checked yet."""
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM predictions
        WHERE was_correct IS NULL
        AND check_date <= date('now')
        ORDER BY predicted_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_prediction_outcome(prediction_id, actual_price, actual_direction, was_correct):
    """Update a prediction with the actual outcome."""
    conn = get_db()
    conn.execute("""
        UPDATE predictions
        SET actual_price = ?,
            actual_direction = ?,
            was_correct = ?,
            checked_at = ?
        WHERE id = ?
    """, (
        actual_price,
        actual_direction,
        1 if was_correct else 0,
        datetime.now().isoformat(),
        prediction_id
    ))
    conn.commit()
    conn.close()


def get_accuracy_stats(symbol=None):
    """Get win rate stats. Pass symbol for per-stock, or None for overall."""
    conn = get_db()

    if symbol:
        rows = conn.execute("""
            SELECT * FROM predictions
            WHERE symbol = ? AND was_correct IS NOT NULL
            ORDER BY predicted_at DESC
        """, (symbol.upper(),)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM predictions
            WHERE was_correct IS NOT NULL
            ORDER BY predicted_at DESC
        """).fetchall()

    conn.close()
    rows = [dict(r) for r in rows]

    if not rows:
        return {"total": 0, "correct": 0, "win_rate": 0, "history": []}

    total = len(rows)
    correct = sum(1 for r in rows if r["was_correct"] == 1)
    win_rate = round((correct / total) * 100, 1)

    return {
        "total": total,
        "correct": correct,
        "win_rate": win_rate,
        "history": rows
    }


def get_all_symbols_accuracy():
    """Get win rate broken down by each symbol."""
    conn = get_db()
    rows = conn.execute("""
        SELECT 
            symbol,
            COUNT(*) as total,
            SUM(was_correct) as correct,
            ROUND(SUM(was_correct) * 100.0 / COUNT(*), 1) as win_rate
        FROM predictions
        WHERE was_correct IS NOT NULL
        GROUP BY symbol
        ORDER BY win_rate DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Alert Log Helpers ────────────────────────────────────────────────────────

def log_alert(symbol, alert_type, message):
    """Log a sent alert."""
    conn = get_db()
    conn.execute("""
        INSERT INTO alert_log (symbol, alert_type, message, sent_at)
        VALUES (?, ?, ?, ?)
    """, (symbol.upper(), alert_type, message, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def was_alert_sent_recently(symbol, alert_type, hours=6):
    """Check if we already sent this alert recently (avoid spam)."""
    conn = get_db()
    row = conn.execute("""
        SELECT id FROM alert_log
        WHERE symbol = ? 
        AND alert_type = ?
        AND sent_at >= datetime('now', ?)
    """, (symbol.upper(), alert_type, f"-{hours} hours")).fetchone()
    conn.close()
    return row is not None


# ─── Init on import ───────────────────────────────────────────────────────────
init_db()
