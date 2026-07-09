import importlib
import sys


def test_package_import_does_not_eagerly_import_threephase_module():
    sys.modules.pop("modbus.devices", None)
    sys.modules.pop("modbus.devices.threephase_energy_meters", None)

    package = importlib.import_module("modbus.devices")
    assert package.__name__ == "modbus.devices"
    assert "modbus.devices.threephase_energy_meters" not in sys.modules
