import datetime
from dateutil import tz
from config import Config
from database import SQLiteDatabase
from meter import EnergyMeter
from display import Display
import time

pst = tz.gettz('America/Los_Angeles')
config = Config('config_bishop.ini')

# Database setup
db_path = config['sqlite']['db_path']
table_name = config['sqlite']['table_name']
database = SQLiteDatabase(db_path=db_path, table_name=table_name)

# Meter setup
host = config['meter']['host']
username = config['kasa']['username']
password = config['kasa']['password']
meter = EnergyMeter(host=host, username=username, password=password)

# Display setup
address = config['display']['address']
port = config['display']['port']
display = Display(port=port, address=address)

def main() -> None:
    now = datetime.datetime.now(pst)
    timestamp = now.isoformat()

    power  = meter.get_power()
    database.insert_realtime({ "timestamp": timestamp, "power": power})

    with SQLiteDatabase(db_path, table_name) as db:
        db.insert_realtime({ "timestamp": now.isoformat(), "power": power})
        bars = db.latest_n15mins(n=60)
    
    bars=[row['power'] for row in bars]
    display.show_chart_with_last_value(value = power, bars=bars)
   
    print({ "timestamp": timestamp, "power": power})
    time.sleep(2)

if __name__ == "__main__":
    main()
