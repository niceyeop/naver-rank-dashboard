#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/naver-rank-dashboard}"
APP_PORT="${APP_PORT:-8501}"

cd "$APP_DIR"
source .venv/bin/activate

exec streamlit run dashboard.py \
  --server.address 0.0.0.0 \
  --server.port "$APP_PORT"
