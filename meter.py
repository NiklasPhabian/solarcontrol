import kasa
import datetime
import asyncio
from dateutil import tz
from config import Config

ips = {'dishwasher': '192.168.1.2',
       'garage_lights': '192.168.1.19',
       'hottub': '192.168.1.11',
       'pv': '192.168.1.3'}


config = Config()


def create_kasa_credentials() -> kasa.Credentials:
    creds = config.get_kasa_credentials()
    return kasa.Credentials(username=creds["username"], password=creds["password"])


class KasaEnergyMonitor:

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


async def main() -> None:
    creds = create_kasa_credentials()
    meter = KasaEnergyMonitor(host=ips['pv'], credentials=creds)
    try:
        await meter.connect()
        data = await meter.get_realtime()
        print(data)
    finally:
        await meter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())






