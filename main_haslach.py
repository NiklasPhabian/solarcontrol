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
hp_nominal_power_min = config['controller']['hp_nominal_power_min']
hp_nominal_power_max = config['controller']['hp_nominal_power_max']
el_nominal_power = config['controller']['el_nominal_power']
safety_margin = config['controller']['safety_margin']
min_hp_off_seconds = config['controller']['min_hp_off_seconds']

# Temperature probes
probe_id_blue = config['temp_sensors']['blue']
probe_id_black = config['temp_sensors']['black']
probe_id_white = config['temp_sensors']['white']

# PV Relay connected to GPIO
relay_pin = config['relay']['pin']

# Displays
display_address1 = config['display1']['address']
display_address2 = config['display2']['address']
display_port1 = config['display1']['port']
display_port2 = config['display2']['port']

# Database setup
db_path = config['sqlite']['db_path']
table_name = config['sqlite']['table_name']
columns = [
    'power_mains', 'power_bwwp', 'power_mypv', 'power_wp',
    'power_pv', 'power_pv_l1', 'power_pv_l2', 'power_pv_l3',
    'temperature_blue', 'temperature_black', 'temperature_white',
    'temperature_sht', 'humidity_sht',
    'fhs280_t1', 'fhs280_t2', 'fhs280_compressor', 'fhs280_elpatron',
    'controller_state', 'fan_relay_state',
]

# Meter
meter_host = config['ecotracker']['host']

# Modbus
modbus_controler1_port = config['modbus_controller']['port']
slave_address_sht20 = config['modbus_slave_addresses']['sht20']
slave_address_sdm230_bwwp = config['modbus_slave_addresses']['sdm230_bwwp']
slave_address_sdm230_mypv = config['modbus_slave_addresses']['sdm230_mypv']
slave_address_finder7m = config['modbus_slave_addresses']['finder7m']
slave_address_sdm72dm = config['modbus_slave_addresses']['sdm72dm']
slave_address_fhs280 = config['modbus_slave_addresses']['fhs280']
slave_address_waveshare_relay = config['modbus_slave_addresses']['waveshare_relay']

# Time settings
LOG_INTERVAL = datetime.timedelta(minutes=5)
PLOT_INTERVAL = datetime.timedelta(minutes=15)

output_dir = "www"


