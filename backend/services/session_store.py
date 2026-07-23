"""
session_store.py — SQLite-backed session persistence for DecisionLens AI.

Replaces the in-memory `sessions: Dict[str, Dict[str, Any]]` dict that was
wiped on every Render free-tier restart. With SQLite, a judge who refreshes
the page mid-demo (or hits the backend after a restart) can restore their
full session state instead of seeing "Session not found".

Design:
  - One SQLite file at SESSION_DB_PATH (default: ./sessions.db)
  - Each session = one row keyed by session_id
  - The cleaned DataFrame is serialized as CSV bytes (portable across
    pandas versions; parquet would be faster but adds a dependency)
  - All derived data (profile, summary, score, whatif, cleaning_log,
    metadata) is stored as JSON text
  - A created_at timestamp enables future TTL cleanup
  - Thread-safe via a module-level Lock (uvicorn runs sync handlers in
    a threadpool, so concurrent writes are possible)

Schema:
    CREATE TABLE sessions (
        session_id   TEXT PRIMARY KEY,
        df_csv       TEXT NOT NULL,        -- cleaned DataFrame as CSV
        filename     TEXT,
        dataset_ctx  TEXT,
        cleaning_log TEXT,                  -- JSON list of strings
        rows_before  INTEGER,
        rows_after   INTEGER,
        start_time_ms INTEGER,
        profile_data TEXT,                  -- JSON
        summary_data TEXT,                  -- JSON
        score_data   TEXT,                  -- JSON
        whatif_data  TEXT,                  -- JSON
        time_to_insight_ms INTEGER,
        created_at   TEXT NOT NULL
    )

All public functions are safe to call from any thread.
"""
import os
import io
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd

# Where to store the SQLite file. Override via env var if needed.
SESSION_DB_PATH = os.getenv("SESSION_DB_PATH", os.path.join(os.getcwd(), "sessions.db"))

_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    """Open a new connection per call. sqlite3 connections are not thread-safe
    by default, so we open one per operation under the lock."""
    conn = sqlite3.connect(SESSION_DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the sessions table if it doesn't exist. Idempotent."""
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id   TEXT PRIMARY KEY,
                    df_csv       TEXT NOT NULL,
                    filename     TEXT,
                    dataset_ctx  TEXT,
                    cleaning_log TEXT,
                    rows_before  INTEGER,
                    rows_after   INTEGER,
                    start_time_ms INTEGER,
                    profile_data TEXT,
                    summary_data TEXT,
                    score_data   TEXT,
                    whatif_data  TEXT,
                    time_to_insight_ms INTEGER,
                    created_at   TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at)")
            conn.commit()
        finally:
            conn.close()


def _df_to_csv(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def _csv_to_df(csv_str: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(csv_str))


def create_session(
    session_id: str,
    df: pd.DataFrame,
    filename: str,
    dataset_context: str,
    cleaning_log: list,
    rows_before: int,
    rows_after: int,
    start_time_ms: int,
) -> None:
    """Insert a new session row."""
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                INSERT INTO sessions
                    (session_id, df_csv, filename, dataset_ctx, cleaning_log,
                     rows_before, rows_after, start_time_ms,
                     profile_data, summary_data, score_data, whatif_data,
                     time_to_insight_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?)
            """, (
                session_id,
                _df_to_csv(df),
                filename,
                dataset_context,
                json.dumps(cleaning_log),
                int(rows_before),
                int(rows_after),
                int(start_time_ms),
                datetime.utcnow().isoformat(),
            ))
            conn.commit()
        finally:
            conn.close()


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Reconstruct the full session dict (matches the old in-memory shape)."""
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()
        finally:
            conn.close()

    if row is None:
        return None

    df = _csv_to_df(row["df_csv"])
    return {
        "df": df,
        "filename": row["filename"] or "upload.csv",
        "dataset_context": row["dataset_ctx"] or "business",
        "cleaning_log": json.loads(row["cleaning_log"] or "[]"),
        "rows_before": int(row["rows_before"] or 0),
        "rows_after": int(row["rows_after"] or 0),
        "start_time_ms": int(row["start_time_ms"] or 0),
        "profile_data": json.loads(row["profile_data"]) if row["profile_data"] else None,
        "summary_data": json.loads(row["summary_data"]) if row["summary_data"] else None,
        "score_data": json.loads(row["score_data"]) if row["score_data"] else None,
        "whatif_data": json.loads(row["whatif_data"]) if row["whatif_data"] else None,
        "time_to_insight_ms": int(row["time_to_insight_ms"]) if row["time_to_insight_ms"] is not None else None,
        "created_at": row["created_at"],
    }


def update_session_field(session_id: str, field: str, value: Any) -> None:
    """Update a single derived-data field on an existing session.

    Allowed fields: profile_data, summary_data, score_data, whatif_data,
    time_to_insight_ms. Anything else raises ValueError.
    """
    allowed = {"profile_data", "summary_data", "score_data", "whatif_data", "time_to_insight_ms"}
    if field not in allowed:
        raise ValueError(f"Cannot update field '{field}'. Allowed: {allowed}")

    if field == "time_to_insight_ms":
        stored = int(value)
    else:
        stored = json.dumps(value, default=str)

    init_db()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                f"UPDATE sessions SET {field} = ? WHERE session_id = ?",
                (stored, session_id)
            )
            conn.commit()
        finally:
            conn.close()


def delete_session(session_id: str) -> None:
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()


def count_sessions() -> int:
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()
            return int(row["n"])
        finally:
            conn.close()


def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """Delete sessions older than max_age_hours. Returns count deleted.

    For hackathon: 24h TTL keeps the DB from growing forever without
    disrupting active demos.
    """
    init_db()
    cutoff = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()


# Initialize the DB on import so the table exists before first request.
init_db()
