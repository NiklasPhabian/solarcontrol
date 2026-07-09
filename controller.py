
import datetime


class Controller:

    def __init__(self, hp_nominal_power_min, hp_nominal_power_max, el_nominal_power, safety_margin, min_hp_off_seconds):
        """Initialize the heating controller.
        
        Args:
            hp_nominal_power_min: Minimum HP consumption in watts (e.g., 450)
            hp_nominal_power_max: Maximum HP consumption in watts (e.g., 550)
            el_nominal_power: EL consumption in watts (e.g., 2000)
            safety_margin: Safety margin for both HP and EL (e.g., 50)
            min_hp_off_seconds: Minimum seconds HP must stay off before restarting
        """
        self.time_turned_off_hp = datetime.datetime.now() - datetime.timedelta(days=365)  # Far in the past so HP can start immediately
        self.current_mode = None  # None, "HP", or "EL"

        # Power thresholds (negative = excess power)
        # Turn on HP from OFF: need HP max (worst case) + safety margin
        self.on_threshold_hp = -(hp_nominal_power_max + safety_margin)  # e.g., -600
        
        # Turn on EL from OFF: need full EL power + safety margin
        self.on_threshold_el_from_off = -(el_nominal_power + safety_margin)  # e.g., -2050
        
        # Switch from HP to EL: use HP min (conservative) to get required additional power
        # If HP is at minimum consumption, we need the most additional power
        self.on_threshold_el_from_hp = -(el_nominal_power - hp_nominal_power_min)  # e.g., -1550
        
        # OFF threshold: turn off devices if power is above this (less excess power)
        # This creates hysteresis: turn on at thresholds, turn off at off_threshold
        self.off_threshold = -safety_margin  # e.g., -50
        
        self.safety_margin = safety_margin
        self.min_hp_off_seconds = int(min_hp_off_seconds)

    def seconds_since_hp_turned_off(self):
        return (datetime.datetime.now() - self.time_turned_off_hp).total_seconds()

    def can_restart_hp(self):
        """Check if HP cooldown period has passed."""
        return self.seconds_since_hp_turned_off() > self.min_hp_off_seconds

    def control(self, power_balance):
        """Update controller state based on power balance with hysteresis.
        
        Uses asymmetric thresholds to prevent oscillation:
        - Turn ON devices at aggressive thresholds (low excess power)
        - Turn OFF or SWITCH devices only when power returns to clear zones
        
        Power zones (negative = excess power):
        - power >= off_threshold (-50): insufficient for any device → OFF
        - on_threshold_hp > power >= off_threshold (-600 to -50): marginal → stay OFF or try HP
        - on_threshold_el_from_hp > power >= on_threshold_hp (-1550 to -600): HP zone
        - on_threshold_el_from_off > power >= on_threshold_el_from_hp (-2050 to -1550): ambiguous (stay in current mode)
        - power < on_threshold_el_from_off (-2050): strong EL zone
        """
        # Currently OFF
        if self.current_mode is None or self.current_mode == "OFF":
            # Try to turn on EL directly if power is very high
            if power_balance < self.on_threshold_el_from_off:
                self.current_mode = "EL"
            # Try to turn on HP if power is sufficient
            elif power_balance < self.on_threshold_hp:
                if self.can_restart_hp():
                    self.current_mode = "HP"
                else:
                    self.current_mode = "OFF"
            else:
                self.current_mode = "OFF"
        
        # Currently in HP mode
        elif self.current_mode == "HP":
            # Check if we should turn off (insufficient power)
            if power_balance >= self.off_threshold:
                self.time_turned_off_hp = datetime.datetime.now()
                self.current_mode = "OFF"
            # Check if we should switch to EL (plenty of power)
            elif power_balance < self.on_threshold_el_from_hp:
                self.current_mode = "EL"
            # else: stay in HP mode
        
        # Currently in EL mode
        elif self.current_mode == "EL":
            # Check if we should turn off (insufficient power)
            if power_balance >= self.off_threshold:
                self.current_mode = "OFF"
            # Check if we're back in HP zone (power dropped enough to switch to lower consumption)
            elif power_balance >= self.on_threshold_hp:
                if self.can_restart_hp():
                    self.current_mode = "HP"
                else:
                    # Cooldown hasn't passed, turn off instead of staying in EL
                    self.current_mode = "OFF"
            # else: stay in EL mode (still in deep EL zone or ambiguous hysteresis zone)
        
        return self.current_mode


async def main():
    from energy_meter import EcoTracker
    import time
    from relay import Relay

    power_meter = EcoTracker(host='192.168.178.115')
    controller = Controller(on_threshold_hp=-500, on_threshold_el=-100, off_threshold=0, min_off_seconds=10)
    relay = Relay(pin='17')

    while True:
        power = await power_meter.get_power()
        state = controller.control(power)
        relay.apply_state(state)
        print(f'{power}, {state}')
        time.sleep(5)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
