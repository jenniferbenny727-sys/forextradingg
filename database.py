import sqlite3
import logging
import os
import config

logger = logging.getLogger(__name__)

def init_db() -> None:
    # Create the directory if it doesn't exist (fixes the OperationalError)
    db_dir = os.path.dirname(config.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directory {db_dir}: {e}")

    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_prefs (
                user_id INTEGER PRIMARY KEY,
                pair TEXT NOT NULL DEFAULT 'EUR/USD',
                timeframe TEXT NOT NULL DEFAULT '1h',
                alerts_enabled INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
    finally:
        conn.close()

def get_prefs(user_id: int) -> dict:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    try:
        row = conn.execute(
            "SELECT pair, timeframe, alerts_enabled FROM user_prefs WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if row:
            return {"pair": row[0], "timeframe": row[1], "alerts": bool(row[2])}
        conn.execute(
            "INSERT INTO user_prefs (user_id) VALUES (?)", (user_id,)
        )
        conn.commit()
        return {"pair": config.DEFAULT_PAIR, "timeframe": config.DEFAULT_TIMEFRAME, "alerts": False}
    finally:
        conn.close()

def set_pref(user_id: int, key: str, value) -> None:
    if key not in ("pair", "timeframe", "alerts_enabled"):
        raise ValueError("Invalid preference key")
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    try:
        get_prefs(user_id)  # ensure row exists
        conn.execute(f"UPDATE user_prefs SET {key}=? WHERE user_id=?", (value, user_id))
        conn.commit()
    finally:
        conn.close()

def get_alert_users() -> list[int]:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    try:
        rows = conn.execute(
            "SELECT user_id FROM user_prefs WHERE alerts_enabled=1"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()
