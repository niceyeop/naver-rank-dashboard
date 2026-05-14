# 네이버 기사 실시간 조회수 순위 대시보드

네이버 통계 API에서 기사별 실시간 조회수 순위(`pvRank`)를 10분 단위로 수집하고, Streamlit 대시보드에서 시각화하는 프로그램입니다.

팀원들은 별도 설치 없이 웹 브라우저에서 대시보드 주소로 접속해 실시간 순위를 확인할 수 있습니다.

---

## 1. 주요 기능

- 네이버 기사 조회수 순위 자동 수집
- 10분 단위 정각 수집  
  예: 00분, 10분, 20분, 30분, 40분, 50분
- 날짜별 조회수 순위 확인
- 당일 기준 조회수 순위 자동 초기화
- 최신 시각 데이터 자동 표시
- 직전 수집 시각 대비 조회수 증가량 표시
- 기사별 조회수 추이 확인
- SQLite DB에 수집 데이터 저장
- Streamlit 웹 대시보드 제공
- 클라우드 서버에서 24시간 운영 가능

---

## 2. 전체 구조

```text
naver-rank-dashboard/
├── collect.py                # 네이버 통계 API 호출 및 데이터 저장
├── run_collector_loop.py     # 10분 단위 자동 수집 루프
├── dashboard.py              # Streamlit 대시보드
├── requirements.txt          # Python 패키지 목록
├── .env                      # API URL, 쿠키 등 환경설정 파일
├── naver_rank.db             # SQLite 데이터베이스
├── naver_cookies.txt         # 자동 저장되는 쿠키 파일
├── collector.log             # 수집기 로그
├── dashboard.log             # 대시보드 로그
└── README.md                 # 설명 문서
```

---

## 3. GitHub 자동 배포 (네이버클라우드)

`main` 브랜치에 코드가 푸시되면 GitHub Actions가 네이버클라우드 서버에 SSH로 접속해 자동 배포를 수행합니다.

### 3-1. 워크플로 파일

- `.github/workflows/deploy_ncloud.yml`

### 3-2. GitHub Secrets 설정

저장소 `Settings > Secrets and variables > Actions`에 아래 값을 등록하세요.

- `NCLOUD_HOST`: 네이버클라우드 서버 IP 또는 도메인
- `NCLOUD_USER`: SSH 로그인 사용자
- `NCLOUD_SSH_KEY`: 배포용 개인키(멀티라인 전체)
- `NCLOUD_PORT`: SSH 포트(일반적으로 `22`)
- `NCLOUD_APP_DIR`: 서버의 프로젝트 경로 (예: `/home/ubuntu/naver-rank-dashboard`)
- `NCLOUD_DEPLOY_BRANCH`: 배포할 브랜치명 (미입력 시 `main`)
- `NCLOUD_DASHBOARD_SERVICE`: 대시보드 서비스명 (예: `naver-rank-dashboard.service`)
- `NCLOUD_COLLECTOR_SERVICE`: 수집기 서비스명 (예: `naver-rank-collector.service`)

### 3-3. 서버 선행 조건

- `NCLOUD_APP_DIR` 경로에 이미 git clone 되어 있어야 함
- 서버에서 `python3`, `pip`, `systemd`, `git` 사용 가능해야 함
- `NCLOUD_DASHBOARD_SERVICE`, `NCLOUD_COLLECTOR_SERVICE`에 입력한 서비스명이 실제로 존재해야 함
- 배포 사용자에게 `sudo systemctl restart ...` 권한이 있어야 함

### 3-4. 배포 시 수행 작업

1. 서버 접속
2. 지정 브랜치 최신 코드 가져오기
3. `requirements.txt` 재설치
4. 대시보드/수집기 서비스 재시작
5. 서비스 active 상태 검증
