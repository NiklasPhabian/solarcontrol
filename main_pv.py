import datetime
from dateutil import tz
from config import Config
from database import SQLiteDatabase
from meter import EnergyMeter
from display import Display
import time
from temperature_sensor import TemperatureSensor

pst = tz.gettz('America/Los_Angeles')
config = Config('config_bishop.ini')

# Database setup
db_path = config['sqlite']['db_path']
table_name = config['sqlite']['table_name']
database = SQLiteDatabase(db_path=db_path, table_name=table_name)
db_table = database.SQLiteTable(database, table_name, columns=['power_pv', 'power_fridge', 'power_dishwasher', 'temperature'])

# Meter setup
username = config['kasa']['username']
password = config['kasa']['password']

host_pv = config['meter_pv']['host']
host_fridge = config['meter_fridge']['host']
host_dishwasher = config['meter_dishwasher']['host']

meter_pv = EnergyMeter(host=host_pv, username=username, password=password)
meter_fridge = EnergyMeter(host=host_fridge, username=username, password=password)
meter_dishwasher = EnergyMeter(host=host_dishwasher, username=username, password=password)

# Temperature sensor setup (optional)
indoor_sensor_id = config['temp_sensors']['indoor']
temp_sensor = TemperatureSensor(serial=indoor_sensor_id)

# Display setup
address = config['display']['address']
port = config['display']['port']
display = Display(port=port, address=address)


def main() -> None:
    now = datetime.datetime.now(pst)
    timestamp = now.isoformat()

    power_pv  = meter_pv.get_power()
    power_fridge  = meter_fridge.get_power()
    power_dishwasher  = meter_dishwasher.get_power()
    temperature = temp_sensor.get_temp()

    row = {
        "timestamp": timestamp,
        "power_pv": power_pv,
        "power_fridge": power_fridge,
        "power_dishwasher": power_dishwasher,
        "temperature": temperature
    }

    db_table.insert_row(row)        
    bars = db_table.latest_n(n=60)   
    
    display.show_chart_with_last_value(value=power_pv, bars=bars)
   
    print(row)
    time.sleep(60)

if __name__ == "__main__":
    main()
