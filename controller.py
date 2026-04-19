
import datetime


class Controller:
    
    def __init__(self, on_threshold, off_threshold, min_on_seconds, min_off_seconds):
        self.turned_on = False
        self.time_turned_on = None
        self.time_turned_off = datetime.datetime.now()
        
        self.min_on_seconds = int(min_on_seconds)
        self.min_off_seconds = int(min_off_seconds)

        self.on_threshold = float(on_threshold)
        self.off_threshold = float(off_threshold)
        
    def seconds_since_on(self):
        return (datetime.datetime.now()-self.time_turned_on).total_seconds()

    def seconds_since_off(self):
        return (datetime.datetime.now()-self.time_turned_off).total_seconds()

    def should_turn_on(self, power_balance):
        should_turn_on = False
        if not self.turned_on:
            if power_balance < self.on_threshold:
                if self.seconds_since_off() > self.min_off_seconds:
                    should_turn_on = True
        return should_turn_on


    def should_turn_off(self, power_balance):
        should_turn_off = False
        if self.turned_on:
            if power_balance > self.off_threshold:
                if self.seconds_since_on() > self.min_on_seconds:
                    should_turn_off = True
        return should_turn_off

    def control(self, power_balance):
        if self.should_turn_on(power_balance):
            self.turned_on = True
            self.time_turned_on = datetime.datetime.now()
        elif self.should_turn_off(power_balance):
            self.turned_on = False
            self.time_turned_off = datetime.datetime.now()
        return self.turned_on