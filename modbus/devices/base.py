"""Base Modbus device abstractions shared by the device-specific modules."""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from ..transport import ModbusController
except ImportError:  # pragma: no cover - fallback for direct script execution
    from modbus.transport import ModbusController

try:
    from pymodbus.constants import Endian
except Exception:
    Endian = None  # type: ignore


class ModbusDevice:
    """A Modbus slave device attached to the adapter bus."""

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


__all__ = ["ModbusDevice"]
