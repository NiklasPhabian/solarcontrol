import time

from config import Config
from database import SQLiteDatabase
from display import PVDisplay

POLL_INTERVAL_SECONDS = 5


def main() -> None:
    config = Config()
    db_path = config.get_sqlite_db_path()
    table_name = config.get_realtime_table_name()

    display = PVDisplay()

    with SQLiteDatabase(db_path, table_name) as db:
        last_timestamp = None
        while True:
            latest = db.latest_realtime()
            if latest is None:
                display.show_text("No data")
            else:
                timestamp = latest.get("timestamp")
                power = latest.get("power")
                if timestamp != last_timestamp:
                    display.show_power(power)
                    last_timestamp = timestamp
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
