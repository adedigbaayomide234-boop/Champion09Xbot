import sqlite3
import os
import threading
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "championx.db")
_lock = threading.Lock()

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            points      INTEGER DEFAULT 0,
            wins        INTEGER DEFAULT 0,
            losses      INTEGER DEFAULT 0,
            games       INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS scores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            game        TEXT NOT NULL,
            user_id     INTEGER NOT NULL,
            score       INTEGER NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_scores_game ON scores(game, score DESC);
        """)

@contextmanager
def _conn():
    with _lock:
        conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

def ensure_user(user_id: int, username: str, first_name: str):
    with _conn() as c:
        c.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
        """, (user_id, username or "", first_name or "Champion"))

def get_user(user_id: int):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

def add_points(user_id: int, points: int, won: bool):
    with _conn() as c:
        c.execute("""
            UPDATE users
            SET points = points + ?,
                wins   = wins   + ?,
                losses = losses + ?,
                games  = games  + 1
            WHERE user_id = ?
        """, (points, 1 if won else 0, 0 if won else 1, user_id))

def save_score(game: str, user_id: int, score: int):
    with _conn() as c:
        c.execute("INSERT INTO scores (game, user_id, score) VALUES (?,?,?)",
                  (game, user_id, score))

def top_global(limit: int = 10):
    with _conn() as c:
        rows = c.execute("""
            SELECT u.user_id, u.first_name, u.username, u.points, u.wins, u.games
            FROM users u
            ORDER BY u.points DESC, u.wins DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def top_game(game: str, limit: int = 10):
    with _conn() as c:
        rows = c.execute("""
            SELECT s.score, u.first_name, u.username, u.user_id
            FROM scores s
            JOIN users u ON u.user_id = s.user_id
            WHERE s.game = ?
            ORDER BY s.score DESC
            LIMIT ?
        """, (game, limit)).fetchall()
        return [dict(r) for r in rows]

def user_rank(user_id: int):
    with _conn() as c:
        row = c.execute("""
            SELECT COUNT(*) + 1 AS rank
            FROM users
            WHERE points > (SELECT points FROM users WHERE user_id=?)
        """, (user_id,)).fetchone()
        return row["rank"] if row else 0
