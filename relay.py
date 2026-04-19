import RPi.GPIO as GPIO


class Relay:

    def __init__(self, pin: int):
        self.pin = int(pin)
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)

        self.active_high = True  # or False depending on relay
        self.off_gpio_state = GPIO.HIGH if self.active_high else GPIO.LOW
        self.on_gpio_state = GPIO.LOW if self.active_high else GPIO.HIGH

        self.on = False
        self.turn_off()

    def apply_state(self, state: bool):
        if state and not self.on:
            self.turn_on()
        elif not state and self.on:
            self.turn_off()

    def turn_off(self):
        self.on = False
        GPIO.output(self.pin, self.off_gpio_state)

    def turn_on(self):
        self.on = True
        GPIO.output(self.pin, self.on_gpio_state)


if __name__ == "__main__":
    import time
    relay = Relay(17)  
    try:
        while True:
            relay.turn_on()
            time.sleep(1)
            relay.turn_off()
            time.sleep(1)
    finally:
        GPIO.cleanup()