# Install

## Dependencies
```bash
sudo apt install i2c-tools
sudo apt install libjpeg-dev
sudo apt install libopenblas0
```

## Install
```bash
cd solarcontrol
set INSTALLDIR /opt/solarcontrol
sudo mkdir -p $INSTALLDIR
#sudo cp -r . $INSTALLDIR/app
sudo ln -s (pwd -P) $INSTALLDIR/app
sudo chown -R $USER:$USER $INSTALLDIR
```

## Env setup
```bash
cd $INSTALLDIR
python3 -m venv venv
source venv/bin/activate.fish
pip install --upgrade pip
pip install -r app/requirements.txt
```

## Service
Create the systemd unit from the template in this repository:

```bash
sudo cp solarcontrol.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now solarcontrol.service
sudo systemctl status solarcontrol
journalctl -u solarcontrol -f
```


# Development 

## Python-kasa
```bash
pip install --upgrade pip
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


## Serving Plotter images with nginx

The plotter generates PNG images and an HTML index page in the `www/` subdirectory. To serve these through nginx on port 80:

1. Copy the nginx configuration:

```bash
sudo cp nginx/plotter_images.conf /etc/nginx/sites-available/solarcontrol_plots
sudo ln -s /etc/nginx/sites-available/solarcontrol_plots /etc/nginx/sites-enabled/
```

2. **Important**: Disable the default nginx site to avoid port 80 conflicts:

```bash
sudo unlink /etc/nginx/sites-enabled/default
```

   *Why?* The default nginx installation includes a site that also listens on port 80. Having multiple sites on the same port causes conflicts.

   **Alternative**: If you want to keep the default site, you can either:
   - Use a different port (change `listen 80;` to `listen 8080;` in the config)
   - Add a specific `server_name` directive to distinguish between sites

3. Update the `alias` path in `/etc/nginx/sites-available/solarcontrol_plots` to point to your app's `www/` directory (if different from the default installation path).

4. Test the configuration and reload nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

5. Access the generated images and HTML gallery at `http://<server>/plots/`.

### Troubleshooting

If nginx fails to start or reload on your server:

- **Port 80 conflict**: Check if another service is using port 80:
  ```bash
  sudo netstat -tlnp | grep :80
  sudo lsof -i :80
  ```

- **Permission issues**: Ensure nginx can read the `www/` directory:
  ```bash
  sudo chown -R www-data:www-data /opt/solarcontrol/app/www/
  ```

- **SELinux/AppArmor**: If running on systems with security modules, ensure nginx has access to the directory.

- **Test configuration**: Always test before reloading:
  ```bash
  sudo nginx -t
  ```

During development, you can serve directly from the repository by setting the alias to the repo's `www/` folder instead of the installation path.
