"""Three-phase energy meter device abstractions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

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
DEFAULT_SLAVE_ADDRESS = 5


class ThreePhaseEnergyMeter(ModbusDevice):
    """Common 3-phase energy meter abstraction for SDM630/Finder-style meters."""

    REG_CURRENT_L1: int
    REG_CURRENT_L2: int
    REG_CURRENT_L3: int
    REG_ACTIVE_POWER_L1: int
    REG_ACTIVE_POWER_L2: int
    REG_ACTIVE_POWER_L3: int
    REG_TOTAL_ACTIVE_POWER: int
    REG_ACTIVE_POWER_IMPORT: Optional[int] = None
    REG_ACTIVE_POWER_EXPORT: Optional[int] = None
    REG_FREQUENCY: int
    REG_IMPORT_ENERGY: Optional[int] = None
    REG_EXPORT_ENERGY: Optional[int] = None

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
    
    def read_active_power_import(self) -> float:
        if self.REG_ACTIVE_POWER_IMPORT is None:
            raise NotImplementedError("This meter does not expose import active power")
        return self.read_float32(self.REG_ACTIVE_POWER_IMPORT, input_registers=True)
    
    def read_active_power_export(self) -> float:
        if self.REG_ACTIVE_POWER_EXPORT is None:
            raise NotImplementedError("This meter does not expose export active power")
        return self.read_float32(self.REG_ACTIVE_POWER_EXPORT, input_registers=True)

    def read_total_active_power(self) -> float:
        return self.read_float32(self.REG_TOTAL_ACTIVE_POWER, input_registers=True)

    def read_frequency(self) -> float:
        return self.read_float32(self.REG_FREQUENCY, input_registers=True)

    def read_import_active_energy(self) -> float:
        if self.REG_IMPORT_ENERGY is None:
            raise NotImplementedError("This meter does not expose import energy")
        return self.read_float32(self.REG_IMPORT_ENERGY, input_registers=True)

    def read_export_active_energy(self) -> float:
        if self.REG_EXPORT_ENERGY is None:
            raise NotImplementedError("This meter does not expose export energy")
        return self.read_float32(self.REG_EXPORT_ENERGY, input_registers=True)
    

class SDM630(ThreePhaseEnergyMeter):
    """EASTRON SDM630 three-phase energy meter (Modbus RTU)."""

    REG_CURRENT_L1 = 0x0006
    REG_CURRENT_L2 = 0x0008
    REG_CURRENT_L3 = 0x000A
    REG_ACTIVE_POWER_L1 = 0x000C
    REG_ACTIVE_POWER_L2 = 0x000E
    REG_ACTIVE_POWER_L3 = 0x0010
    REG_ACTIVE_POWER_IMPORT = 0x79C1  # 31281 
    REG_ACTIVE_POWER_EXPORT = 0x79C3  # 31283 
    REG_TOTAL_ACTIVE_POWER = 0x0034  # 30053
    REG_FREQUENCY = 0x0046
    REG_IMPORT_ENERGY = 0x0156
    REG_EXPORT_ENERGY = 0x0158
    

class SDM72DM_V2(ThreePhaseEnergyMeter):
    """Eastron SDM72DM-V2 3-phase two-direction meter (Modbus RTU)."""

    # Verified against SDM72DM-V2 manual Input Registers table.
    REG_VOLTAGE_L1N = 0x0000  # 30001, V
    REG_VOLTAGE_L2N = 0x0002  # 30003, V
    REG_CURRENT_L1 = 0x0006  # 30007
    REG_CURRENT_L2 = 0x0008  # 30009
    REG_CURRENT_L3 = 0x000A  # 30011
    REG_ACTIVE_POWER_L1 = 0x000C  # 30013
    REG_ACTIVE_POWER_L2 = 0x000E  # 30015
    REG_ACTIVE_POWER_L3 = 0x0010  # 30017
    REG_APPARENT_POWER_L1 = 0x0012  # 30019, VA
    REG_APPARENT_POWER_L2 = 0x0014  # 30021, VA
    REG_APPARENT_POWER_L3 = 0x0016  # 30023, VA
    REG_REACTIVE_POWER_L1 = 0x0018  # 30025, VAr
    REG_REACTIVE_POWER_L2 = 0x001A  # 30027, VAr
    REG_REACTIVE_POWER_L3 = 0x001C  # 30029, VAr
    REG_POWER_FACTOR_L1 = 0x001E  # 30031, unitless
    REG_POWER_FACTOR_L2 = 0x0020  # 30033, unitless
    REG_POWER_FACTOR_L3 = 0x0022  # 30035, unitless
    REG_AVERAGE_VOLTAGE_LN = 0x002A  # 30043, V
    REG_AVERAGE_LINE_CURRENT = 0x002E  # 30047, A
    REG_SUM_LINE_CURRENTS = 0x0030  # 30049, A
    REG_TOTAL_ACTIVE_POWER = 0x0034  # 30053
    REG_TOTAL_APPARENT_POWER = 0x0038  # 30057, VA
    REG_TOTAL_REACTIVE_POWER = 0x003C  # 30061, VAr
    REG_TOTAL_POWER_FACTOR = 0x003E  # 30063, unitless
    REG_FREQUENCY = 0x0046  # 30071
    REG_IMPORT_ENERGY = 0x0048  # 30073
    REG_EXPORT_ENERGY = 0x004A  # 30075
    REG_VOLTAGE_L12 = 0x00C8  # 30201, V
    REG_VOLTAGE_L23 = 0x00CA  # 30203, V
    REG_VOLTAGE_L31 = 0x00CC  # 30205, V
    REG_AVERAGE_VOLTAGE_LL = 0x00CE  # 30207, V
    REG_NEUTRAL_CURRENT = 0x00E0  # 30225, A
    REG_TOTAL_ACTIVE_ENERGY = 0x0156  # 30343, kWh
    REG_TOTAL_REACTIVE_ENERGY = 0x0158  # 30345, kVArh
    REG_RESETTABLE_TOTAL_ACTIVE_ENERGY = 0x0180  # 30385, kWh
    REG_RESETTABLE_TOTAL_REACTIVE_ENERGY = 0x0182  # 30387, kVArh
    REG_RESETTABLE_IMPORT_ACTIVE_ENERGY = 0x0184  # 30389, kWh
    REG_RESETTABLE_EXPORT_ACTIVE_ENERGY = 0x0186  # 30391, kWh
    REG_NET_ACTIVE_ENERGY = 0x018C  # 30397, kWh (import - export)
    REG_ACTIVE_POWER_IMPORT = 0x0500  # 31281
    REG_ACTIVE_POWER_EXPORT = 0x0502  # 31283
    

class Finder7M38_8_400(ThreePhaseEnergyMeter):
    """Finder 7M 38.8.400 three-phase energy meter (Modbus RTU)."""

    DEFAULT_WORDORDER = "little"
    DEFAULT_BYTEORDER = "big"

    REG_FREQUENCY = 0x09C1  # 32498/32499
    REG_ACTIVE_POWER_L1 = 0x09E1  # 32530/32531
    REG_ACTIVE_POWER_L2 = 0x09E3  # 32532/32533
    REG_ACTIVE_POWER_L3 = 0x09E5  # 32534/32535
    REG_TOTAL_ACTIVE_POWER = 0x09E7  # 32536/32537



def read_sdm72() -> None:
    controller = ModbusController(port='/dev/ttyUSB0')
    controller.connect()
    slave_address = 5
    try:
        meter = SDM72DM_V2(controller, slave_address=slave_address)
        active_power_l1 = meter.read_active_power_l1()
        active_power_l2 = meter.read_active_power_l2()
        active_power_l3 = meter.read_active_power_l3()
        total_active_power = meter.read_total_active_power()
        import_energy = meter.read_import_active_energy()
        export_energy = meter.read_export_active_energy()
        import_power = meter.read_active_power_import()
        export_power = meter.read_active_power_export()
        print(f"""SDM72DM-V2 @ {slave_address}: 
              active_power_l1={active_power_l1:.2f} W, 
              active_power_l2={active_power_l2:.2f} W, 
              active_power_l3={active_power_l3:.2f} W, 
              total_active_power={total_active_power:.2f} W, 
              import_power={import_power:.2f} W, 
              export_power={export_power:.2f} W,
              import_energy={import_energy:.2f} kWh, 
              export_energy={export_energy:.2f} kWh""")        
        
    finally:
        controller.close()

def read_finder7m() -> None:
    controller = ModbusController(port='/dev/ttyUSB0')
    controller.connect()
    slave_address = 149
    try:
        meter = Finder7M38_8_400(controller, slave_address=slave_address)
        active_power_l1 = meter.read_active_power_l1()
        active_power_l2 = meter.read_active_power_l2()
        active_power_l3 = meter.read_active_power_l3()
        total_active_power = meter.read_total_active_power()
        frequency = meter.read_frequency()
        print(f"""Finder 7M 38.8.400 @ {slave_address}: 
              active_power_l1={active_power_l1:.2f} W, 
              active_power_l2={active_power_l2:.2f} W, 
              active_power_l3={active_power_l3:.2f} W, 
              total_active_power={total_active_power:.2f} W, 
              frequency={frequency:.2f} Hz""")        
        
    finally:
        controller.close()


if __name__ == "__main__":
    read_finder7m()
    read_sdm72()


__all__ = [
    "ThreePhaseEnergyMeter",
    "SDM630",
    "SDM72DM_V2",
    "Finder7M38_8_400",
]
