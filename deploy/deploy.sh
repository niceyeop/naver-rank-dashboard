#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-$(pwd)}"
SERVICE_NAME="${SERVICE_NAME:-naver-rank-dashboard}"
APP_PORT="${APP_PORT:-8501}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

cd "$APP_DIR"

echo "[deploy] app dir: $APP_DIR"
echo "[deploy] service: $SERVICE_NAME"
echo "[deploy] port: $APP_PORT"

git pull --ff-only origin main

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt

sudo systemctl restart "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager
