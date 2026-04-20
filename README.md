# Install

```bash
cd solarcontrol
sudo mkdir -p /opt/solarcontrol
#sudo cp -r . /opt/solarcontrol
sudo ln -s "$(pwd -P)" /opt/solarcontrol

sudo chown -R $USER:$USER /opt/solarcontrol
```

```bash
cd /opt/solarcontrol
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

# install dependencies
pip install -r requirements.txt


## Service
Create the systemd unit from the template in this repository:

```bash
sudo cp solarcontrol.service /etc/systemd/system/solarcontrol.service
sudo systemctl daemon-reload
sudo systemctl enable --now solarcontrol.service
sudo systemctl daemon-reload
journalctl -u solarcontrol -f
```

# Development 
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

#### Identification Notes 

| ID                | Sensor                |
| :--               | :--                   |
| 28-3ce1d44312b4   | Haslach White         |
| 28-3ce1d4432b6f   | Haslach Black         |
| 28-3ce1d4438ff7   | Haslach Blue          |
| 28-3ce1d4431e7c   | Bishop Solar          |


# Making pngs

```bash
pip install pandas==1.5.3
```
