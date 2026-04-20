import datetime
import asyncio
import dateutil
from config import Config
from database import SQLiteDatabase, SQLiteTable
from energy_meter import KasaEnergyMeter
from display import Display
from temperature_sensor import TemperatureSensor

config = Config('config_bishop.ini')

timezone_str = config['timezone']['tz']
timezone = dateutil.tz.gettz(timezone_str)

# Database setup
db_path = config['sqlite']['db_path']
table_name = config['sqlite']['table_name']

# Kasa setup
username = config['kasa']['username']
password = config['kasa']['password']

# Meter setup
host_pv = config['meter_pv']['host']
host_fridge = config['meter_fridge']['host']
host_dishwasher = config['meter_dishwasher']['host']

# Temperature sensor setup (optional)
indoor_sensor_id = config['temp_sensors']['indoor']

# Display setup
address = config['display']['address']
port = config['display']['port']

LOG_INTERVAL = datetime.timedelta(minutes=5)

async def main() -> None:    
    last_log = datetime.datetime.min.replace(tzinfo=timezone)

    meter_pv = KasaEnergyMeter(host=host_pv, username=username, password=password)
    meter_fridge = KasaEnergyMeter(host=host_fridge, username=username, password=password)
    meter_dishwasher = KasaEnergyMeter(host=host_dishwasher, username=username, password=password)

    display = Display(port=port, address=address)
    temp_sensor = TemperatureSensor(serial=indoor_sensor_id)

    database = SQLiteDatabase(db_path=db_path)
    db_table = SQLiteTable(database=database, name=table_name, columns=['power_pv', 'power_fridge', 'power_dishwasher', 'temperature'])
    db_table.create_if_not_exists()
    
    try:
        while True:
            now = datetime.datetime.now(timezone)
            timestamp = now.isoformat()

            power_pv = await meter_pv.get_power()
            power_fridge = await meter_fridge.get_power()
            power_dishwasher = await meter_dishwasher.get_power()
            temperature = temp_sensor.get_temp()

            row = {
                "timestamp": timestamp,
                "power_pv": power_pv,
                "power_fridge": power_fridge,
                "power_dishwasher": power_dishwasher,
                "temperature": temperature
            }

            if now - last_log >= LOG_INTERVAL:
                db_table.insert_row(row)        
                bars = db_table.latest_n_resampled_values(n=60, column="power_pv", aggregate="AVG", sample_interval=15)   
                last_log = now
            
            display.show_chart_with_last_value(value=power_pv, unit='W', bars=bars)                 
            print(row)

            await asyncio.sleep(10)
    finally:
        await meter_pv.disconnect()
        await meter_fridge.disconnect()
        await meter_dishwasher.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
