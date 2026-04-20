import re
import sqlite3
from pathlib import Path
from typing import Dict, Optional

TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLiteDatabase:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
<<<<<<< HEAD
        self.conn = sqlite3.connect(self.db_path)
        self._ensure_table()
=======
        self.conn = sqlite3.connect(self.db_path)        
>>>>>>> 582eff108a0b04459e817f8b1c410a9cc9418910

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

<<<<<<< HEAD
    def create(self):        
        columns_def = ", ".join(f"{name} REAL" for name in self.columns)
        create_sql = f"CREATE TABLE IF NOT EXISTS {self.name} (TIMESTAMP TEXT PRIMARY KEY, {columns_def})"
=======
    def create_if_not_exists(self):        
        columns_def = ", ".join(f"{name} REAL" for name in self.columns)
        create_sql = f"CREATE TABLE IF NOT EXISTS {self.name} (timestamp TEXT PRIMARY KEY, {columns_def})"
>>>>>>> 582eff108a0b04459e817f8b1c410a9cc9418910
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
    
<<<<<<< HEAD
    def latest_n(self, column, n=60, aggregate="AVG", sample_interval=15) -> list[Dict[str, object]]:
=======
    def lates_row(self) -> Optional[Dict[str, object]]:
        query_sql = f"SELECT * FROM {self.name} ORDER BY timestamp DESC LIMIT 1"
        cursor = self.database.conn.execute(query_sql)
        row = cursor.fetchone()
        if row:
            return dict(zip(["timestamp"] + self.columns, row))
        return None
    
    def latest_n_resampled_values(self, column, n=60, aggregate="AVG", sample_interval=15) -> list[Dict[str, object]]:
>>>>>>> 582eff108a0b04459e817f8b1c410a9cc9418910
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
<<<<<<< HEAD
        return [{"timestamp": row[0], column: row[1]} for row in rows]
=======
        return [row[1] for row in rows]
    
    def resampled_timeseries(self, column, start_time, end_time, sample_interval=15) -> list[Dict[str, object]]:
        query_sql = f"""\
        SELECT 
            datetime(strftime('%Y-%m-%d %H:', timestamp) || printf('%02d', (strftime('%M', timestamp) / {sample_interval}) * {sample_interval}), 'localtime') AS interval,
            AVG({column}) AS value
        FROM {self.name}
        WHERE timestamp BETWEEN ? AND ?
        GROUP BY interval
        ORDER BY interval;
        """
        cursor = self.database.conn.execute(query_sql, (start_time.isoformat(), end_time.isoformat()))
        rows = cursor.fetchall()
        return [{"timestamp": row[0], column: row[1]} for row in rows]


def main():
    database = SQLiteDatabase("solarcontrol.db")
    db_table = SQLiteTable(database=database, name='main', columns=['power_pv', 'power_fridge', 'power_dishwasher', 'temperature'])        
    print(db_table.latest_value("power_pv"))
    print(db_table.latest_n_aggregate("power_pv", n=5, aggregate="AVG", sample_interval=15))
    database.close()


if __name__ == "__main__":
    main()
>>>>>>> 582eff108a0b04459e817f8b1c410a9cc9418910
