import datetime
import time


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
        hp_nominal_power_min = float(hp_nominal_power_min)
        hp_nominal_power_max = float(hp_nominal_power_max)
        el_nominal_power    = float(el_nominal_power)
        safety_margin       = float(safety_margin)
        min_hp_off_seconds = float(min_hp_off_seconds)

        if hp_nominal_power_min <= 0:
            raise ValueError("hp_nominal_power_min must be > 0")
        if hp_nominal_power_max <= 0:
            raise ValueError("hp_nominal_power_max must be > 0")
        if hp_nominal_power_min > hp_nominal_power_max:
            raise ValueError("hp_nominal_power_min must be <= hp_nominal_power_max")
        if el_nominal_power <= 0:
            raise ValueError("el_nominal_power must be > 0")
        if safety_margin < 0:
            raise ValueError("safety_margin must be >= 0")
        if min_hp_off_seconds < 0:
            raise ValueError("min_hp_off_seconds must be >= 0")

        # Far in the past so HP can start immediately on first run
        self.time_turned_off_hp = datetime.datetime.now() - datetime.timedelta(days=365)
        self._hp_off_monotonic = time.monotonic() - datetime.timedelta(days=365).total_seconds()
        self.current_mode = None  # None, "HP", or "EL"

        # Power thresholds (negative = excess power flowing to grid)
        # Turn on HP from OFF: need HP max + safety margin of excess
        self.on_threshold_hp = -(hp_nominal_power_max + safety_margin)          # e.g. -600

        # Turn on EL from OFF: need full EL power + safety margin of excess
        self.on_threshold_el_from_off = -(el_nominal_power + safety_margin)     # e.g. -2050

        # Upgrade HP→EL: HP already draws hp_min, so only the delta is needed
        self.on_threshold_el_from_hp = -(el_nominal_power - hp_nominal_power_min)  # e.g. -1550

        # Turn off any device: less than safety_margin of excess remaining
        self.off_threshold = -safety_margin                                      # e.g. -50

        self.min_hp_off_seconds = int(min_hp_off_seconds)

    def seconds_since_hp_turned_off(self):
        return time.monotonic() - self._hp_off_monotonic

    def can_restart_hp(self):
        """Check if HP cooldown period has passed."""
        return self.seconds_since_hp_turned_off() >= self.min_hp_off_seconds

    def hp_cooldown_remaining_seconds(self):
        """Return remaining HP cooldown in whole seconds, clamped at 0."""
        remaining = self.min_hp_off_seconds - self.seconds_since_hp_turned_off()
        return max(0, int(remaining))

    def _mark_hp_turned_off(self):
        """Start cooldown timer when HP stops running."""
        self.time_turned_off_hp = datetime.datetime.now()
        self._hp_off_monotonic = time.monotonic()

    def control(self, power_balance):
        """Update controller state based on power balance with hysteresis.

        Power convention: negative = excess solar being exported to grid.

        State machine:

          OFF ──(< on_threshold_hp)──────────────────► HP
          OFF ──(< on_threshold_el_from_off)─────────► EL

          HP  ──(>= off_threshold)────────────────────► OFF  (stamps cooldown timer)
          HP  ──(< on_threshold_el_from_hp)───────────► EL   (stamps cooldown timer)

          EL  ──(>= off_threshold)────────────────────► OFF  (no cooldown stamp)

        There is intentionally no direct EL→HP transition.  When excess solar
        drops while in EL mode the controller goes EL→OFF, from which HP can
        restart once the cooldown has passed.  A direct EL→HP shortcut would
        create an oscillation: switching from EL to HP lowers apparent load by
        ~1500 W, making the new power_balance cross the HP→EL threshold
        immediately and bouncing indefinitely.
        """
        if self.current_mode is None or self.current_mode == "OFF":
            if power_balance < self.on_threshold_el_from_off:
                self.current_mode = "EL"
            elif power_balance < self.on_threshold_hp:
                if self.can_restart_hp():
                    self.current_mode = "HP"
                else:
                    self.current_mode = "OFF"
            else:
                self.current_mode = "OFF"

        elif self.current_mode == "HP":
            if power_balance >= self.off_threshold:
                self._mark_hp_turned_off()
                self.current_mode = "OFF"
            elif power_balance < self.on_threshold_el_from_hp:
                # Stamp the timer so a rapid EL→OFF→HP cycle still respects cooldown
                self._mark_hp_turned_off()
                self.current_mode = "EL"
            # else: stay in HP

        elif self.current_mode == "EL":
            if power_balance >= self.off_threshold:
                self.current_mode = "OFF"
            # else: stay in EL — no direct EL→HP transition (see docstring)

        return self.current_mode
