from pymodbus.client import ModbusSerialClient
import time
import logging

logging.basicConfig()
#logging.getLogger("pymodbus").setLevel(logging.DEBUG)

client = ModbusSerialClient(
        port="/dev/ttyUSB0",
        baudrate=9600,
        parity="N",
        stopbits=1,
        bytesize=8,
        timeout=0.5,
        retries=0
)

if not client.connect():
    raise RuntimeError("Could not open serial port")


def scan_modbus_devices():
    for slave in range(0, 256):
        try:
            rr = client.read_holding_registers(
                address=0,
                count=1,
                slave=slave,
            )

            if rr is not None:
                if rr.isError():
                    print(f"Found device at slave ID {slave} (Modbus exception: {rr})")
                else:
                    print(f"Found device at slave ID {slave}: {rr.registers}")

        except Exception as e:
            print(f"Error scanning slave {slave}: {e}")
        time.sleep(0.5)


def coil_scan():
    for slave in range(1, 248):
        rr = client.read_coils(
            address=0,
            count=1,
            slave=slave,
        )
        if not rr.isError():
            print("Coil device:", slave)

def probe_device(slave_id):
    rr = client.read_coils(
        address=0,
        count=1,
        slave=slave_id)
    print(rr)

    rr = client.read_discrete_inputs(
        address=0,
        count=1,
        slave=slave_id)
    print(rr)

    rr = client.read_input_registers(
        address=0,
        count=5,
        slave=slave_id)
    print(rr)


scan_modbus_devices()    
#coil_scan()
#probe_device(6)

client.close()