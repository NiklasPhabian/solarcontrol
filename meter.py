import kasa
import datetime
import asyncio


class KasaEnergyMeter:

    def __init__(self, host, username, password):
        self.host = host
        self.device = None
        self.energy_module = None
        self.credentials = kasa.Credentials(username=username, password=password)
        self.loop = asyncio.new_event_loop()
        self.connect()

    async def connect_async(self):
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

    def connect(self):
        """Synchronous wrapper for connect_async."""
        self.loop.run_until_complete(self.connect_async())

    async def get_power_async(self) -> dict:
        """
        Returns realtime energy data as dict.
        """
        if self.device is None:
            raise RuntimeError("Device not connected. Call connect() first.")

        await self.device.update()
        realtime = await self.energy_module.get_status()

        return realtime.power

    def get_power(self) -> float:
        """Synchronous wrapper for get_power_async."""
        return self.loop.run_until_complete(self.get_power_async())

    async def disconnect_async(self) -> None:
        """Disconnect and release kasa device network resources."""
        if self.device is not None:
            await self.device.disconnect()
            self.device = None
            self.energy_module = None

    def disconnect(self) -> None:
        """Synchronous wrapper for disconnect_async."""
        if self.loop.is_closed():
            return
        self.loop.run_until_complete(self.disconnect_async())
        self.loop.close()


class EcoTrackerEnergyMeter:
    """Energy monitor implementation for EcoTracker devices."""

    def __init__(self, host: str):
        self.host = host

    def get_power_async():
        # Placeholder for actual implementation to fetch power data from EcoTracker
        return 0.0  # Replace with actual power value


class EnergyMeter:

    def __init__(self, device, host, username=None, password=None):
        self.device = device
        self.host = host
        self.username = username
        self.password = password
        
        if self.device == "kasa":
            self.meter = KasaEnergyMeter(host=self.host, username=self.username, password=self.password)
            self.meter.connect()
        elif self.device == "ecotracker":
            self.meter = EcoTrackerEnergyMeter(host=self.host)
        else:
            raise ValueError(f"Unsupported device type: {self.device}")

    def get_power(self):
        return self.meter.get_power()

    def disconnect(self):
        if self.device == "kasa":
            self.meter.disconnect()
        # Add disconnect logic for EcoTracker if needed




if __name__ == "__main__":
    from dateutil import tz
    from config import Config
    import time
    
    pst = tz.gettz('America/Los_Angeles')

    config = Config()
    device = config['meter']['meter_device']
    host = config['meter']['host_pv']
    username = config['kasa']['username']
    password = config['kasa']['password']
    
    meter = EnergyMeter(device=device, host=host, username=username, password=password)

    while True:
        try:
            power = meter.get_power()
        
            now = datetime.datetime.now(pst)
            timestamp = now.isoformat()

            print({"timestamp": timestamp, "power": power})
            time.sleep(5)
        finally:
            meter.disconnect()





