import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Sequence, Union

TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLiteDatabase:

    def __init__(self, db_path: Union[str, Path], journal_mode: str = "DELETE", synchronous: str = "FULL") -> None:
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._apply_pragmas(journal_mode=journal_mode, synchronous=synchronous)

    def _apply_pragmas(self, journal_mode: str, synchronous: str) -> None:
        allowed_journal_modes = {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}
        allowed_synchronous = {"OFF", "NORMAL", "FULL", "EXTRA"}

        journal_mode = journal_mode.upper()
        synchronous = synchronous.upper()

        if journal_mode not in allowed_journal_modes:
            raise ValueError(f"Unsupported SQLite journal_mode: {journal_mode}")
        if synchronous not in allowed_synchronous:
            raise ValueError(f"Unsupported SQLite synchronous mode: {synchronous}")

        self.conn.execute(f"PRAGMA journal_mode={journal_mode}")
        self.conn.execute(f"PRAGMA synchronous={synchronous}")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteDatabase":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: object,
    ) -> None:
        self.close()


class SQLiteTable:

    def __init__(
        self,
        database: SQLiteDatabase,
        name: str,
        columns: Sequence[str],
        column_types: Optional[Dict[str, str]] = None,
    ) -> None:
        self.database = database
        self.name = name
        self.columns = list(columns)
        self.column_types = column_types or {}

    def create_if_not_exists(self) -> None:
        def _col_type(col: str) -> str:
            return self.column_types.get(col, "REAL")
        columns_def = ", ".join(f"{col} {_col_type(col)}" for col in self.columns)
        create_sql = f"CREATE TABLE IF NOT EXISTS {self.name} (timestamp TEXT PRIMARY KEY, {columns_def})"
        self.database.conn.execute(create_sql)
        self.database.conn.commit()

    def insert_row(self, row: Dict[str, object]) -> None:
        columns = ", ".join(row.keys())
        placeholders = ", ".join(f":{key}" for key in row.keys())
        insert_sql = f"INSERT OR REPLACE INTO {self.name} ({columns}) VALUES ({placeholders})"
        self.database.conn.execute(insert_sql, row)
        self.database.conn.commit()

    def latest_value(self, column: str) -> Optional[object]:
        query_sql = f"SELECT {column} FROM {self.name} ORDER BY timestamp DESC LIMIT 1"
        cursor = self.database.conn.execute(query_sql)
        row = cursor.fetchone()
        return row[0] if row else None
    
    def lates_row(self) -> Optional[Dict[str, object]]:
        query_sql = f"SELECT * FROM {self.name} ORDER BY timestamp DESC LIMIT 1"
        cursor = self.database.conn.execute(query_sql)
        row = cursor.fetchone()
        if row:
            return dict(zip(["timestamp"] + self.columns, row))
        return None
    
    def latest_n_resampled_values(
        self,
        column: str,
        n: int = 60,
        aggregate: str = "AVG",
        sample_interval: int = 15,
    ) -> list[object]:
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
        return [row[1] for row in rows]
    
    def resampled_timeseries(
        self,
        column: str,
        *,
        start_time: datetime,
        end_time: datetime,
        sample_interval: int = 15,
    ) -> list[Dict[str, object]]:
        query_sql = f"""\
        SELECT 
            datetime(strftime('%Y-%m-%d %H:', timestamp) || printf('%02d', (strftime('%M', timestamp) / {sample_interval}) * {sample_interval}), 'localtime') AS interval,
            AVG({column}) AS value
        FROM {self.name}
        WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)
        GROUP BY interval
        ORDER BY interval;
        """
        cursor = self.database.conn.execute(query_sql, (start_time.isoformat(), end_time.isoformat()))
        rows = cursor.fetchall()
        return [{"timestamp": row[0], column: row[1]} for row in rows]

    def daily_energy(
        self,
        column: str,
        *,
        start_time: datetime,
        end_time: datetime,
        resample_interval: int = 1,
    ) -> list[Dict[str, object]]:
        """Resample power (W) to regular intervals, then integrate per day to get energy (Wh)."""
        where_clause = "WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)"
        params = [start_time.isoformat(), end_time.isoformat()]

        query_sql = f"""\
        WITH resampled AS (
            SELECT
                date(timestamp, 'localtime') AS day,
                strftime('%Y-%m-%d %H:%M',
                    CAST(strftime('%s', timestamp) AS INTEGER) / ({resample_interval} * 60) * ({resample_interval} * 60),
                    'unixepoch', 'localtime'
                ) AS interval,
                AVG({column}) AS avg_power
            FROM {self.name}
            {where_clause}
            GROUP BY interval
        )
        SELECT day, SUM(avg_power) * {resample_interval} / 60.0 AS energy_wh
        FROM resampled
        GROUP BY day
        ORDER BY day;
        """
        cursor = self.database.conn.execute(query_sql, params)
        rows = cursor.fetchall()
        return [{"date": row[0], "energy_wh": row[1]} for row in rows]


def main() -> None:
    database = SQLiteDatabase("database/haslach.db")
    db_table = SQLiteTable(database=database, name='main', columns=['power_pv', 'power_fridge', 'power_dishwasher', 'temperature'])        
    daily_energy = db_table.daily_energy(
        column='power_pv',
        start_time=datetime(2026, 8, 1),
        end_time=datetime(2026, 8, 31, 23, 59, 59),
        resample_interval=15,
    )
    print(daily_energy)
    
    database.close()


if __name__ == "__main__":
    main()
