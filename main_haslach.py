import asyncio
from config import Config
from energy_meter import EcoTracker
from controller import Controller
from relay import Relay
from display import Display
from database import SQLiteDatabase, SQLiteTable
from dateutil import tz
from temperature_sensor import TemperatureSensor
import datetime
import modbus.transport
import modbus.devices
from html_writer import HTMLWriter
from plotter import Plotter


timezone = tz.gettz('Europe/Berlin')

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
meter_host = config['ecotracker']['host']

# Modbus
modbus_controler1_port = config['modbus_controller']['port']
slave_address_sht20 = config['SHT20']['slave_address']
slave_address_sdm230_bwwp = config['SDM230_bwwp']['slave_address']
slave_address_sdm230_mypv = config['SDM230_mypv']['slave_address']
slave_address_finder7m = config['Finder7M']['slave_address']

# Time settings
LOG_INTERVAL = datetime.timedelta(minutes=5)
PLOT_INTERVAL = datetime.timedelta(hours=1)

output_dir = "www"

async def main(interactive=False):
    last_log = datetime.datetime.min.replace(tzinfo=timezone)
    last_plot = datetime.datetime.min.replace(tzinfo=timezone)

    power_meter = EcoTracker(host=meter_host)

    temperature_sensor_blue = TemperatureSensor(serial=probe_id_blue)
    temperature_sensor_black = TemperatureSensor(serial=probe_id_black)
    temperature_sensor_white = TemperatureSensor(serial=probe_id_white)

    modbus_controller = modbus.transport.ModbusController(port=modbus_controler1_port)
    sht20 = modbus.devices.SHT20(modbus_controller, slave_address_sht20)
    sdm_bwwp = modbus.devices.SDM230(modbus_controller, slave_address_sdm230_bwwp)
    sdm_mypv = modbus.devices.SDM230(modbus_controller, slave_address_sdm230_mypv)
    finder7m = modbus.devices.Finder7M38_8_400(modbus_controller, slave_address_finder7m)

    display1 = Display(port=display_port1, address=display_address1)
    display2 = Display(port=display_port2, address=display_address2)

    database = SQLiteDatabase(db_path=db_path)
    table = SQLiteTable(database=database, name=table_name, columns=columns)
    table.create_if_not_exists()

    plotter = Plotter(table)

    controller = Controller(on_threshold=on_threshold, off_threshold=off_threshold, min_on_seconds=min_on_seconds, min_off_seconds=min_off_seconds)
    relay = Relay(pin=relay_pin)

    try:
        while True:
            now = datetime.datetime.now(timezone)
            timestamp = now.isoformat()

            power_mains = await power_meter.get_power()
            power_bwwp = sdm_bwwp.read_active_power()
            power_mypv = sdm_mypv.read_active_power()
            power_wp = finder7m.read_total_active_power()

            temp_blue = temperature_sensor_blue.get_temp()
            temp_black = temperature_sensor_black.get_temp()
            temp_white = temperature_sensor_white.get_temp()

            temp_sht = sht20.read_temperature()
            humid_sht = sht20.read_humidity()

            state = controller.control(power_mains)
            relay.apply_state(state)

            row = {
                    "timestamp": timestamp,
                    "power_mains": power_mains,
                    "power_bwwp": power_bwwp,
                    "power_mypv": power_mypv,
                    "power_wp": power_wp,
                    "temperature_blue": temp_blue,
                    "temperature_black": temp_black,
                    "temperature_white": temp_white,
                    "controller_state": state,
                    "temperature_sht": temp_sht,
                    "humidity_sht": humid_sht
                }

            if now - last_log >= LOG_INTERVAL:
                table.insert_row(row)
                power_bars = table.latest_n_resampled_values(n=60, column="power_mains", aggregate="AVG", sample_interval=15)
                temperature_bars = table.latest_n_resampled_values(n=60, column="temperature_blue", aggregate="AVG", sample_interval=15)
                last_log = now

            if now - last_plot >= PLOT_INTERVAL:
                plot_files = []
                plot_files.append(plotter.plot_timeseries("power_mains", hours=24))        
                plot_files.append(plotter.plot_timeseries("power_bwwp", hours=24))        
                plot_files.append(plotter.plot_timeseries("power_mypv", hours=24))        
                last_plot = now

            html_writer = HTMLWriter(output_dir=output_dir, plot_files=plot_files, current_conditions=row)
            html_writer.write_html()

            display1.show_chart_with_last_value(value=power_mains, unit='W', bars=power_bars)
            display2.show_chart_with_last_value(value=temp_blue, unit='°C', bars=temperature_bars)

            if interactive:
                print(row)

            await asyncio.sleep(60)
    finally:
        database.close()
        relay.cleanup()


if __name__ == "__main__":
    asyncio.run(main(interactive=True))
