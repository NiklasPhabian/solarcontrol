import RPi.GPIO as GPIO
import datetime
from config import Config

config = Config()
feed_in_threshold = config['controller']['feed_in_threshold']
consumption_threshold = config['controller']['consumption_threshold']
min_on_seconds = config['controller']['min_on_seconds']

class Controller:
    
    def __init__(self, cursor=None):
        self.channel = 22
        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.channel, GPIO.OUT)
        self.on = None
        self.cursor = cursor

    def get_state(self):
        query = 'SELECT on FROM solarthermal ORDER BY timestamp DESC LIMIT 1'
        self.cursor.execute(query)
        self.on = bool(self.cursor.fetchone()[0])

    def get_seconds_since_on(self):
        query = 'SELECT timestamp FROM bwwp WHERE on=1 ORDER BY timestamp DESC LIMIT 1'
        self.cursor.execute(query)
        last_time_on = self.cursor.fetchone()[0]
        last_time_on = datetime.datetime.strptime(last_time_on, '%Y-%m-%d %H:%M:%S.%f')
        self.seconds_since_on = (datetime.datetime.now()-last_time_on).total_seconds()

    def control(self, power):
        if power < feed_in_threshold and not self.on:
            print("Feed-in above threshold. Turning on")
            self.turn_on()
        elif power > consumption_threshold and self.seconds_since_on > min_on_seconds and self.on:
            print("Consumption above threshold. Turning off")
            self.turn_off()
    
    def turn_off(self):
        self.on = False
        GPIO.output(self.channel, GPIO.LOW)
    
    def turn_on(self):
        self.on = True
        GPIO.output(self.channel, GPIO.HIGH)