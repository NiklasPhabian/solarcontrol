import time

from config import Config
from database import SQLiteDatabase
from display import Display

POLL_INTERVAL_SECONDS = 5

config = Config()
db_path = config.sqlite_db_path()
table_name = config.realtime_table_name()
display = Display()


def display_power() -> None:
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
                    display.display_watts(power)
                    last_timestamp = timestamp
            time.sleep(POLL_INTERVAL_SECONDS)


def display_chart() -> None:
    with SQLiteDatabase(db_path, table_name) as db:
        while True:
            bars = [row['power'] for row in db.latest_n15mins(60)]
            value = db.latest_realtime()['power']
            display.show_chart_with_last_value(bars=bars, value=value)
            time.sleep(POLL_INTERVAL_SECONDS)
        


if __name__ == "__main__":
    try:
        #display_power()
        display_chart()
    except KeyboardInterrupt:
        pass
