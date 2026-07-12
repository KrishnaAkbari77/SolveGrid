from __future__ import annotations

from pathlib import Path
import sqlite3
from contextlib import closing

import matplotlib.pyplot as plt
import pandas as pd

from database import DEFAULT_DB_PATH, init_db


def load_history(db_path: str | Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        df = pd.read_sql_query("SELECT * FROM solves ORDER BY date", conn, parse_dates=["date"])
    return df


def generate_dashboard(
    db_path: str | Path = DEFAULT_DB_PATH,
    output_dir: str | Path = "charts",
) -> list[Path]:
    """Write line chart from the solves table."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    df = load_history(db_path)

    if df.empty:
        raise ValueError("no solve history available; solve a puzzle before generating charts")

    written: list[Path] = []

    solves_over_time = df.set_index("date").resample("D").size()
    plt.figure(figsize=(8, 4))
    solves_over_time.plot(marker="o")
    plt.title("Solves over time")
    plt.xlabel("Date")
    plt.ylabel("Solves")
    plt.tight_layout()
    path = output_path / "solves_over_time.png"
    plt.savefig(path)
    plt.close()
    written.append(path)



    return written


if __name__ == "__main__":
    for chart in generate_dashboard():
        print(chart)
