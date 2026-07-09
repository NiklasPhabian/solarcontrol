"""Waveshare ESP32-S3 Relay 1CH Modbus RTU device abstraction."""

from __future__ import annotations

from .base import ModbusDevice

from ..transport import ModbusController


class WaveshareESP32S3Relay1CH(ModbusDevice):
    """Waveshare ESP32-S3 Relay 1CH Modbus RTU device."""

    RELAY_COIL_ADDRESS = 0x0000
    SLAVE_ADDRESS_REGISTER = 0x0000

    def __init__(self, controller: ModbusController, slave_address: int = 1):
        super().__init__(controller, slave_address)

    def read_relay_state(self) -> bool:
        coils = self.read_coils(self.RELAY_COIL_ADDRESS, count=1)
        return bool(coils[0])

    def turn_on(self):
        self.write_coil(self.RELAY_COIL_ADDRESS, True)

    def turn_off(self):
        self.write_coil(self.RELAY_COIL_ADDRESS, False)

    def read_slave_address(self) -> int:
        registers = self.read_holding_registers(self.SLAVE_ADDRESS_REGISTER, count=1)
        return int(registers[0])

    def set_slave_address(self, address: int) -> None:
        self.write_register(self.SLAVE_ADDRESS_REGISTER, address)
        self.slave_address = int(address)

__all__ = ["WaveshareESP32S3Relay1CH"]


def read_relay_state_example():    
    parity = 'N'
        
    controller = ModbusController(port="/dev/ttyUSB0", baudrate=9600, parity=parity, stopbits=1, bytesize=8)
    slave_address = 7
    controller.connect()
    try:
        relay_device = WaveshareESP32S3Relay1CH(controller, slave_address=slave_address)
        print(f"Relay Modbus address: {relay_device.read_slave_address()}")
        relay_state = relay_device.read_relay_state()
        print(f"Relay state: {'ON' if relay_state else 'OFF'}")
    finally:
        controller.close()


if __name__ == "__main__":
    read_relay_state_example()