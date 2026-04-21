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

config = Config('config_haslach.ini')

# Controller
on_threshold = config['controller']['on_threshold']
off_threshold = config['controller']['off_threshold']
min_on_seconds = config['controller']['min_on_seconds']
min_off_seconds = config['controller']['min_off_seconds']

# Temperature probes
probe_id_blue = config['temp_sensors']['blue']
probe_id_black = config['temp_sensors']['black']
probe_id_white = config['temp_sensors']['white']

# Relay 
relay_pin = config['relay']['pin']

# Displays
display_address1 = config['display1']['address']
display_address2 = config['display2']['address']
display_port1 = config['display1']['port']
display_port2 = config['display2']['port']

# Database setup
db_path = config['sqlite']['db_path']
table_name = config['sqlite']['table_name']
columns=['power', 'temperature_blue', 'temperature_black', 'temperature_white', 'controller_state']

# Meter
meter_host = config['meter']['host']
username = config['kasa']['username']
password = config['kasa']['password']

LOG_INTERVAL = datetime.timedelta(minutes=5)

async def main():
    last_log = datetime.datetime.min.replace(tzinfo=timezone)

    power_meter = KasaEnergyMeter(host=meter_host, username=username, password=password)
    temperature_sensor_blue = TemperatureSensor(serial=probe_id_blue)
    temperature_sensor_black = TemperatureSensor(serial=probe_id_black)
    temperature_sensor_white = TemperatureSensor(serial=probe_id_white)

    display1 = Display(port=display_port1, address=display_address1)
    display2 = Display(port=display_port2, address=display_address2)
    
    database = SQLiteDatabase(db_path=db_path)
    table = SQLiteTable(database=database, name=table_name, columns=columns)
    table.create_if_not_exists()

    controller = Controller(on_threshold=on_threshold, off_threshold=off_threshold, min_on_seconds=min_on_seconds, min_off_seconds=min_off_seconds)
    relay = Relay(pin=relay_pin)

    try:
        while True:
            now = datetime.datetime.now(timezone)
            timestamp = now.isoformat()
                
            power = await power_meter.get_power()

            temp_blue = temperature_sensor_blue.get_temp()
            temp_black = temperature_sensor_black.get_temp()
            temp_white = temperature_sensor_white.get_temp()

            state = controller.control(temp_blue)
            relay.apply_state(state)

            row = {
                    "timestamp": timestamp,
                    "power": power,
                    "temperature_blue": temp_blue,
                    "temperature_black": temp_black,
                    "temperature_white": temp_white,
                    "controller_state": state
                }

            if now - last_log >= LOG_INTERVAL:
                table.insert_row(row)
                power_bars = table.latest_n_resampled_values(n=60, column="power", aggregate="AVG", sample_interval=15)
                temperature_bars = table.latest_n_resampled_values(n=60, column="temperature_blue", aggregate="AVG", sample_interval=15)
                last_log = now
            
            display1.show_chart_with_last_value(value=power, unit='W', bars=power_bars)
            display2.show_chart_with_last_value(value=temp_blue, unit='°C', bars=temperature_bars)
            #display2.display_celsius(temp_blue)

            #print(row)
            await asyncio.sleep(15)
    finally:
             await power_meter.disconnect()
             database.close()
             relay.cleanup()
             display1.cleanup()
             display2.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
