"""Waveshare ESP32-S3 Relay 1CH Modbus RTU device abstraction."""

from __future__ import annotations

from .base import ModbusDevice
from ..transport import ModbusController


class WaveshareESP32S3Relay1CH(ModbusDevice):
    """Waveshare ESP32-S3 Relay 1CH controlled via the Modbus RTU bridge firmware.

    Slave ID 7 is hardcoded in the firmware.  The device exposes a single relay
    on coil address 0x0000 (FC01 / FC05) and mirrors the same state on holding
    register 0x0000 (FC03) for scanners that only probe holding registers.
    """

    RELAY_COIL_ADDRESS = 0x0000
    RELAY_HOLDING_REGISTER = 0x0000
    DEFAULT_SLAVE_ID = 7

    def __init__(self, controller: ModbusController, slave_address: int = DEFAULT_SLAVE_ID):
        super().__init__(controller, slave_address)

    # ── relay control ─────────────────────────────────────────────────────────

    def turn_on(self) -> None:
        """Energise the relay (FC05, coil 0x0000 = 0xFF00)."""
        self.write_coil(self.RELAY_COIL_ADDRESS, True)

    def turn_off(self) -> None:
        """De-energise the relay (FC05, coil 0x0000 = 0x0000)."""
        self.write_coil(self.RELAY_COIL_ADDRESS, False)

    def set_relay(self, state: bool) -> None:
        """Set the relay to an explicit state."""
        if state:
            self.turn_on()
        else:
            self.turn_off()

    # ── relay state reads ─────────────────────────────────────────────────────

    def read_relay_state(self) -> bool:
        """Return the current relay state via FC01 (Read Coil Status)."""
        coils = self.read_coils(self.RELAY_COIL_ADDRESS, count=1)
        return bool(coils[0])

    def read_relay_state_register(self) -> bool:
        """Return the current relay state via FC03 (Read Holding Registers).

        Produces the same value as ``read_relay_state``; useful for masters
        that only support holding-register reads.
        """
        registers = self.read_holding_registers(self.RELAY_HOLDING_REGISTER, count=1)
        return bool(registers[0])


__all__ = ["WaveshareESP32S3Relay1CH"]


def _example():
    controller = ModbusController(
        port="/dev/ttyUSB0",
        baudrate=9600,
        parity="N",
        stopbits=1,
        bytesize=8,
    )
    controller.connect()
    try:
        relay = WaveshareESP32S3Relay1CH(controller)
        print(f"State (coil):     {'ON' if relay.read_relay_state() else 'OFF'}")
        print(f"State (register): {'ON' if relay.read_relay_state_register() else 'OFF'}")
        relay.turn_on()
        print(f"After turn_on:    {'ON' if relay.read_relay_state() else 'OFF'}")
        relay.turn_off()
        print(f"After turn_off:   {'ON' if relay.read_relay_state() else 'OFF'}")
    finally:
        controller.close()


if __name__ == "__main__":
    _example()
