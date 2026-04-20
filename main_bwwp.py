from config import Config
from meter import EnergyMeter
from controller import Controller
from relay import Relay
from display import Display
from database import SQLiteDatabase
from dateutil import tz
from temperature_sensor import TemperatureSensor
import time
import datetime
import atexit


pst = tz.gettz('America/Los_Angeles')

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
display1 = Display(port=port1, address=address1)
display2 = Display(port=port2, address=address2)

# Database setup
db_path = config['sqlite']['db_path']
table_name = config['sqlite']['table_name']
database = SQLiteDatabase(db_path=db_path, table_name=table_name)

# Meter
device = config['meter']['meter_device']
host = config['meter']['host']
username = config['kasa']['username']
password = config['kasa']['password']
meter = EnergyMeter(device=device, host=host, username=username, password=password)
atexit.register(meter.disconnect)

def main():

    while True:
        now = datetime.datetime.now(pst)
        timestamp = now.isoformat()
        
        power = meter.get_power()
        state = controller.control(power)
        relay.apply_state(state)

        temp_blue = ts_blue.get_temp()
        temp_black = ts_black.get_temp()
        temp_white = ts_white.get_temp()

        #database.log(power, state)
        display1.display_watts(power)
        display2.display_celsius(temp_blue)

        print({'timestamp': timestamp, 'power': power, 'state': state, 'temp_blue': temp_blue, 'temp_black': temp_black, 'temp_white': temp_white})
        time.sleep(5)



if __name__ == "__main__":
    main()
