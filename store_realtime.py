import asyncio

from config import Config
from database import SQLiteDatabase
from meter import KasaEnergyMeter, create_kasa_credentials

config = Config()


async def fetch_realtime_data() -> dict:
    creds = create_kasa_credentials()
    monitor = KasaEnergyMeter(host=config['kasa']['host_pv'], credentials=creds)
    try:
        await monitor.connect()
        return await monitor.get_realtime()
    finally:
        await monitor.disconnect()


def main() -> None:
    db_path = config.sqlite_db_path()
    table_name = config.realtime_table_name()

    realtime = asyncio.run(fetch_realtime_data())
    with SQLiteDatabase(db_path, table_name) as db:
        db.insert_realtime(realtime)

    print(f"Stored realtime row in {db_path}")
    print(realtime)


if __name__ == "__main__":
    main()
