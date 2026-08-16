# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project At A Glance

- Two runtime profiles:
  - Haslach control loop: [main_haslach.py](main_haslach.py)
  - Bishop monitoring/dashboard loop: [main_bishop.py](main_bishop.py)
- Config is INI-based and loaded via [config.py](config.py).
- Core control logic is in [controller.py](controller.py).
- Hardware adapters are isolated by module (GPIO relay, Modbus devices, Kasa meter, Shelly plug).

## First Steps

1. Read [README.md](README.md) for deployment context.
2. Identify target profile and matching config file:
   - Haslach: [config_haslach.ini](config_haslach.ini)
   - Bishop: [config_bishop.ini](config_bishop.ini)
3. Keep changes profile-safe (do not break the other profile).

## Environment And Command Conventions

- Use the existing conda environment `solarcontrol` for Python execution.
- If a prompt references `solarconrol`, treat it as the same intended `solarcontrol` conda environment.
- Do not create a new virtual environment unless the user explicitly asks.

## Execution Context (RPi vs Workstation)

- The `main_*` runtimes are generally intended to run on a Raspberry Pi accessed via SSH.
- SSH alias `rpi_haslach` has been verified for remote command execution.
- In this workspace, files may be edited through SSHFS from a workstation.
- Commands run from the workstation execute on the workstation, not on the Raspberry Pi.
- Workstation runs cannot access Raspberry Pi-attached hardware (for example Modbus devices, GPIO, and local bus peripherals).
- Hardware-integrated validation must be executed on the Raspberry Pi over SSH.
- Prefer workstation-side unit tests with mocks for hardware boundaries; run real hardware checks only on the Pi.

Example remote execution pattern:

```bash
ssh rpi_haslach 'cd ~/rpi_haslach/solarcontrol && conda run -n solarcontrol python -m unittest -v tests/test_controller.py'
```

Primary test command:

```bash
conda run -n solarcontrol python -m unittest discover -s tests -p "test_*.py"
```

Run a single test module:

```bash
conda run -n solarcontrol python -m unittest -v tests/test_controller.py
```

## Architecture Map

- Runtime wiring:
  - [main_haslach.py](main_haslach.py)
  - [main_bishop.py](main_bishop.py)
- Control/state machine:
  - [controller.py](controller.py)
- Data persistence and outputs:
  - [database.py](database.py)
  - [plotter.py](plotter.py)
  - [html_writer.py](html_writer.py)
- Device integration:
  - Kasa meter: [energy_meter.py](energy_meter.py)
  - GPIO relay: [relay.py](relay.py)
  - Shelly Plug M Gen3: [shelly_plug_m_gen3.py](shelly_plug_m_gen3.py)
  - Modbus transport: [modbus/transport.py](modbus/transport.py)
  - Modbus device base: [modbus/devices/base.py](modbus/devices/base.py)
  - Example Modbus devices: [modbus/devices/fhs280.py](modbus/devices/fhs280.py), [modbus/devices/sdm230.py](modbus/devices/sdm230.py), [modbus/devices/waveshare_relay.py](modbus/devices/waveshare_relay.py)

## Coding Conventions And Pitfalls

- Prefer small adapter classes around hardware protocols; avoid mixing protocol details into control logic.
- Keep config keys stable; code indexes config sections by string names.
- Respect power sign conventions in control flow:
  - Negative values indicate export/excess generation.
- Be careful with hardware assumptions:
  - GPIO and I2C may be unavailable on non-RPi dev machines.
  - Modbus serial paths and slave IDs vary by deployment.
- For tests, mock hardware/network boundaries instead of requiring real devices.

## Change Safety Checklist

1. Confirm whether the change is Haslach-only, Bishop-only, or shared.
2. Update config examples when introducing new config keys.
3. Add or adjust tests under [tests/](tests/).
4. Run targeted tests in `solarcontrol` env.
5. Keep unrelated files untouched.

## Deployment References

- Install script: [scripts/install_rpi.sh](scripts/install_rpi.sh)
- Service units: [systemd/solarcontrol-haslach.service](systemd/solarcontrol-haslach.service), [systemd/solarcontrol-bishop.service](systemd/solarcontrol-bishop.service)
- Legacy service files in repo root: [solarcontrol.service](solarcontrol.service), [solarcontrol.example.service](solarcontrol.example.service)
