# SolarControl Raspberry Pi Setup

This guide documents everything needed to get a fresh Raspberry Pi from zero to a running SolarControl deployment.

It covers:
- OS packages and hardware interfaces
- Application installation layout under `/opt/solarcontrol`
- Python environment and dependencies
- Configuration files (`config_haslach.ini` or `config_bishop.ini`)
- systemd service setup
- nginx setup to serve generated plots
- A preflight checklist before enabling startup

## Quick Start (Automated)

For a one-command setup, use the installer script:

```bash
cd /path/to/solarcontrol
bash scripts/install_rpi.sh --profile haslach --service-user <your-linux-user>
# or
bash scripts/install_rpi.sh --profile bishop --service-user <your-linux-user>
```

What it does:
- installs required apt packages
- creates `/opt/solarcontrol` layout
- creates virtualenv and installs Python dependencies
- installs profile-specific systemd service
- configures nginx site and enables services
- adds service user to `gpio`, `i2c`, and `dialout` groups

Optional flags:

```text
--copy-app
--skip-packages
--skip-nginx
--skip-enable
--install-dir <path>
--repo-path <path>
```

## 1. Base System Packages

```bash
sudo apt update
sudo apt install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  i2c-tools \
  libjpeg-dev \
  libopenblas0 \
  nginx
```

## 2. Clone Repository

```bash
cd ~
git clone <your-repo-url> solarcontrol
cd solarcontrol
```

## 3. Create Installation Layout in /opt

SolarControl expects:
- app code at `/opt/solarcontrol/app`
- virtualenv at `/opt/solarcontrol/venv`

Use a symlink during development (recommended):

```bash
INSTALLDIR=/opt/solarcontrol
sudo mkdir -p "$INSTALLDIR"
sudo ln -sfn "$(pwd -P)" "$INSTALLDIR/app"
sudo chown -R "$USER:$USER" "$INSTALLDIR"
```

If you use fish shell:

```fish
set INSTALLDIR /opt/solarcontrol
sudo mkdir -p $INSTALLDIR
sudo ln -sfn (pwd -P) $INSTALLDIR/app
sudo chown -R $USER:$USER $INSTALLDIR
```

## 4. Python Environment

```bash
cd /opt/solarcontrol
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt
```

For fish shell activation:

```fish
source /opt/solarcontrol/venv/bin/activate.fish
```

## 5. Configure Raspberry Pi Interfaces

### I2C (OLED display)

```bash
sudo raspi-config
```

Enable: Interface Options -> I2C -> Enable

Verify:

```bash
sudo i2cdetect -y 1
```

OLED wiring:

| OLED Pin | Pi Pin | Description |
| -------- | ------ | ----------- |
| GND      | Pin 6  | Ground      |
| VCC      | Pin 1  | 3.3V        |
| SDA      | Pin 3  | I2C data    |
| SCL      | Pin 5  | I2C clock   |

### 1-wire temperature probes

Load modules now:

```bash
sudo modprobe w1-gpio
sudo modprobe w1-therm
```

Persist modules:

```bash
printf "w1-gpio\nw1-therm\n" | sudo tee -a /etc/modules
```

Persist overlay in `/boot/config.txt`:

```bash
echo "dtoverlay=w1-gpio,gpiopin=4" | sudo tee -a /boot/config.txt
```

Reboot and verify:

```bash
sudo reboot
# after reboot
ls /sys/bus/w1/devices/
```

Known sensor IDs:

| ID                | Sensor        |
| :--               | :--           |
| 28-3ce1d44312b4   | Haslach White |
| 28-3ce1d4432b6f   | Haslach Black |
| 28-3ce1d4438ff7   | Haslach Blue  |
| 28-3ce1d4431e7c   | Bishop Solar  |

## 6. Configure App

Choose one profile:

### Haslach profile

```bash
cd /opt/solarcontrol/app
cp config_haslach.ini config_haslach.local.ini
```

