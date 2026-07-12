"""SQLite solve history shared by Sudoku and cube workflows."""

from __future__ import annotations

from datetime import datetime
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).with_name("solves.db")


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS solves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                puzzle_type TEXT NOT NULL,
                date TEXT NOT NULL,
                time_taken_seconds REAL NOT NULL,
                input_summary TEXT
            )
            """
        )
        conn.commit()


def log_solve(
    puzzle_type: str,
    time_taken: float,
    input_summary: str = "",
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    """Log a solve and return the inserted row id."""
    init_db(db_path)
    now = datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.execute(
            """
            INSERT INTO solves (puzzle_type, date, time_taken_seconds, input_summary)
            VALUES (?, ?, ?, ?)
            """,
            (puzzle_type, now, float(time_taken), input_summary),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_history(
    puzzle_type: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return solve rows, optionally filtered by puzzle type."""
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        if puzzle_type is None:
            rows = conn.execute("SELECT * FROM solves ORDER BY date").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM solves WHERE puzzle_type = ? ORDER BY date",
                (puzzle_type,),
            ).fetchall()
    return [dict(row) for row in rows]
