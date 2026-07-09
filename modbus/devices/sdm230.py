"""SDM230 single-phase energy meter device abstraction."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from ..transport import ModbusController
except ImportError:  # pragma: no cover - fallback for direct script execution
    from modbus.transport import ModbusController

try:
    from .base import ModbusDevice
except ImportError:  # pragma: no cover - fallback for direct script execution
    from modbus.devices.base import ModbusDevice

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_SLAVE_ADDRESS = 2


class SDM230(ModbusDevice):
    """SDM230 single-phase energy meter (Modbus RTU) abstraction."""

    REG_VOLTAGE = 0x0000
    REG_CURRENT = 0x0006
    REG_ACTIVE_POWER = 0x000C
    REG_APPARENT_POWER = 0x0012
    REG_REACTIVE_POWER = 0x0018
    REG_POWER_FACTOR = 0x001E
    REG_FREQUENCY = 0x0046
    REG_IMPORT_ENERGY = 0x0156
    REG_EXPORT_ENERGY = 0x0158
    REG_TOTAL_ENERGY = 0x015A

    def read_voltage(self) -> float:
        return self.read_float32(self.REG_VOLTAGE, input_registers=True)

    def read_current(self) -> float:
        return self.read_float32(self.REG_CURRENT, input_registers=True)

    def read_active_power(self) -> float:
        return self.read_float32(self.REG_ACTIVE_POWER, input_registers=True)

    def read_apparent_power(self) -> float:
        return self.read_float32(self.REG_APPARENT_POWER, input_registers=True)

    def read_reactive_power(self) -> float:
        return self.read_float32(self.REG_REACTIVE_POWER, input_registers=True)

    def read_power_factor(self) -> float:
        return self.read_float32(self.REG_POWER_FACTOR, input_registers=True)

    def read_frequency(self) -> float:
        return self.read_float32(self.REG_FREQUENCY, input_registers=True)

    def read_import_active_energy(self) -> float:
        return self.read_float32(self.REG_IMPORT_ENERGY, input_registers=True)

    def read_export_active_energy(self) -> float:
        return self.read_float32(self.REG_EXPORT_ENERGY, input_registers=True)

    def read_total_active_energy(self) -> float:
        return self.read_float32(self.REG_TOTAL_ENERGY, input_registers=True)

    def read_multiple(self, regs: list[int]) -> dict:
        results: dict = {}
        for r in regs:
            results[r] = self.read_float32(r, input_registers=True)
        return results


def main() -> None:
    controller = ModbusController(port=DEFAULT_PORT)
    controller.connect()
    slave_address = 2
    try:
        meter = SDM230(controller, slave_address=slave_address)
        print(
            f"SDM230 @ {slave_address}: voltage={meter.read_voltage():.2f} V "
            f"current={meter.read_current():.3f} A"
        )
    finally:
        controller.close()


__all__ = ["SDM230"]


if __name__ == "__main__":
    main()