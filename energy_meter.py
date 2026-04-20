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
    
    async def reconnect(self):
        try:
            await self.disconnect()
        except Exception:
            pass  # ignore cleanup errors

        await asyncio.sleep(1)  # small backoff
        await self.connect()
            
    async def get_power_unsafe(self) -> dict:
        """
        Returns realtime energy data as dict.
        """
        if self.device is None:
            raise RuntimeError("Device not connected. Call connect() first.")

        await self.device.update()
        realtime = await self.energy_module.get_status()

        return realtime.power
    
    async def get_power(self):
        try:
            return await self.get_power_unsafe()
        except Exception as e:            
            await self.reconnect()

            return await self.get_power_unsafe()
    
    async def disconnect(self) -> None:
        """Disconnect and release kasa device network resources."""
        if self.device is not None:
            await self.device.disconnect()
            self.device = None
            self.energy_module = None


class EcoTrackerEnergyMeter:
    """Energy monitor implementation for EcoTracker devices."""

    def __init__(self, host: str):
        self.host = host

    def get_power_async():
        # Placeholder for actual implementation to fetch power data from EcoTracker
        return 0.0  # Replace with actual power value


async def main():
    from dateutil import tz
    from config import Config    
    
    pst = tz.gettz('PST')

    config = Config('config_bishop.ini')    
    host_pv_meter = config['meter_pv']['host']
    host_fridge_meter = config['meter_fridge']['host']
    host_dishwasher_meter = config['meter_dishwasher']['host']
    username = config['kasa']['username']
    password = config['kasa']['password']
    
    meter_pv = KasaEnergyMeter(host=host_pv_meter, username=username, password=password)
    meter_fridge = KasaEnergyMeter(host=host_fridge_meter, username=username, password=password)
    meter_dishwasher = KasaEnergyMeter(host=host_dishwasher_meter, username=username, password=password)

    try:        
        while True:
            power_pv = await meter_pv.get_power()
            power_fridge = await meter_fridge.get_power()
            power_dishwasher = await meter_dishwasher.get_power()

            now = datetime.datetime.now(pst)
            timestamp = now.isoformat()

            print({"timestamp": timestamp, "power": power_pv, "power_fridge": power_fridge, "power_dishwasher": power_dishwasher})
            await asyncio.sleep(5)
    finally:
        await meter_pv.disconnect()
        await meter_fridge.disconnect()
        await meter_dishwasher.disconnect()


if __name__ == "__main__":
    asyncio.run(main())