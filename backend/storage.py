import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def save_assessment(result: dict) -> None:
    database = Path(os.getenv("AZPU_DATABASE_PATH", ".azpu/assessments.sqlite3"))
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute(
            "INSERT INTO assessments (id, result_json) VALUES (?, ?)",
            (result["assessment_id"], json.dumps(result, ensure_ascii=False)),
        )
