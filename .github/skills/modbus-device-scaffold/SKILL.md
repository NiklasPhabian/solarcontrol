---
name: modbus-device-scaffold
description: "Use when creating or extending a Modbus device adapter module, including register mapping, decoding helpers, and matching unit tests."
---

# Modbus Device Scaffold Skill

Create new Modbus device adapters that match repository patterns.

## Inputs To Collect

- Target device name and protocol notes
- Slave address defaults
- Register map (address, type, units, scale)
- Byte/word order requirements
- Read/write operations required

## Implementation Pattern

1. Add or update device module under [modbus/devices/](modbus/devices/).
2. Inherit from `ModbusDevice` from [modbus/devices/base.py](modbus/devices/base.py).
3. Keep constants for register addresses and defaults at class level.
4. Implement explicit reader/writer methods with domain names.
5. Export class via [modbus/devices/__init__.py](modbus/devices/__init__.py) lazy import pattern.

## Test Pattern

1. Add a unittest module under [tests/](tests/), e.g. `tests/test_<device>.py`.
2. Mock bus interactions using dummy controller objects.
3. Verify method-to-register mapping, units/scaling, and endian handling.
4. Avoid requiring real serial devices.

## Verification Commands

- Use existing conda env `solarcontrol`.
- Run target test only first, then broader tests if needed.

```bash
conda run -n solarcontrol python -m unittest -v tests/test_<device>.py
conda run -n solarcontrol python -m unittest discover -s tests -p "test_*.py"
```

## Guardrails

- Keep profile safety: changes to shared Modbus code must not break Haslach or Bishop runtime wiring.
- Preserve backward compatibility for existing device class names unless explicitly requested.
- Document any new config keys in [config.example.ini](config.example.ini).
