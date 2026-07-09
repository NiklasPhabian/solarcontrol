import unittest

from modbus.devices.waveshare_relay import WaveshareESP32S3Relay1CH


class DummyController:
    def __init__(self):
        self.writes = []
        self.reads = []
        self.registers = [7]

    def read_coils(self, address, count, unit):
        self.reads.append(("coil", address, count, unit))
        return [False] * count

    def read_holding_registers(self, address, count, unit):
        self.reads.append(("holding", address, count, unit))
        return self.registers[:count]

    def write_coil(self, address, value, unit):
        self.writes.append((address, value, unit))

    def write_register(self, address, value, unit):
        self.writes.append((address, value, unit))
        self.registers[0] = value


class WaveshareRelayTests(unittest.TestCase):
    def test_relay_state_helpers_use_the_single_relay_coil_and_address_register(self):
        controller = DummyController()
        device = WaveshareESP32S3Relay1CH(controller, 1)

        self.assertFalse(device.read_relay_state())
        self.assertEqual(device.read_slave_address(), 7)

        device.turn_on()
        device.turn_off()
        device.set_slave_address(9)

        self.assertIn((0, True, 1), controller.writes)
        self.assertIn((0, False, 1), controller.writes)
        self.assertIn((0, 9, 1), controller.writes)
        self.assertEqual(device.slave_address, 9)


if __name__ == "__main__":
    unittest.main()
