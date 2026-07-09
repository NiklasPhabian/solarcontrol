import unittest

from modbus.devices.fhs280 import FHS280


class DummyController:
    def __init__(self):
        self.writes = []
        self.reads = []

    def read_holding_registers(self, address, count, unit):
        self.reads.append(("holding", address, count, unit))
        return [0] * count

    def read_input_registers(self, address, count, unit):
        self.reads.append(("input", address, count, unit))
        return [0] * count

    def write_register(self, address, value, unit):
        self.writes.append((address, value, unit))


class FHS280Tests(unittest.TestCase):
    def test_holding_register_helpers_use_documented_addresses(self):
        controller = DummyController()
        device = FHS280(controller, 1)

        self.assertEqual(device.read_setpoint(), 0)
        self.assertEqual(device.read_holiday(), 0)
        self.assertEqual(device.read_modbus_address(), 0)

        device.write_setpoint(25)
        device.write_holiday(3)
        device.write_modbus_address(42)

        self.assertIn((4, 25, 1), controller.writes)
        self.assertIn((20, 3, 1), controller.writes)
        self.assertIn((114, 42, 1), controller.writes)

    def test_input_temperature_helpers_scale_by_tenth(self):
        controller = DummyController()
        device = FHS280(controller, 1)

        controller.reads = []

        class InputController(DummyController):
            def read_input_registers(self, address, count, unit):
                self.reads.append(("input", address, count, unit))
                if address == 7:
                    return [250]
                if address == 8:
                    return [315]
                return [0]

        controller = InputController()
        device = FHS280(controller, 1)

        self.assertEqual(device.read_t1(), 25.0)
        self.assertEqual(device.read_t2(), 31.5)

    def test_relay_status_helpers_return_booleans(self):
        controller = DummyController()
        device = FHS280(controller, 1)

        class InputController(DummyController):
            def read_input_registers(self, address, count, unit):
                self.reads.append(("input", address, count, unit))
                if address == 9:
                    return [1]
                if address == 10:
                    return [0]
                return [0]

        controller = InputController()
        device = FHS280(controller, 1)

        self.assertTrue(device.read_relay1_kompressor())
        self.assertFalse(device.read_relay2_elpatron())

    def test_state_parsing_methods_return_strings(self):
        controller = DummyController()
        device = FHS280(controller, 1)

        class HoldingController(DummyController):
            def read_holding_registers(self, address, count, unit):
                self.reads.append(("holding", address, count, unit))
                if address == 17:  # solacel
                    return [2]
                if address == 20:  # holiday
                    return [3]
                if address == 12:  # hp_pump
                    return [3]
                return [0]

        controller = HoldingController()
        device = FHS280(controller, 1)

        self.assertEqual(device.read_solacel_state(), "Only EL")
        self.assertEqual(device.read_holiday_state(), "3 Weeks")
        self.assertEqual(device.read_hp_pump_state(), "HP+EL")


if __name__ == "__main__":
    unittest.main()
