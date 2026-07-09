"""Modbus transport utilities: controller, device base, sniffer, helpers."""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence
import inspect
from dataclasses import dataclass
import threading
import time

try:
    from pymodbus.client import ModbusSerialClient
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadDecoder
except ImportError:  # pragma: no cover - import is optional in test environments
    ModbusSerialClient = None  # type: ignore[assignment]
    Endian = None  # type: ignore[assignment]
    BinaryPayloadDecoder = None  # type: ignore[assignment]

try:
    import serial
except Exception:
    serial = None


def crc16(data: bytes) -> int:
    """Compute Modbus RTU CRC16 (returned as integer)."""
    crc = 0xFFFF
    for ch in data:
        crc ^= ch
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


@dataclass
class SerialConfig:
    port: str
    baudrate: int = 9600
    parity: str = "N"
    stopbits: int = 1
    bytesize: int = 8
    timeout: float = 1.0
    method: str = "rtu"


class ModbusController:
    """A controller for USB-to-RS485 / USB-to-Modbus serial adapters."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        timeout: float = 1.0,
        method: str = "rtu",
        serial_config: Optional[SerialConfig] = None,
    ) -> None:
        if serial_config is not None:
            self.port = serial_config.port
            self.baudrate = serial_config.baudrate
            self.parity = serial_config.parity
            self.stopbits = serial_config.stopbits
            self.bytesize = serial_config.bytesize
            self.timeout = serial_config.timeout
            self.method = serial_config.method
        else:
            self.port = port
            self.baudrate = baudrate
            self.parity = parity
            self.stopbits = stopbits
            self.bytesize = bytesize
            self.timeout = timeout
            self.method = method
        if ModbusSerialClient is None:
            raise ImportError(
                "pymodbus is required for Modbus support. Install with `pip install pymodbus`."
            )

        # pymodbus has changed APIs across versions; try constructing the
        # ModbusSerialClient with `method=` first, and fall back to a
        # signature that doesn't accept `method` if needed.
        try:
            self.client = ModbusSerialClient(
                method=self.method,
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout,
            )
        except TypeError:
            # Older/newer pymodbus variants may not accept `method` kwarg.
            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout,
            )

    def connect(self) -> bool:
        """Open the serial connection to the Modbus adapter."""
        return self.client.connect()

    def close(self) -> None:
        """Close the serial connection."""
        self.client.close()

    def scan(self, start: int = 1, stop: int = 247) -> List[int]:
        """Scan for Modbus slave units on the bus."""
        found: List[int] = []
        for unit in range(start, stop + 1):
            try:
                if self.ping(unit):
                    found.append(unit)
            except Exception:
                continue
        return found

    def ping(self, unit: int) -> bool:
        """Check whether a slave responds to simple Modbus traffic."""
        try:
            self._ensure_connected()
            response = self._invoke("read_holding_registers", 0, count=1, unit=unit)
            return bool(response and not getattr(response, "isError", lambda: False)())
        except Exception:
            return False

    def read_coils(self, address: int, count: int, unit: int) -> List[bool]:
        self._ensure_connected()
        response = self._invoke("read_coils", address, count=count, unit=unit)
        self._raise_for_error(response, "read_coils")
        return list(response.bits)

    def read_discrete_inputs(self, address: int, count: int, unit: int) -> List[bool]:
        self._ensure_connected()
        response = self._invoke("read_discrete_inputs", address, count=count, unit=unit)
        self._raise_for_error(response, "read_discrete_inputs")
        return list(response.bits)

    def read_holding_registers(
        self, address: int, count: int, unit: int
    ) -> List[int]:
        self._ensure_connected()
        response = self._invoke("read_holding_registers", address, count=count, unit=unit)
        self._raise_for_error(response, "read_holding_registers")
        return list(response.registers)

    def read_input_registers(
        self, address: int, count: int, unit: int
    ) -> List[int]:
        self._ensure_connected()
        response = self._invoke("read_input_registers", address, count=count, unit=unit)
        self._raise_for_error(response, "read_input_registers")
        return list(response.registers)

    def write_coil(self, address: int, value: bool, unit: int) -> None:
        self._ensure_connected()
        response = self._invoke("write_coil", address, value, unit=unit)
        self._raise_for_error(response, "write_coil")

    def write_register(self, address: int, value: int, unit: int) -> None:
        self._ensure_connected()
        response = self._invoke("write_register", address, value, unit=unit)
        self._raise_for_error(response, "write_register")

    def write_registers(self, address: int, values: Sequence[int], unit: int) -> None:
        self._ensure_connected()
        response = self._invoke("write_registers", address, list(values), unit=unit)
        self._raise_for_error(response, "write_registers")

    def _ensure_connected(self) -> None:
        if not self.client.connect():
            raise ConnectionError(
                f"Unable to connect to Modbus adapter on {self.port}."
            )

    def _invoke(self, method_name: str, *args, unit: Optional[int] = None, **kwargs):
        """Call a pymodbus client method with fallbacks for different API names.

        Some pymodbus versions use `unit=`, others `slave=` or accept the unit
        positionally. This helper tries common variants to remain compatible.
        """
        method = getattr(self.client, method_name)
        try:
            sig = inspect.signature(method)
            param_names = [p.name for p in list(sig.parameters.values())[1:]]
        except Exception:
            sig = None
            param_names = []
        # If no unit provided, call directly
        if unit is None:
            return method(*args, **kwargs)
        # Prefer keyword if method explicitly accepts it
        if "unit" in param_names:
            try:
                return method(*args, **{**kwargs, "unit": unit})
            except TypeError:
                pass
        if "slave" in param_names or "slave_id" in param_names or "unit_id" in param_names:
            key = "slave" if "slave" in param_names else ("slave_id" if "slave_id" in param_names else "unit_id")
            try:
                return method(*args, **{**kwargs, key: unit})
            except TypeError:
                pass

        # If method accepts **kwargs, try passing as `unit`
        if sig is not None and any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            try:
                return method(*args, **{**kwargs, "unit": unit})
            except TypeError:
                pass

        # If method accepts *args, try passing unit as positional
        if sig is not None and any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()):
            try:
                return method(*args, unit, **kwargs)
            except TypeError:
                pass

        # As a last attempt, try common keywords then fallback to calling without unit
        for key in ("unit", "slave", "slave_id", "unit_id"):
            try:
                return method(*args, **{**kwargs, key: unit})
            except TypeError:
                continue

        try:
            return method(*args, **kwargs)
        except TypeError:
            # If even that fails, re-raise the original error for visibility
            raise

    @staticmethod
    def _raise_for_error(response: Any, operation: str) -> None:
        if response is None:
            raise ConnectionError(f"No response received during {operation}.")
        if hasattr(response, "isError") and response.isError():
            raise ConnectionError(
                f"Modbus error during {operation}: {response}",
            )





class ModbusSniffer:
    """Listen-only Modbus RTU sniffer using a second serial adapter.

    The sniffer reads raw bytes from a serial port and attempts to detect
    Modbus RTU frames by validating the CRC16 on candidate frames. When a
    valid frame is found the provided callback is invoked with the raw frame
    bytes.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        timeout: float = 0.1,
        buffer_limit: int = 2048,
    ) -> None:
        if serial is None:
            raise RuntimeError("pyserial is required for ModbusSniffer")
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout
        self.buffer_limit = buffer_limit

        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            parity=self.parity,
            stopbits=self.stopbits,
            bytesize=self.bytesize,
            timeout=self.timeout,
        )

        self._buf = bytearray()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def _find_frame(self) -> Optional[tuple]:
        """Find a valid Modbus RTU frame in the buffer and return (start,end)."""
        buf = self._buf
        n = len(buf)
        for start in range(0, n - 3):
            for end in range(start + 4, min(n, start + 256) + 1):
                frame = bytes(buf[start:end])
                data = frame[:-2]
                crc_lo = frame[-2]
                crc_hi = frame[-1]
                crc = crc16(data)
                if (crc & 0xFF) == crc_lo and ((crc >> 8) & 0xFF) == crc_hi:
                    return (start, end)
        return None

    def _read_loop(self, callback: Callable[[bytes], None]) -> None:
        while self._running:
            try:
                chunk = self._ser.read(256)
            except Exception:
                chunk = b""
            if chunk:
                self._buf.extend(chunk)
                if len(self._buf) > self.buffer_limit:
                    self._buf = self._buf[-self.buffer_limit:]

                while True:
                    found = self._find_frame()
                    if not found:
                        break
                    start, end = found
                    frame = bytes(self._buf[start:end])
                    try:
                        callback(frame)
                    except Exception:
                        pass
                    del self._buf[:end]
            else:
                time.sleep(self.timeout or 0.01)

    def start(self, callback: Callable[[bytes], None]) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, args=(callback,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        try:
            self._ser.close()
        except Exception:
            pass