def safe(fn, *args, **kwargs):
    """Call fn(*args, **kwargs) and return None on any exception."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        name = getattr(fn, '__qualname__', None) or getattr(fn, '__name__', repr(fn))
        print(f"[warn] {name}: {exc}")
        return None


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
    sdm72dm = modbus.devices.SDM72DM_V2(modbus_controller, slave_address_sdm72dm)
    fhs280 = modbus.devices.FHS280(modbus_controller, slave_address_fhs280)
    fan_relay = modbus.devices.WaveshareESP32S3Relay1CH(modbus_controller, slave_address_waveshare_relay)

    display1 = safe(Display, port=display_port1, address=display_address1)
    display2 = safe(Display, port=display_port2, address=display_address2)

    database = SQLiteDatabase(db_path=db_path)
    table = SQLiteTable(database=database, name=table_name, columns=columns,
                       column_types={'controller_state': 'TEXT'})
    table.create_if_not_exists()

    plotter = Plotter(table)

    bwwp_controller = Controller(hp_nominal_power_min=hp_nominal_power_min,
                                 hp_nominal_power_max=hp_nominal_power_max,
                                 el_nominal_power=el_nominal_power,
                                 safety_margin=safety_margin,
                                 min_hp_off_seconds=min_hp_off_seconds)
    fhs280_pv_relay = Relay(pin=relay_pin)
    prev_controller_state = None

    power_bars = []
    plot_files = []

    try:
        while True:
            now = datetime.datetime.now(timezone)
            timestamp = now.isoformat()

            power_mains = await power_meter.get_power()
            power_bwwp = safe(sdm_bwwp.read_active_power)
            power_mypv = safe(sdm_mypv.read_active_power)
            power_wp = safe(finder7m.read_total_active_power)
            power_pv = safe(sdm72dm.read_total_active_power)
            power_pv_l1 = safe(sdm72dm.read_active_power_l1)
            power_pv_l2 = safe(sdm72dm.read_active_power_l2)
            power_pv_l3 = safe(sdm72dm.read_active_power_l3)

            temp_blue = temperature_sensor_blue.get_temp()
            temp_black = temperature_sensor_black.get_temp()
            temp_white = temperature_sensor_white.get_temp()

            temp_sht = safe(sht20.read_temperature)
            humid_sht = safe(sht20.read_humidity)

            if power_mains is not None:
                bwwp_controller_state = bwwp_controller.control(power_mains)
            else:
                bwwp_controller_state = bwwp_controller.current_mode or "OFF"

            if bwwp_controller_state != prev_controller_state:
                mains_str = f"{power_mains:.1f}W" if power_mains is not None else "n/a"
                print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} | controller: {prev_controller_state} -> {bwwp_controller_state}  (mains={mains_str})")
                prev_controller_state = bwwp_controller_state

            if bwwp_controller_state == "HP":
                safe(fhs280_pv_relay.turn_on)
                safe(fhs280.set_solacel_only_hp)
            elif bwwp_controller_state == "EL":
                safe(fhs280_pv_relay.turn_on)
                safe(fhs280.set_solacel_only_el)
            elif bwwp_controller_state == "OFF":
                safe(fhs280_pv_relay.turn_off)
                safe(fhs280.set_solacel_off)

            fhs280_t1 = safe(fhs280.read_t1)
            fhs280_t2 = safe(fhs280.read_t2)
            fhs280_compressor = safe(fhs280.read_relay1_kompressor)
            fhs280_elpatron = safe(fhs280.read_relay2_elpatron)

            if fhs280_compressor:
                safe(fan_relay.turn_on)
            else:
                safe(fan_relay.turn_off)

            fan_relay_state = safe(fan_relay.read_relay_state)

            row = {
                "timestamp": timestamp,
                "power_mains": power_mains,
                "power_bwwp": power_bwwp,
                "power_mypv": power_mypv,
                "power_wp": power_wp,
                "power_pv": power_pv,
                "power_pv_l1": power_pv_l1,
                "power_pv_l2": power_pv_l2,
                "power_pv_l3": power_pv_l3,
                "temperature_blue": temp_blue,
                "temperature_black": temp_black,
                "temperature_white": temp_white,
                "temperature_sht": temp_sht,
                "humidity_sht": humid_sht,
                "fhs280_t1": fhs280_t1,
                "fhs280_t2": fhs280_t2,
                "controller_state": bwwp_controller_state,
                "fhs280_compressor": fhs280_compressor,
                "fhs280_elpatron": fhs280_elpatron,
                "fan_relay_state": fan_relay_state,
            }

            if now - last_log >= LOG_INTERVAL:
                table.insert_row(row)
                power_bars = table.latest_n_resampled_values(n=60, column="power_mains", aggregate="AVG", sample_interval=15)
                last_log = now

            if now - last_plot >= PLOT_INTERVAL:
                plot_files = []
                plot_files.append(plotter.plot_timeseries("power_mains", hours=24))
                plot_files.append(plotter.plot_bwwp_with_fhs280_temperatures(hours=24))
                plot_files.append(plotter.plot_avg_by_hours_of_day("power_bwwp", days=7))
                plot_files.append(plotter.plot_timeseries("power_mypv", hours=24))
                plot_files.append(plotter.plot_pv_phase_powers(hours=24, sample_interval=15))
                plot_files.append(plotter.plot_daily_trajectory("power_pv", days=30)) 
                plot_files.append(plotter.plot_avg_by_hours_of_day("power_pv", days=7))                
                last_plot = now

            html_writer = HTMLWriter(output_dir=output_dir, plot_files=plot_files, current_conditions=row)
            html_writer.write_html()

            if display1 is not None:
                safe(display1.show_chart_with_last_value, value=power_mains, unit='W', bars=power_bars)

            if display2 is not None:
                cooldown_left = bwwp_controller.hp_cooldown_remaining_seconds()
                safe(display2.show_controller_state,
                     state=bwwp_controller_state,
                     power_balance=power_mains,
                     cooldown_remaining_s=cooldown_left if bwwp_controller_state == "OFF" else None)

            if interactive:
                print(row)

            await asyncio.sleep(60)
    finally:
        database.close()
        fhs280_pv_relay.cleanup()


if __name__ == "__main__":
    asyncio.run(main(interactive=True))
