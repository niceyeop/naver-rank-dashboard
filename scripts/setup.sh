#!/bin/bash
# GCE VM 최초 1회 실행 — Python 환경, 서비스 설치, 방화벽 설정
set -e

REPO_URL="https://github.com/niceyeop/naver-rank-dashboard.git"
APP_DIR="/opt/naver-rank-dashboard"
GITHUB_USER="github-deploy"  # 배포 전용 리눅스 계정

echo "=== [1/6] 시스템 패키지 업데이트 ==="
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

echo "=== [2/6] 배포 계정 생성 ==="
if ! id "$GITHUB_USER" &>/dev/null; then
    sudo useradd -m -s /bin/bash "$GITHUB_USER"
fi

echo "=== [3/6] 코드 클론 ==="
sudo git clone "$REPO_URL" "$APP_DIR"
sudo chown -R "$GITHUB_USER:$GITHUB_USER" "$APP_DIR"

echo "=== [4/6] Python 가상환경 및 패키지 설치 ==="
sudo -u "$GITHUB_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$GITHUB_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$GITHUB_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "=== [5/6] .env 파일 생성 ==="
echo "아래 내용을 채워서 $APP_DIR/.env 에 저장하세요:"
cat << 'EOF'
DB_PATH=/opt/naver-rank-dashboard/naver_rank.db
NAVER_STATS_URL=
NAVER_METHOD=GET
NAVER_REFERER=
NAVER_COOKIE=
NAVER_BODY=
COOKIE_JAR_PATH=/opt/naver-rank-dashboard/naver_cookies.txt
EOF

echo "=== [6/6] systemd 서비스 설치 ==="
# 서비스 파일의 User= 를 배포 계정으로 수정
sudo sed "s/User=ubuntu/User=$GITHUB_USER/" "$APP_DIR/naver-collector.service" \
    | sudo tee /etc/systemd/system/naver-collector.service > /dev/null

sudo sed "s/User=ubuntu/User=$GITHUB_USER/" "$APP_DIR/naver-dashboard.service" \
    | sudo tee /etc/systemd/system/naver-dashboard.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable naver-collector naver-dashboard

echo ""
echo "============================="
echo " 설치 완료!"
echo "============================="
echo " 1. $APP_DIR/.env 파일을 네이버 클라우드에서 가져와 채우세요"
echo " 2. 네이버 클라우드에서 DB 파일 복사:"
echo "    scp user@naver-cloud-ip:/path/to/naver_rank.db $APP_DIR/"
echo " 3. 서비스 시작:"
echo "    sudo systemctl start naver-collector naver-dashboard"
echo " 4. 상태 확인:"
echo "    sudo systemctl status naver-collector naver-dashboard"
