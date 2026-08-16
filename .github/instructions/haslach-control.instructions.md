---
description: "Use when editing Haslach control-loop code or Haslach config files."
applyTo: "main_haslach.py,controller.py,config_haslach.ini,temperature_sensor.py,display.py,relay.py,shelly_plug_m_gen3.py,modbus/**"
---

# Haslach Control Instructions

Keep changes safe for the Haslach runtime profile and avoid regressions in Bishop.

## Scope Guard

- Treat [main_haslach.py](main_haslach.py), [controller.py](controller.py), and [config_haslach.ini](config_haslach.ini) as Haslach-critical.
- If touching shared modules, confirm behavior remains valid for [main_bishop.py](main_bishop.py).

## Required Checks For Control Changes

1. Validate sign conventions in control logic:
   - Negative power means export/excess generation.
2. Preserve HP cooldown semantics driven by `min_hp_off_seconds`.
3. Keep config key names backward-compatible whenever possible.

## Test And Verification

- Default environment: use existing conda env `solarcontrol` (sometimes referred to by typo `solarconrol` in chat).
- Do not create a new virtual environment unless explicitly requested.
- Run targeted tests first:
  - `conda run -n solarcontrol python -m unittest -v tests/test_controller.py`
  - `conda run -n solarcontrol python -m unittest -v tests/test_fhs280.py`

## Hardware Boundaries

- Mock GPIO, Modbus serial, and network APIs in tests.
- Do not assume GPIO/I2C/1-Wire are available on dev machines.
- Keep hardware protocol details in adapters, not in controller state logic.
