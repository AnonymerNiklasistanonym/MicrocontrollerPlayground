import sqlite3
from datetime import datetime
from pathlib import Path


def initialize_database(db_path: Path, tables: list[tuple[str, str, str]]):
    """
    Initialize a SQLite database.
    """
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Create tables if not existing
    for table_name, column_name, data_type in tables:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                {column_name} {data_type} NOT NULL,
                UNIQUE(timestamp, {column_name})
            )
        """)
    conn.commit()
    conn.close()


def add_database_entry(db_name: Path, table_name: str, column_name: str, time: datetime, value):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    # Add table entry
    try:
        cursor.execute(f"""
            INSERT INTO {table_name} (timestamp, {column_name})
            VALUES (?, ?)
        """, (time.isoformat(timespec='seconds'), value))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Duplicate entry ignored: {time=}, {value=}")
    conn.close()
