import unittest

from modbus.devices.waveshare_relay import WaveshareESP32S3Relay1CH


class DummyController:
    def __init__(self):
        self.writes = []
        self._coil_state = False

    def read_coils(self, address, count, unit):
        return [self._coil_state] * count

    def read_holding_registers(self, address, count, unit):
        return [int(self._coil_state)] * count

    def write_coil(self, address, value, unit):
        self.writes.append(("coil", address, bool(value), unit))
        self._coil_state = bool(value)

    def write_register(self, address, value, unit):
        self.writes.append(("register", address, value, unit))


class WaveshareRelayTests(unittest.TestCase):

    def _make_device(self):
        controller = DummyController()
        device = WaveshareESP32S3Relay1CH(controller)
        return device, controller

    def test_default_slave_id_is_7(self):
        device, _ = self._make_device()
        self.assertEqual(device.slave_address, 7)

    def test_turn_on_writes_coil_true(self):
        device, ctrl = self._make_device()
        device.turn_on()
        self.assertIn(("coil", 0, True, 7), ctrl.writes)

    def test_turn_off_writes_coil_false(self):
        device, ctrl = self._make_device()
        device.turn_off()
        self.assertIn(("coil", 0, False, 7), ctrl.writes)

    def test_set_relay_delegates_to_turn_on_and_turn_off(self):
        device, ctrl = self._make_device()
        device.set_relay(True)
        device.set_relay(False)
        self.assertIn(("coil", 0, True, 7), ctrl.writes)
        self.assertIn(("coil", 0, False, 7), ctrl.writes)

    def test_read_relay_state_reflects_coil(self):
        device, ctrl = self._make_device()
        self.assertFalse(device.read_relay_state())
        device.turn_on()
        self.assertTrue(device.read_relay_state())

    def test_read_relay_state_register_reflects_holding_register(self):
        device, ctrl = self._make_device()
        self.assertFalse(device.read_relay_state_register())
        device.turn_on()
        self.assertTrue(device.read_relay_state_register())

    def test_both_read_paths_agree(self):
        device, _ = self._make_device()
        device.turn_on()
        self.assertEqual(device.read_relay_state(), device.read_relay_state_register())
        device.turn_off()
        self.assertEqual(device.read_relay_state(), device.read_relay_state_register())


if __name__ == "__main__":
    unittest.main()
