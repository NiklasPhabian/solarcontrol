"""Modbus package providing transport and device abstractions.

This package intentionally avoids importing `modbus.devices` at package
import time to prevent a runtime warning when executing a submodule with
``python -m modbus.devices``. The device classes are imported lazily via
``__getattr__`` so they're available as attributes but don't trigger
early import.

Public API (transport is imported eagerly):
- ModbusController, SerialConfig, crc16, ModbusSniffer
- ModbusDevice, SHT20, SDM230 (lazy)
"""
from .transport import ModbusController, SerialConfig, crc16, ModbusSniffer

__all__ = [
    "ModbusController",
    "SerialConfig",
    "crc16",
    "ModbusSniffer",
    "ModbusDevice",
    "SHT20",
    "SDM230",
]


def __getattr__(name: str):
    # Lazily import device classes to avoid importing modbus.devices when the
    # package is imported (avoids runpy RuntimeWarning when running modules).
    if name in ("ModbusDevice", "SHT20", "SDM230"):
        from . import devices

        return getattr(devices, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + ["ModbusDevice", "SHT20", "SDM230"])
