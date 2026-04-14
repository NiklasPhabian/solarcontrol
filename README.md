# Install

## Python-kasa

```bash
rm -rf ~/envs/pv
python3 -m venv ~/envs/pv
source ~/envs/pv/bin/activate.fish
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
i2cdetect -y 1
```

```bash
sudo apt install libjpeg-dev
pip install luma.oled
```




# Run the displaying as service

Create the systemd unit from the template in this repository:

```bash
sudo cp pv-oled-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pv-oled-display.service
```

If you need to inspect it, the unit template is available in `pv-oled-display.service`.


# Making pngs

```bash
pip install pandas==1.5.3
```
