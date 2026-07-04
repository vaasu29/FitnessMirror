"""
storage.py
Simple SQLite-backed workout history storage. Zero cost, no server needed.
"""
import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "workouts.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def init_db():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            exercise TEXT,
            reps INTEGER,
            avg_form_score REAL,
            duration_seconds REAL
        )
    """)
    conn.commit()
    conn.close()


def save_workout(exercise, reps, avg_form_score, duration_seconds):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO workouts (timestamp, exercise, reps, avg_form_score, duration_seconds) VALUES (?, ?, ?, ?, ?)",
        (time.time(), exercise, reps, avg_form_score, duration_seconds),
    )
    conn.commit()
    conn.close()


def get_history(limit=20):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT timestamp, exercise, reps, avg_form_score, duration_seconds FROM workouts ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
