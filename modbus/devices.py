"""Device-specific Modbus abstractions: SHT20 and SDM230.

This module contains high-level device wrappers that use the transport
layer in `modbus.transport`.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Tuple, List, Sequence, Optional, Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from .transport import ModbusController
except ImportError:  # pragma: no cover - fallback for direct script execution
    from modbus.transport import ModbusController

try:
    from pymodbus.constants import Endian
except Exception:
    Endian = None  # type: ignore


class ModbusDevice:
    """A Modbus slave device attached to the adapter bus.

    This base class provides convenience wrappers around a `ModbusController`
    instance for common read/write and typed-decoding operations.
    """

    DEFAULT_WORDORDER: Optional[Any] = "big"
    DEFAULT_BYTEORDER: Optional[Any] = "big"

    def __init__(self, controller: ModbusController, slave_address: int) -> None:
        self.controller = controller
        self.slave_address = int(slave_address)

    def read_coils(self, address: int, count: int = 1) -> List[bool]:
        return self.controller.read_coils(address, count, unit=self.slave_address)

    def read_discrete_inputs(self, address: int, count: int = 1) -> List[bool]:
        return self.controller.read_discrete_inputs(address, count, unit=self.slave_address)

    def read_holding_registers(self, address: int, count: int = 1) -> List[int]:
        return self.controller.read_holding_registers(address, count, unit=self.slave_address)

    def read_input_registers(self, address: int, count: int = 1) -> List[int]:
        return self.controller.read_input_registers(address, count, unit=self.slave_address)

    def write_coil(self, address: int, value: bool) -> None:
        self.controller.write_coil(address, value, unit=self.slave_address)

    def write_register(self, address: int, value: int) -> None:
        self.controller.write_register(address, value, unit=self.slave_address)

    def write_registers(self, address: int, values: Sequence[int]) -> None:
        self.controller.write_registers(address, values, unit=self.slave_address)

    def read_uint16(self, address: int, input_registers: bool = False) -> int:
        registers = self._read_registers(address, count=1, input_registers=input_registers)
        return self._decode(registers, "uint16")

    def read_int16(self, address: int, input_registers: bool = False) -> int:
        registers = self._read_registers(address, count=1, input_registers=input_registers)
        return self._decode(registers, "int16")

    def read_uint32(
        self,
        address: int,
        input_registers: bool = False,
        wordorder: Optional[Any] = None,
    ) -> int:
        registers = self._read_registers(address, count=2, input_registers=input_registers)
        return self._decode(registers, "uint32", wordorder=wordorder)

    def read_int32(
        self,
        address: int,
        input_registers: bool = False,
        wordorder: Optional[Any] = None,
    ) -> int:
        registers = self._read_registers(address, count=2, input_registers=input_registers)
        return self._decode(registers, "int32", wordorder=wordorder)

    def read_float32(
        self,
        address: int,
        input_registers: bool = False,
        wordorder: Optional[Any] = None,
        byteorder: Optional[Any] = None,
    ) -> float:
        if wordorder is None:
            wordorder = self.DEFAULT_WORDORDER
        if byteorder is None:
            byteorder = self.DEFAULT_BYTEORDER
        registers = self._read_registers(address, count=2, input_registers=input_registers)
        return self._decode(
            registers,
            "float32",
            wordorder=wordorder,
            byteorder=byteorder,
        )

    def read_string(
        self,
        address: int,
        count: int,
        input_registers: bool = False,
        encoding: str = "ascii",
        wordorder: Optional[Any] = None,
        byteorder: Optional[Any] = None,
    ) -> str:
        registers = self._read_registers(address, count=count, input_registers=input_registers)
        raw = self._registers_to_bytes(registers, wordorder=wordorder, byteorder=byteorder)
        return raw.decode(encoding, errors="ignore").rstrip("\x00")

    def _read_registers(
        self,
        address: int,
        count: int,
        input_registers: bool = False,
    ) -> List[int]:
        if input_registers:
            return self.read_input_registers(address, count)
        return self.read_holding_registers(address, count)

    @staticmethod
    def _normalize_endian(order: Optional[Any]) -> Optional[str]:
        if order is None:
            return None
        if Endian is not None:
            little = getattr(Endian, "Little", None)
            big = getattr(Endian, "Big", None)
            if order in (little, big):
                return "little" if order == little else "big"
        value = str(order).lower()
        if "little" in value:
            return "little"
        if "big" in value:
            return "big"
        return None

    @staticmethod
    def _registers_to_bytes(
        registers: List[int],
        wordorder: Optional[Any] = None,
        byteorder: Optional[Any] = None,
    ) -> bytes:
        wordorder_str = ModbusDevice._normalize_endian(wordorder)
        byteorder_str = ModbusDevice._normalize_endian(byteorder)
        regs = list(registers)
        if wordorder_str == "little":
            regs.reverse()
        raw = bytearray()
        for reg in regs:
            chunk = reg.to_bytes(2, "big")
            if byteorder_str == "little":
                chunk = chunk[::-1]
            raw.extend(chunk)
        return bytes(raw)

    @staticmethod
    def _decode(
        registers: List[int],
        data_type: str,
        wordorder: Optional[Any] = None,
        byteorder: Optional[Any] = None,
    ) -> Any:
        if not registers:
            raise ValueError("No registers to decode")

        if data_type == "uint16":
            return registers[0]
        if data_type == "int16":
            value = registers[0]
            return value - 0x10000 if value & 0x8000 else value

        raw = ModbusDevice._registers_to_bytes(registers, wordorder=wordorder, byteorder=byteorder)
        if data_type == "uint32":
            return struct.unpack(">I", raw)[0]
        if data_type == "int32":
            return struct.unpack(">i", raw)[0]
        if data_type == "float32":
            return struct.unpack(">f", raw)[0]

        raise ValueError(f"Unsupported decode type: {data_type}")


class SHT20(ModbusDevice):
    """SHT20 temperature & humidity sensor (Modbus RTU).

    See device register map in docstring in the repository.
    """

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

    # Configuration helpers
    def read_device_address(self) -> int:
        regs = self.read_holding_registers(self._REG_DEVICE_ADDR, count=1)
        return int(regs[0])


class ThreePhaseEnergyMeter(ModbusDevice):
    """Common 3-phase energy meter abstraction for SDM630/Finder-style meters."""

    REG_CURRENT_L1: int
    REG_CURRENT_L2: int
    REG_CURRENT_L3: int
    REG_ACTIVE_POWER_L1: int
    REG_ACTIVE_POWER_L2: int
    REG_ACTIVE_POWER_L3: int
    REG_TOTAL_ACTIVE_POWER: int
    REG_FREQUENCY: int

    def read_current_l1(self) -> float:
        return self.read_float32(self.REG_CURRENT_L1, input_registers=True)

    def read_current_l2(self) -> float:
        return self.read_float32(self.REG_CURRENT_L2, input_registers=True)

    def read_current_l3(self) -> float:
        return self.read_float32(self.REG_CURRENT_L3, input_registers=True)

    def read_phase_currents(self) -> tuple[float, float, float]:
        return (
            self.read_current_l1(),
            self.read_current_l2(),
            self.read_current_l3(),
        )

    def read_active_power_l1(self) -> float:
        return self.read_float32(self.REG_ACTIVE_POWER_L1, input_registers=True)

    def read_active_power_l2(self) -> float:
        return self.read_float32(self.REG_ACTIVE_POWER_L2, input_registers=True)

    def read_active_power_l3(self) -> float:
        return self.read_float32(self.REG_ACTIVE_POWER_L3, input_registers=True)

    def read_phase_active_powers(self) -> tuple[float, float, float]:
        return (
            self.read_active_power_l1(),
            self.read_active_power_l2(),
            self.read_active_power_l3(),
        )

    def read_total_active_power(self) -> float:
        return self.read_float32(self.REG_TOTAL_ACTIVE_POWER, input_registers=True)

    def read_frequency(self) -> float:
        return self.read_float32(self.REG_FREQUENCY, input_registers=True)


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


class SDM630(ThreePhaseEnergyMeter):
    """EASTRON SDM630 three-phase energy meter (Modbus RTU)."""

    REG_CURRENT_L1 = 0x0006
    REG_CURRENT_L2 = 0x0008
    REG_CURRENT_L3 = 0x000A
    REG_ACTIVE_POWER_L1 = 0x000C
    REG_ACTIVE_POWER_L2 = 0x000E
    REG_ACTIVE_POWER_L3 = 0x0010
    REG_TOTAL_ACTIVE_POWER = 0x015A
    REG_FREQUENCY = 0x0046


class Finder7M38_8_400(ThreePhaseEnergyMeter):
    """Finder 7M 38.8.400 three-phase energy meter (Modbus RTU)."""

    DEFAULT_WORDORDER = "little"
    DEFAULT_BYTEORDER = "big"

    REG_FREQUENCY = 0x09C1  # 32498/32499
    REG_ACTIVE_POWER_L1 = 0x09E1  # 32530/32531
    REG_ACTIVE_POWER_L2 = 0x09E3  # 32532/32533
    REG_ACTIVE_POWER_L3 = 0x09E5  # 32534/32535
    REG_TOTAL_ACTIVE_POWER = 0x09E7  # 32536/32537



def main_sht20() -> None:
    slave_address = 1
    port = "/dev/ttyUSB0"
    modbus_controller = ModbusController(port=port)
    modbus_controller.connect()
    if not modbus_controller.connect():
        raise RuntimeError(f"Unable to open Modbus adapter on {port}")
    try:
        sensor = SHT20(modbus_controller, slave_address)    
        t, h = sensor.read_temperature_humidity()
        print(f"Temperature: {t:.1f} °C")
        print(f"Humidity:    {h:.1f} %RH")
    finally:
        modbus_controller.close()

    
def main_sdm230():
    slave_address = 3
    port = "/dev/ttyUSB0"
    modbus_controller = ModbusController(port=port)
    modbus_controller.connect()
    if not modbus_controller.connect():
        raise RuntimeError(f"Unable to open Modbus adapter on {port}")
    try:
        meter = SDM230(modbus_controller, slave_address)
        voltage = meter.read_voltage()
        current = meter.read_current()
        active_power = meter.read_active_power()
        apparent_power = meter.read_apparent_power()
        reactive_power = meter.read_reactive_power()
        power_factor = meter.read_power_factor()
        frequency = meter.read_frequency()
        import_energy = meter.read_import_active_energy()
        export_energy = meter.read_export_active_energy()
        total_energy = meter.read_total_active_energy()

        print(f"Voltage: {voltage:.2f} V")
        print(f"Current: {current:.3f} A")
        print(f"Active Power: {active_power:.2f} W")
        print(f"Apparent Power: {apparent_power:.2f} VA")
        print(f"Reactive Power: {reactive_power:.2f} VAR")
        print(f"Power Factor: {power_factor:.3f}")
        print(f"Frequency: {frequency:.2f} Hz")
        print(f"Import Active Energy: {import_energy:.3f} kWh")
        print(f"Export Active Energy: {export_energy:.3f} kWh")
        print(f"Total Active Energy: {total_energy:.3f} kWh")

    finally:
        modbus_controller.close()



def main_finder():
    slave_address = 4
    port = "/dev/ttyUSB0"
    modbus_controller = ModbusController(port=port)
    modbus_controller.connect()
    if not modbus_controller.connect():
        raise RuntimeError(f"Unable to open Modbus adapter on {port}")
    try:
        meter = Finder7M38_8_400(modbus_controller, slave_address)
        meter.read_active_power_l1()
        meter.read_active_power_l2()
        meter.read_active_power_l3()
        meter.read_total_active_power()
        meter.read_frequency()
        print(f"Active Power L1: {meter.read_active_power_l1():.2f} W")
        print(f"Active Power L2: {meter.read_active_power_l2():.2f} W")
        print(f"Active Power L3: {meter.read_active_power_l3():.2f} W")
        print(f"Total Active Power: {meter.read_total_active_power():.2f} W")
        print(f"Frequency: {meter.read_frequency():.2f} Hz")        
        

    finally:
        modbus_controller.close()



if __name__ == "__main__":    
    #main_sdm230()
    main_finder()

