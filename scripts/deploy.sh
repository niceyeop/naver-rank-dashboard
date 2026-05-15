#!/bin/bash
# GitHub Actions에서 SSH로 호출되는 배포 스크립트
set -e

APP_DIR="/opt/naver-rank-dashboard"

echo "=== [1/3] 코드 최신화 ==="
cd "$APP_DIR"
git pull origin main

echo "=== [2/3] 패키지 업데이트 ==="
"$APP_DIR/venv/bin/pip" install -q --upgrade -r requirements.txt

echo "=== [3/3] 서비스 재시작 ==="
sudo systemctl restart naver-collector
sudo systemctl restart naver-dashboard

echo "배포 완료: $(date '+%Y-%m-%d %H:%M:%S')"
sudo systemctl status naver-collector --no-pager -l | tail -5
sudo systemctl status naver-dashboard --no-pager -l | tail -5
