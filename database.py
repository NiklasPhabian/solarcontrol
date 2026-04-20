import re
import sqlite3
from pathlib import Path
from typing import Dict, Optional

TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLiteDatabase:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._ensure_table()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteDatabase":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class SQLiteTable:
    
    def __init__(self, database, name, columns):
        self.database = database
        self.name = name
        self.columns = columns

    def create(self):        
        columns_def = ", ".join(f"{name} REAL" for name in self.columns)
        create_sql = f"CREATE TABLE IF NOT EXISTS {self.name} (TIMESTAMP TEXT PRIMARY KEY, {columns_def})"
        self.database.conn.execute(create_sql)
        self.database.conn.commit()
    
    def insert_row(self, row: dict) -> None:
        columns = ", ".join(row.keys())
        placeholders = ", ".join(f":{key}" for key in row.keys())
        insert_sql = f"INSERT OR REPLACE INTO {self.name} ({columns}) VALUES ({placeholders})"
        self.database.conn.execute(insert_sql, row)
        self.database.conn.commit()

    def latest_value(self, column) -> Optional[Dict[str, object]]:
        query_sql = f"SELECT {column} FROM {self.name} ORDER BY timestamp DESC LIMIT 1"
        cursor = self.database.conn.execute(query_sql)
        row = cursor.fetchone()
        return row[0] if row else None
    
    def latest_n(self, column, n=60, aggregate="AVG", sample_interval=15) -> list[Dict[str, object]]:
        query_sql = f"""\
        SELECT 
            datetime(strftime('%Y-%m-%d %H:', timestamp) || printf('%02d', (strftime('%M', timestamp) / {sample_interval}) * {sample_interval}), 'localtime') AS interval,
            {aggregate}({column}) AS value
        FROM {self.name}
        GROUP BY interval
        ORDER BY interval DESC
        LIMIT {n};
        """
        cursor = self.database.conn.execute(query_sql)
        rows = cursor.fetchall()[::-1]  # Reverse to get oldest first
        return [{"timestamp": row[0], column: row[1]} for row in rows]
