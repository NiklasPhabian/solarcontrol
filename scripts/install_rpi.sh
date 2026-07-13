#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/install_rpi.sh --profile <haslach|bishop> [options]

Options:
  --profile <name>      Required. One of: haslach, bishop
  --service-user <user> Linux user that runs systemd service (default: current user)
  --install-dir <path>  Install root directory (default: /opt/solarcontrol)
  --repo-path <path>    Repository path to link/copy as app (default: current directory)
  --copy-app            Copy app to install dir instead of symlink
  --skip-packages       Skip apt package installation
  --skip-nginx          Skip nginx site installation
  --skip-enable         Skip systemctl enable/start
  -h, --help            Show help

Examples:
  scripts/install_rpi.sh --profile haslach
  scripts/install_rpi.sh --profile bishop --service-user pi --copy-app
EOF
}

PROFILE=""
SERVICE_USER="${USER}"
INSTALL_DIR="/opt/solarcontrol"
REPO_PATH="$(pwd -P)"
COPY_APP=0
SKIP_PACKAGES=0
SKIP_NGINX=0
SKIP_ENABLE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    --service-user)
      SERVICE_USER="${2:-}"
      shift 2
      ;;
    --install-dir)
      INSTALL_DIR="${2:-}"
      shift 2
      ;;
    --repo-path)
      REPO_PATH="${2:-}"
      shift 2
      ;;
    --copy-app)
      COPY_APP=1
      shift
      ;;
    --skip-packages)
      SKIP_PACKAGES=1
      shift
      ;;
    --skip-nginx)
      SKIP_NGINX=1
      shift
      ;;
    --skip-enable)
      SKIP_ENABLE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$PROFILE" != "haslach" && "$PROFILE" != "bishop" ]]; then
  echo "Error: --profile must be one of: haslach, bishop" >&2
  usage
  exit 1
fi

if [[ ! -d "$REPO_PATH" ]]; then
  echo "Error: repo path does not exist: $REPO_PATH" >&2
  exit 1
fi

if [[ ! -f "$REPO_PATH/requirements.txt" ]]; then
  echo "Error: repo path does not look like solarcontrol root: $REPO_PATH" >&2
  exit 1
fi

if [[ "$PROFILE" == "haslach" ]]; then
  UNIT_TEMPLATE="$REPO_PATH/systemd/solarcontrol-haslach.service"
  ENTRYPOINT="main_haslach.py"
  CONFIG_FILE="$REPO_PATH/config_haslach.ini"
else
  UNIT_TEMPLATE="$REPO_PATH/systemd/solarcontrol-bishop.service"
  ENTRYPOINT="main_bishop.py"
  CONFIG_FILE="$REPO_PATH/config_bishop.ini"
fi

if [[ ! -f "$UNIT_TEMPLATE" ]]; then
  echo "Error: missing unit template: $UNIT_TEMPLATE" >&2
  exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Error: missing profile config file: $CONFIG_FILE" >&2
  exit 1
fi

echo "[1/9] Installing base packages"
if [[ "$SKIP_PACKAGES" -eq 0 ]]; then
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
else
  echo "  skipped (--skip-packages)"
fi

echo "[2/9] Creating install layout"
sudo mkdir -p "$INSTALL_DIR"
if [[ "$COPY_APP" -eq 1 ]]; then
  sudo rm -rf "$INSTALL_DIR/app"
  sudo cp -a "$REPO_PATH" "$INSTALL_DIR/app"
else
  sudo ln -sfn "$REPO_PATH" "$INSTALL_DIR/app"
fi
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

echo "[3/9] Creating Python virtual environment"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/app/requirements.txt"

echo "[4/9] Ensuring service user has hardware access groups"
sudo usermod -aG gpio,i2c,dialout "$SERVICE_USER"

echo "[5/9] Installing profile-specific systemd unit"
TMP_UNIT="$(mktemp)"
sed \
  -e "s|__SERVICE_USER__|$SERVICE_USER|g" \
  -e "s|__WORKING_DIR__|$INSTALL_DIR/app|g" \
  -e "s|__EXEC_START__|$INSTALL_DIR/venv/bin/python $ENTRYPOINT|g" \
  "$UNIT_TEMPLATE" > "$TMP_UNIT"
sudo cp "$TMP_UNIT" /etc/systemd/system/solarcontrol.service
rm -f "$TMP_UNIT"

echo "[6/9] Installing nginx site"
if [[ "$SKIP_NGINX" -eq 0 ]]; then
  sudo cp "$INSTALL_DIR/app/nginx/plotter_images.conf" /etc/nginx/sites-available/solarcontrol_plots
  sudo ln -sfn /etc/nginx/sites-available/solarcontrol_plots /etc/nginx/sites-enabled/solarcontrol_plots
  sudo rm -f /etc/nginx/sites-enabled/default
  sudo nginx -t
  sudo systemctl enable --now nginx
  sudo systemctl reload nginx
else
  echo "  skipped (--skip-nginx)"
fi

echo "[7/9] Reloading systemd"
sudo systemctl daemon-reload

echo "[8/9] Enabling services"
if [[ "$SKIP_ENABLE" -eq 0 ]]; then
  sudo systemctl enable --now solarcontrol.service
else
  echo "  skipped (--skip-enable)"
fi

echo "[9/9] Final notes"
echo "Installation complete for profile: $PROFILE"
echo "Service user: $SERVICE_USER"
echo
echo "Next manual checks:"
echo "  1) Verify and edit profile config if needed: $CONFIG_FILE"
echo "  2) Enable I2C in raspi-config if display is used"
echo "  3) Enable 1-wire overlay for DS18B20 sensors if used"
echo "  4) Log out and back in so new groups apply"
echo
echo "Useful commands:"
echo "  sudo systemctl status solarcontrol.service"
echo "  journalctl -u solarcontrol.service -f"
echo "  sudo nginx -t"
