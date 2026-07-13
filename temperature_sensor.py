from config import Config


class TemperatureSensor():
    def __init__(self, serial):
        self.temp_sensor = f'/sys/bus/w1/devices/{serial}/w1_slave'

    def get_temp(self):
        try:
            with open(self.temp_sensor, 'r') as tmpfile:
                last_line = tmpfile.readlines()[-1]
                return float(last_line.split('=')[-1]) / 1000
        except FileNotFoundError:
            return None


if __name__ == '__main__':
    import time
    import datetime
    from dateutil import tz

    pst = tz.gettz('America/Los_Angeles')

    sensor_id = '28-3ce1d4438ff7' # blue
  #  sensor_id = '28-3ce1d4432b6f' # black
 #   sensor_id = '28-3ce1d44312b4' # white
    sensor = TemperatureSensor(serial=sensor_id)

    while True:
        now = datetime.datetime.now(pst)
        timestamp = now.isoformat()    
        temp = sensor.get_temp()
        print(temp)
        time.sleep(1)
