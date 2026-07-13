import unittest
import datetime
import time
from controller import Controller


def make_controller(**kwargs):
    defaults = dict(
        hp_nominal_power_min=450,
        hp_nominal_power_max=550,
        el_nominal_power=2000,
        safety_margin=50,
        min_hp_off_seconds=300,
    )
    defaults.update(kwargs)
    return Controller(**defaults)


class TestOffState(unittest.TestCase):
    def test_stays_off_with_insufficient_excess(self):
        c = make_controller()
        self.assertEqual(c.control(-30), "OFF")   # only 30 W excess, need 600

    def test_starts_hp_with_moderate_excess(self):
        c = make_controller()
        self.assertEqual(c.control(-700), "HP")   # 700 W excess, threshold -600

    def test_starts_el_directly_with_high_excess(self):
        c = make_controller()
        self.assertEqual(c.control(-2100), "EL")  # 2100 W excess, threshold -2050

    def test_hp_blocked_by_cooldown(self):
        c = make_controller(min_hp_off_seconds=300)
        c.time_turned_off_hp = datetime.datetime.now()   # keep wall-clock stamp for observability
        c._hp_off_monotonic = time.monotonic()           # just turned off
        self.assertEqual(c.control(-700), "OFF")

    def test_hp_does_not_start_exactly_at_threshold(self):
        c = make_controller()
        self.assertEqual(c.control(-600), "OFF")

    def test_el_exact_threshold_falls_back_to_hp_zone(self):
        c = make_controller()
        # At exact EL threshold, EL does not start (strict <), but HP still can.
        self.assertEqual(c.control(-2050), "HP")


class TestHPMode(unittest.TestCase):
    def _in_hp(self):
        c = make_controller()
        c.control(-700)   # enter HP
        return c

    def test_stays_in_hp_with_stable_excess(self):
        c = self._in_hp()
        self.assertEqual(c.control(-700), "HP")

    def test_turns_off_when_excess_disappears(self):
        c = self._in_hp()
        self.assertEqual(c.control(-20), "OFF")   # above off_threshold (-50)

    def test_off_stamps_cooldown_timer(self):
        c = self._in_hp()
        before = datetime.datetime.now()
        c.control(-20)
        self.assertGreaterEqual(c.time_turned_off_hp, before)

    def test_upgrades_to_el_with_high_excess(self):
        c = self._in_hp()
        self.assertEqual(c.control(-1600), "EL")  # 1600 W excess, threshold -1550

    def test_hp_does_not_upgrade_to_el_at_exact_threshold(self):
        c = self._in_hp()
        self.assertEqual(c.control(-1550), "HP")

    def test_hp_to_el_stamps_cooldown_timer(self):
        """HP→EL must stamp the cooldown so a rapid EL→OFF→HP cycle is throttled."""
        c = self._in_hp()
        before = datetime.datetime.now()
        c.control(-1600)   # HP → EL
        self.assertGreaterEqual(c.time_turned_off_hp, before)


class TestELMode(unittest.TestCase):
    def _in_el(self):
        c = make_controller()
        c.control(-2100)   # enter EL
        return c

    def test_stays_in_el_with_high_excess(self):
        c = self._in_el()
        self.assertEqual(c.control(-2100), "EL")

    def test_turns_off_when_excess_drops_below_margin(self):
        c = self._in_el()
        self.assertEqual(c.control(-20), "OFF")

    def test_el_to_off_does_not_stamp_hp_cooldown_timer(self):
        c = self._in_el()
        old_wall = c.time_turned_off_hp
        old_mono = c._hp_off_monotonic
        self.assertEqual(c.control(-20), "OFF")
        self.assertEqual(c.time_turned_off_hp, old_wall)
        self.assertEqual(c._hp_off_monotonic, old_mono)

    def test_no_direct_el_to_hp_transition(self):
        """EL must go through OFF — a direct EL→HP would cause oscillation."""
        c = self._in_el()
        # power in the HP zone (600–2050 W excess, with EL running)
        result = c.control(-700)
        self.assertNotEqual(result, "HP", "EL→HP direct transition causes oscillation; must go via OFF")
        self.assertEqual(result, "EL")   # still enough excess to stay in EL

    def test_el_stays_when_hp_cooldown_not_expired(self):
        """EL must NOT turn off just because HP cooldown is active — solar still covers EL."""
        c = self._in_el()
        c.time_turned_off_hp = datetime.datetime.now()   # keep wall-clock stamp for observability
        c._hp_off_monotonic = time.monotonic()           # cooldown active
        # power_balance = -700: EL is sustainable (exporting 700 W), stay in EL
        self.assertEqual(c.control(-700), "EL")


class TestOscillationFreedom(unittest.TestCase):
    def test_no_oscillation_at_boundary_solar(self):
        """At solar ≈ 2600 W the old code oscillated EL↔HP every cycle; must be stable."""
        c = make_controller()
        # Enter EL from OFF (high solar burst)
        c.control(-2100)
        states = [c.control(-600) for _ in range(5)]   # solar settles at 2600 W (with EL: pb=-600)
        self.assertTrue(
            all(s == states[0] for s in states),
            f"Mode oscillated: {states}",
        )


class TestCooldownBoundary(unittest.TestCase):
    def test_hp_can_restart_at_exact_cooldown(self):
        c = make_controller(min_hp_off_seconds=300)
        c.current_mode = "OFF"
        c._hp_off_monotonic = time.monotonic() - 300
        self.assertEqual(c.control(-700), "HP")


class TestCooldownHelpers(unittest.TestCase):
    def test_remaining_cooldown_is_positive_before_expiry(self):
        c = make_controller(min_hp_off_seconds=300)
        c._hp_off_monotonic = time.monotonic() - 120
        remaining = c.hp_cooldown_remaining_seconds()
        self.assertGreaterEqual(remaining, 179)
        self.assertLessEqual(remaining, 181)

    def test_remaining_cooldown_clamps_to_zero(self):
        c = make_controller(min_hp_off_seconds=300)
        c._hp_off_monotonic = time.monotonic() - 301
        self.assertEqual(c.hp_cooldown_remaining_seconds(), 0)


class TestValidation(unittest.TestCase):
    def test_rejects_inverted_hp_range(self):
        with self.assertRaises(ValueError):
            make_controller(hp_nominal_power_min=600, hp_nominal_power_max=550)

    def test_rejects_negative_safety_margin(self):
        with self.assertRaises(ValueError):
            make_controller(safety_margin=-1)

    def test_rejects_negative_cooldown(self):
        with self.assertRaises(ValueError):
            make_controller(min_hp_off_seconds=-1)


if __name__ == "__main__":
    unittest.main()
