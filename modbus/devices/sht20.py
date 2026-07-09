"""SHT20 temperature and humidity sensor device abstraction."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple

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
DEFAULT_SLAVE_ADDRESS = 1


class SHT20(ModbusDevice):
    """SHT20 temperature & humidity sensor (Modbus RTU)."""

    _REG_TEMPERATURE = 0x0001
    _REG_HUMIDITY = 0x0002

    _REG_DEVICE_ADDR = 0x0101
    _REG_BAUDRATE = 0x0102
    _REG_TEMP_OFFSET = 0x0103
    _REG_HUM_OFFSET = 0x0104

    def read_temperature(self) -> float:
        regs = self.read_input_registers(self._REG_TEMPERATURE, count=1)
        if not regs:
            raise RuntimeError("No response reading temperature")
        raw = regs[0]
        if raw & 0x8000:
            raw = raw - 0x10000
        return raw / 10.0

    def read_humidity(self) -> float:
        regs = self.read_input_registers(self._REG_HUMIDITY, count=1)
        if not regs:
            raise RuntimeError("No response reading humidity")
        raw = regs[0]
        return raw / 10.0

    def read_temperature_humidity(self) -> Tuple[float, float]:
        regs = self.read_input_registers(self._REG_TEMPERATURE, count=2)
        if not regs or len(regs) < 2:
            raise RuntimeError("No response reading temperature+humidity")
        t_raw, h_raw = regs[0], regs[1]
        if t_raw & 0x8000:
            t_raw = t_raw - 0x10000
        return (t_raw / 10.0, h_raw / 10.0)

    def read_device_address(self) -> int:
        regs = self.read_holding_registers(self._REG_DEVICE_ADDR, count=1)
        return int(regs[0])


def main() -> None:
    controller = ModbusController(port='/dev/ttyUSB0')
    controller.connect()
    try:
        sensor = SHT20(controller, 1)
        temperature, humidity = sensor.read_temperature_humidity()
        print(f"SHT20 @ {DEFAULT_SLAVE_ADDRESS}: temperature={temperature:.1f} C humidity={humidity:.1f} %")
    finally:
        controller.close()


__all__ = ["SHT20"]


if __name__ == "__main__":
    main()