Then edit `config_haslach.ini` (or update service/entrypoint to use your chosen file):
- `[ecotracker] host`
- `[sqlite] db_path`
- `[temp_sensors]` IDs
- `[modbus_controller] port` (usually `/dev/ttyUSB0`)
- `[modbus_slave_addresses]`

### Bishop profile

```bash
cd /opt/solarcontrol/app
cp config_bishop.ini config_bishop.local.ini
```

Then edit `config_bishop.ini` (or update service/entrypoint to use your chosen file):
- `[kasa] username/password`
- meter host IPs
- `[sqlite] db_path`
- `[temp_sensors]`

Important:
- `main_haslach.py` loads `config_haslach.ini`
- `main_bishop.py` loads `config_bishop.ini`

If you prefer separate local files (`*.local.ini`), update the corresponding main file or service command accordingly.

## 7. Linux Permissions for Hardware Access

The service user needs access to GPIO, I2C, and USB serial (for Modbus adapters).

```bash
SERVICE_USER=<your-linux-user>
sudo usermod -aG gpio,i2c,dialout "$SERVICE_USER"
```

Re-login (or reboot) so group changes apply.

Confirm serial adapter appears:

```bash
ls -l /dev/ttyUSB*
```

## 8. systemd Service

Two service templates exist:
- `systemd/solarcontrol-haslach.service` -> starts Haslach profile
- `systemd/solarcontrol-bishop.service` -> starts Bishop profile

Copy the one you need and replace placeholders:

```bash
cd /opt/solarcontrol/app
sudo cp systemd/solarcontrol-haslach.service /etc/systemd/system/solarcontrol.service
sudo nano /etc/systemd/system/solarcontrol.service
```

Replace:
- `__SERVICE_USER__` -> your Linux user
- `__WORKING_DIR__` -> `/opt/solarcontrol/app`
- `__EXEC_START__` -> `/opt/solarcontrol/venv/bin/python main_haslach.py` (or `main_bishop.py`)

If you prefer the existing legacy unit files in repo root (`solarcontrol.service`, `solarcontrol.example.service`), you can still use them.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now solarcontrol.service
sudo systemctl status solarcontrol.service
journalctl -u solarcontrol.service -f
```

## 9. nginx for Plot Images and HTML

SolarControl writes plots and `index.html` into `www/` under the app directory.

Install nginx config:

```bash
cd /opt/solarcontrol/app
sudo cp nginx/plotter_images.conf /etc/nginx/sites-available/solarcontrol_plots
sudo ln -sfn /etc/nginx/sites-available/solarcontrol_plots /etc/nginx/sites-enabled/solarcontrol_plots
sudo rm -f /etc/nginx/sites-enabled/default
```

The provided config serves from:
- `location /`
- `alias /opt/solarcontrol/app/www/`

Test and reload:

```bash
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

Open:

```text
http://<raspberry-pi-ip>/
```

Do not set ownership of `www/` to `www-data` if the app service user writes plot files there. Keep app write permissions intact and ensure nginx has read access.

## 10. Preflight Checklist

Run this before relying on auto-start:

```bash
set -e

echo "== Service file =="
sudo systemctl cat solarcontrol.service >/dev/null

echo "== Python venv =="
test -x /opt/solarcontrol/venv/bin/python

echo "== App path =="
test -d /opt/solarcontrol/app

echo "== Config file present =="
test -f /opt/solarcontrol/app/config_haslach.ini || test -f /opt/solarcontrol/app/config_bishop.ini

echo "== 1-wire devices =="
ls /sys/bus/w1/devices/ | grep -E '^28-' || true

echo "== I2C bus =="
sudo i2cdetect -y 1 >/dev/null

echo "== Modbus serial adapter =="
ls /dev/ttyUSB* >/dev/null

echo "== nginx config =="
sudo nginx -t

echo "== Final status =="
systemctl is-active solarcontrol.service
systemctl is-active nginx
echo "Preflight complete"
```

## 11. Optional: Local Manual Start

For quick debugging without systemd:

```bash
cd /opt/solarcontrol/app
source /opt/solarcontrol/venv/bin/activate
python main_haslach.py
# or
python main_bishop.py
```
