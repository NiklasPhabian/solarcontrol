import asyncio
from config import Config
from energy_meter import KasaEnergyMeter
from controller import Controller
from relay import Relay
from display import Display
from database import SQLiteDatabase, SQLiteTable
from dateutil import tz
from temperature_sensor import TemperatureSensor
import datetime


timezone = tz.gettz('America/Los_Angeles')

config = Config()

# Controller
on_threshold = config['controller']['feedin_threshold']
off_threshold = config['controller']['consumption_threshold']
min_on_seconds = config['controller']['min_on_seconds']
min_off_seconds = config['controller']['min_off_seconds']
controller = Controller(on_threshold=on_threshold, off_threshold=off_threshold, min_on_seconds=min_on_seconds, min_off_seconds=min_off_seconds)

# Temperature probes
temp_blue = config['temp_sensors']['blue']
temp_black = config['temp_sensors']['black']
temp_white = config['temp_sensors']['white']
ts_blue = TemperatureSensor(temp_blue)
ts_black = TemperatureSensor(temp_black)
ts_white = TemperatureSensor(temp_white)

# Relay 
pin = config['relay']['pin']
relay = Relay(pin=pin)

# Displays
address1 = config['display1']['address']
address2 = config['display2']['address']
port1 = config['display1']['port']
port2 = config['display2']['port']

# Database setup
db_path = config['sqlite']['db_path']
table_name = config['sqlite']['table_name']
database = SQLiteDatabase(db_path=db_path, table_name=table_name)

# Meter
device = config['meter']['meter_device']
host = config['meter']['host']
username = config['kasa']['username']
password = config['kasa']['password']

LOG_INTERVAL = datetime.timedelta(minutes=1)

async def main():
    last_log = datetime.datetime.min.replace(tzinfo=timezone)
    meter = KasaEnergyMeter(device=device, host=host, username=username, password=password)
    display1 = Display(port=port1, address=address1)
    display2 = Display(port=port2, address=address2)
    database = SQLiteDatabase(db_path=db_path, table_name=table_name)
    table = SQLiteTable(database=database, name=table_name, columns=['power', 'temperature_blue', 'temperature_black', 'temperature_white'])
    table.create_if_not_exists()

    try:
        while True:
            now = datetime.datetime.now(timezone)
            timestamp = now.isoformat()
                
            power = await meter.get_power()
            state = controller.control(power)
            relay.apply_state(state)

            temp_blue = ts_blue.get_temp()
            temp_black = ts_black.get_temp()
            temp_white = ts_white.get_temp()

            row = {
                    "timestamp": timestamp,
                    "power": power,
                    "temperature_blue": temp_blue,
                    "temperature_black": temp_black,
                    "temperature_white": temp_white
                }

            if now - last_log >= LOG_INTERVAL:
                table.insert_row(row)
                power_bars = table.latest_n_resampled_values(n=60, column="power", aggregate="AVG", sample_interval=15)                   
                last_log = now
            
            display1.show_bar_chart(bars=power_bars, value=power, unit='W',)
            display2.display_celsius(temp_blue)

            print(row)
            await asyncio.sleep(10)

    except KeyboardInterrupt:
             await meter.disconnect()
             database.close()
             relay.cleanup()
             display1.cleanup()
             display2.cleanup()


if __name__ == "__main__":
    main()
