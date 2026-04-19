class TempSensor():
    def __init__(self, serial):
        self.temp_sensor = f'/sys/bus/w1/devices/{serial}/w1_slave'

    def get_temp(self):
        with open(self.temp_sensor, 'r') as tmpfile:
            last_line = tmpfile.readlines()[-1]
            temp = float(last_line.split('=')[-1]) / 1000            
        return temp


if __name__ == '__main__':
    import time
    
    sensor_ids = {  'blue':  '28-3ce1d4438ff7',
                    'black': '28-3ce1d4432b6f',
                    'white': '28-3ce1d44312b4'}

    ts1 = TempSensor(sensor_ids['blue'])
    ts2 = TempSensor(sensor_ids['black'])
    ts3 = TempSensor(sensor_ids['white'])

    while True:
        temps =    {
            'blue': ts1.get_temp(),
            'black': ts2.get_temp(),
            'white': ts3.get_temp()
        }
        print(temps)
        time.sleep(10)