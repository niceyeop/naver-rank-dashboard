#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/home/ubuntu/naver-rank-dashboard}"
RUN_USER="${2:-ubuntu}"
SYSTEMD_DIR="/etc/systemd/system"

install_unit() {
  local src="$1"
  local dest="$2"

  sed \
    -e "s|/home/ubuntu/naver-rank-dashboard|${APP_DIR}|g" \
    -e "s|User=ubuntu|User=${RUN_USER}|g" \
    "$src" | sudo tee "${SYSTEMD_DIR}/${dest}" >/dev/null
}

install_unit "deploy/gce/naver-rank-dashboard.service" "naver-rank-dashboard.service"
install_unit "deploy/gce/naver-rank-collector.service" "naver-rank-collector.service"

sudo systemctl daemon-reload
sudo systemctl enable naver-rank-dashboard.service
sudo systemctl enable naver-rank-collector.service
sudo systemctl restart naver-rank-dashboard.service
sudo systemctl restart naver-rank-collector.service
sudo systemctl status --no-pager naver-rank-dashboard.service
sudo systemctl status --no-pager naver-rank-collector.service
