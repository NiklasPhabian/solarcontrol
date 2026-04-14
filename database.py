import re
import sqlite3
from pathlib import Path
from typing import Dict, Optional

TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS {table_name} (
    timestamp TEXT PRIMARY KEY,
    power REAL
)
"""

INSERT_REALTIME_SQL = """\
INSERT OR REPLACE INTO {table_name} (timestamp, power)
VALUES (:timestamp, :power)
"""

LATEST_REALTIME_SQL = """\
SELECT timestamp, power
FROM {table_name}
ORDER BY timestamp DESC
LIMIT 1
"""


class SQLiteDatabase:
    def __init__(self, db_path: Path, table_name: str = "realtime"):
        self.db_path = Path(db_path)
        self.table_name = self._validate_table_name(table_name)
        self.conn = sqlite3.connect(self.db_path)
        self._ensure_table()

    @staticmethod
    def _validate_table_name(name: str) -> str:
        if TABLE_NAME_PATTERN.fullmatch(name):
            return name
        raise ValueError(
            "Invalid SQLite table name. Use only letters, numbers, and underscores, and do not start with a digit."
        )

    def _ensure_table(self) -> None:
        create_sql = CREATE_TABLE_SQL.format(table_name=self.table_name)
        self.conn.execute(create_sql)
        self.conn.commit()

    def insert_realtime(self, row: dict) -> None:
        insert_sql = INSERT_REALTIME_SQL.format(table_name=self.table_name)
        self.conn.execute(insert_sql, row)
        self.conn.commit()

    def latest_realtime(self) -> Optional[Dict[str, object]]:
        query_sql = LATEST_REALTIME_SQL.format(table_name=self.table_name)
        cursor = self.conn.execute(query_sql)
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "timestamp": row[0],
            "power": row[1],
        }

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteDatabase":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
