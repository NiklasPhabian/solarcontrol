"""Device-specific Modbus abstractions: SHT20 and SDM230.

This module contains high-level device wrappers that use the transport
layer in `modbus.transport`.
"""

from __future__ import annotations

from typing import Tuple, List, Sequence, Optional, Any

from .transport import ModbusController
try:
    from pymodbus.payload import BinaryPayloadDecoder
except Exception:
    BinaryPayloadDecoder = None  # type: ignore


class ModbusDevice:
    """A Modbus slave device attached to the adapter bus.

    This base class provides convenience wrappers around a `ModbusController`
    instance for common read/write and typed-decoding operations.
    """

    def __init__(self, controller: ModbusController, unit_id: int) -> None:
        self.controller = controller
        self.unit_id = int(unit_id)

    def read_coils(self, address: int, count: int = 1) -> List[bool]:
        return self.controller.read_coils(address, count, unit=self.unit_id)

    def read_discrete_inputs(self, address: int, count: int = 1) -> List[bool]:
        return self.controller.read_discrete_inputs(address, count, unit=self.unit_id)

    def read_holding_registers(self, address: int, count: int = 1) -> List[int]:
        return self.controller.read_holding_registers(address, count, unit=self.unit_id)

    def read_input_registers(self, address: int, count: int = 1) -> List[int]:
        return self.controller.read_input_registers(address, count, unit=self.unit_id)

    def write_coil(self, address: int, value: bool) -> None:
        self.controller.write_coil(address, value, unit=self.unit_id)

    def write_register(self, address: int, value: int) -> None:
        self.controller.write_register(address, value, unit=self.unit_id)

    def write_registers(self, address: int, values: Sequence[int]) -> None:
        self.controller.write_registers(address, values, unit=self.unit_id)

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
        if BinaryPayloadDecoder is None:
            raise RuntimeError("pymodbus BinaryPayloadDecoder not available")
        if wordorder is None and byteorder is None:
            decoder = BinaryPayloadDecoder.fromRegisters(registers)
        else:
            kwargs = {}
            if byteorder is not None:
                kwargs["byteorder"] = byteorder
            if wordorder is not None:
                kwargs["wordorder"] = wordorder
            decoder = BinaryPayloadDecoder.fromRegisters(registers, **kwargs)
        return decoder.decode_string(2 * count).decode(encoding).rstrip("\x00")

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
    def _decode(
        registers: List[int],
        data_type: str,
        wordorder: Optional[Any] = None,
        byteorder: Optional[Any] = None,
    ) -> Any:
        if BinaryPayloadDecoder is None:
            raise RuntimeError("pymodbus BinaryPayloadDecoder not available")
        if wordorder is None and byteorder is None:
            decoder = BinaryPayloadDecoder.fromRegisters(registers)
        else:
            kwargs = {}
            if byteorder is not None:
                kwargs["byteorder"] = byteorder
            if wordorder is not None:
                kwargs["wordorder"] = wordorder
            decoder = BinaryPayloadDecoder.fromRegisters(registers, **kwargs)
        if data_type == "uint16":
            return decoder.decode_16bit_uint()
        if data_type == "int16":
            return decoder.decode_16bit_int()
        if data_type == "uint32":
            return decoder.decode_32bit_uint()
        if data_type == "int32":
            return decoder.decode_32bit_int()
        if data_type == "float32":
            return decoder.decode_32bit_float()
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

    def write_device_address(self, new_addr: int) -> None:
        if not (1 <= new_addr <= 247):
            raise ValueError("address out of range 1..247")
        self.write_register(self._REG_DEVICE_ADDR, int(new_addr))

    def read_baud_rate(self) -> int:
        regs = self.read_holding_registers(self._REG_BAUDRATE, count=1)
        return int(regs[0])

    def write_baud_rate(self, code: int) -> None:
        if code not in (0, 1, 2):
            raise ValueError("unsupported baud rate code; use 0=9600,1=14400,2=19200")
        self.write_register(self._REG_BAUDRATE, int(code))

    def read_temperature_offset(self) -> float:
        regs = self.read_holding_registers(self._REG_TEMP_OFFSET, count=1)
        raw = regs[0]
        if raw & 0x8000:
            raw = raw - 0x10000
        return raw / 10.0

    def write_temperature_offset(self, offset_celsius: float) -> None:
        if not (-10.0 <= offset_celsius <= 10.0):
            raise ValueError("temperature offset out of supported range -10.0..10.0")
        raw = int(round(offset_celsius * 10)) & 0xFFFF
        self.write_register(self._REG_TEMP_OFFSET, raw)

    def read_humidity_offset(self) -> float:
        regs = self.read_holding_registers(self._REG_HUM_OFFSET, count=1)
        raw = regs[0]
        if raw & 0x8000:
            raw = raw - 0x10000
        return raw / 10.0

    def write_humidity_offset(self, offset_rh: float) -> None:
        if not (-10.0 <= offset_rh <= 10.0):
            raise ValueError("humidity offset out of supported range -10.0..10.0")
        raw = int(round(offset_rh * 10)) & 0xFFFF
        self.write_register(self._REG_HUM_OFFSET, raw)


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


def _main_probe_sht20() -> None:
    unit = 1
    port = "/dev/ttyUSB0"
    controller = ModbusController(port=port)
    if not controller.connect():
        raise RuntimeError(f"Unable to open Modbus adapter on {port}")
    try:
        sensor = SHT20(controller, unit)    
        t, h = sensor.read_temperature_humidity()
        print(f"Temperature: {t:.1f} °C")
        print(f"Humidity:    {h:.1f} %RH")
    finally:
        controller.close()


if __name__ == "__main__":
    _main_probe_sht20()
