# Install

## Env setup
```bash
sudo mkdir -p /opt/solarcontrol
sudo chown -R $USER:$USER /opt/solarcontrol
python3 -m venv /opt/solarcontrol/venv
source /opt/solarcontrol/venv/bin/activate.fish
pip install --upgrade pip
```


## Python-kasa
```bash
pip install --upgrade pip setuptools wheel
pip install "cryptography<42"
pip install python-kasa
```

## Display

```bash
cat /proc/device-tree/model
```

| OLED Pin | Pi Pin | Description |
| -------- | ------ | ----------- |
| GND      | Pin 6  | Ground      |
| VCC      | Pin 1  | 3.3V        |
| SDA      | Pin 3  | I²C data    |
| SCL      | Pin 5  | I²C clock   |


```bash
sudo raspi-config
```

Interface Options → I2C → Enable

```bash
sudo apt install i2c-tools
sudo i2cdetect -y 1
```

```bash
sudo apt install libjpeg-dev
pip install luma.oled
```

### Run the displaying as service

Create the systemd unit from the template in this repository:

```bash
sudo cp pv-oled-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pv-oled-display.service
```

If you need to inspect it, the unit template is available in `pv-oled-display.service`.

## Temperatue probes
### Activate kernel modules

#### Temporarily:
```bash
sudo modprobe w1-gpio
sudo modprobe w1-therm
```

#### Persist
```bash
sudo nano /etc/modules
``` 

Add
```
w1-gpio
w1-therm
```

reboot and verify with:

```bash
lsmod | grep w1
```

### Add overlays
#### Temporarily

```bash
sudo dtoverlay w1-gpio gpiopin=4 pullup=0
```

#### Persist

```bash
sudo nano /boot/config.txt 
```


```bash
dtoverlay=w1-gpio,gpiopin=4
```

Reboot and verify with:

```bash
ls /sys/bus/w1/devices/
```

#### Identification Notes for my BWWP system:

| ID                | Cable Color   |
| :--               | :--           |
| 28-3ce1d44312b4   | White         |
| 28-3ce1d4432b6f   | Black         |
| 28-3ce1d4438ff7   | Blue          |


# Making pngs

```bash
pip install pandas==1.5.3
```
