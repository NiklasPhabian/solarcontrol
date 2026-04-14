#!/bin/sh
set -e

# Change to the repository directory so relative imports and config file paths resolve.
cd "$(dirname "$0")"

# Use the virtualenv Python directly so cron does not depend on PATH.
PYTHON=/home/griessbaum/envs/pv/bin/python

exec "$PYTHON" store_realtime.py
