import kasa
import datetime
import asyncio
from dateutil import tz
from config import Config
from abc import ABC, abstractmethod


ips = {'dishwasher': '192.168.1.2',
        'garage_lights': '192.168.1.19',
        'hottub': '192.168.1.11',
        'pv': '192.168.1.3'}

config = Config()


def create_kasa_credentials() -> kasa.Credentials:
    creds = config.kasa_credentials()
    return kasa.Credentials(username=creds["username"], password=creds["password"])


class EnergyMeter(ABC):
    """Abstract base class for energy monitoring devices."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the energy monitoring device."""
        pass

    @abstractmethod
    async def get_realtime(self) -> dict:
        """
        Returns realtime energy data as dict.
        Expected format: {"timestamp": ISO format string, "power": float}
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect and release device resources."""
        pass


class KasaEnergyMeter(EnergyMeter):

    def __init__(self, host: str, credentials: kasa.Credentials):
        self.host = host
        self.credentials = credentials
        self.device = None
        self.energy_module = None

    async def connect(self):
        """
        Discover and initialize the device.
        Must be called once before polling.
        """
        self.device = await kasa.Discover.discover_single(
            self.host,
            credentials=self.credentials,
        )

        await self.device.update()

        if kasa.Module.Energy not in self.device.modules:
            raise RuntimeError("Device does not support energy monitoring.")

        self.energy_module = self.device.modules[kasa.Module.Energy]

    async def get_realtime(self) -> dict:
        """
        Returns realtime energy data as dict.
        """
        if self.device is None:
            raise RuntimeError("Device not connected. Call connect() first.")

        await self.device.update()
        realtime = await self.energy_module.get_status()

        pst = tz.gettz('America/Los_Angeles')
        now = datetime.datetime.now(pst)

        return {
            "timestamp": now.isoformat(),
            "power": realtime.power,
        }

    async def disconnect(self) -> None:
        """Disconnect and release kasa device network resources."""
        if self.device is not None:
            await self.device.disconnect()
            self.device = None
            self.energy_module = None


class EcoTrackerEnergyMonitor(EnergyMeter):
    """Energy monitor implementation for EcoTracker devices."""

    def __init__(self, host: str, port: int = 502):
        """
        Initialize EcoTracker energy monitor.
        
        Args:
            host: IP address or hostname of the EcoTracker device
            port: Modbus TCP port (default 502)
        """
        self.host = host
        self.port = port
        self.client = None

    async def connect(self) -> None:
        """
        Connect to the EcoTracker device via Modbus TCP.
        """
        try:
            from pymodbus.client import AsyncModbusTcpClient
            self.client = AsyncModbusTcpClient(host=self.host, port=self.port)
            await self.client.connect()
            if not self.client.is_socket_open():
                raise RuntimeError(f"Failed to connect to EcoTracker at {self.host}:{self.port}")
        except ImportError:
            raise ImportError("pymodbus is required for EcoTracker support. Install it with: pip install pymodbus")

    async def get_realtime(self) -> dict:
        """
        Returns realtime energy data from EcoTracker device.
        Reads power (watts) from standard Modbus registers.
        """
        if self.client is None:
            raise RuntimeError("Device not connected. Call connect() first.")

        try:
            # Read power value from holding register (typical EcoTracker config)
            # Register 0: Power in watts (as 32-bit float)
            result = await self.client.read_holding_registers(
                address=0,
                count=2,
                slave=1
            )

            if result.isError():
                raise RuntimeError(f"Modbus read error: {result}")

            # Combine two 16-bit registers into 32-bit float
            import struct
            power = struct.unpack('>f', struct.pack('>HH', result.registers[0], result.registers[1]))[0]

            pst = tz.gettz('America/Los_Angeles')
            now = datetime.datetime.now(pst)

            return {
                "timestamp": now.isoformat(),
                "power": power,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to read EcoTracker data: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the EcoTracker device."""
        if self.client is not None:
            await self.client.close()
            self.client = None


async def main() -> None:
    creds = create_kasa_credentials()
    meter = KasaEnergyMeter(host=config['kasa']['host_pv'], credentials=creds)
    try:
        await meter.connect()
        data = await meter.get_realtime()
        print(data)
    finally:
        await meter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())






