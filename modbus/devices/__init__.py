"""Device-specific Modbus abstractions.

This package exposes the Modbus device classes from smaller focused modules.
"""

from __future__ import annotations

from .base import ModbusDevice

__all__ = [
    "ModbusDevice",
    "ThreePhaseEnergyMeter",
    "FHS280",
    "SHT20",
    "SDM230",
    "SDM630",
    "SDM72DM_V2",
    "Finder7M38_8_400",
    "WaveshareESP32S3Relay1CH",
]


def __getattr__(name: str):
    if name == "ThreePhaseEnergyMeter":
        from .threephase_energy_meters import ThreePhaseEnergyMeter

        return ThreePhaseEnergyMeter
    if name == "FHS280":
        from .fhs280 import FHS280

        return FHS280
    if name == "WaveshareESP32S3Relay1CH":
        from .waveshare_relay import WaveshareESP32S3Relay1CH

        return WaveshareESP32S3Relay1CH
    if name == "SHT20":
        from .sht20 import SHT20

        return SHT20
    if name == "SDM230":
        from .sdm230 import SDM230

        return SDM230
    if name in {"SDM630", "SDM72DM_V2", "Finder7M38_8_400"}:
        from .threephase_energy_meters import SDM630, SDM72DM_V2, Finder7M38_8_400

        return {
            "SDM630": SDM630,
            "SDM72DM_V2": SDM72DM_V2,
            "Finder7M38_8_400": Finder7M38_8_400,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + __all__)

