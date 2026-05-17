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

## 3. GitHub 자동 배포 (Google Compute Engine)

`main` 브랜치에 코드가 푸시되면 GitHub Actions가 Google Compute Engine VM에 SSH로 접속해 자동 배포를 수행합니다.

### 3-1. 워크플로 파일

- `.github/workflows/deploy_gce.yml`

### 3-2. GitHub Secrets 설정

저장소 `Settings > Secrets and variables > Actions`에 아래 값을 등록하세요.

- `GCP_CREDENTIALS_JSON`: Google Cloud 서비스 계정 키 JSON 전체 내용
- `GCE_INSTANCE_NAME`: Compute Engine VM 이름
- `GCE_ZONE`: VM이 속한 zone
- `GCE_SSH_USER`: VM SSH 사용자명
- `GCE_SSH_PRIVATE_KEY`: 배포용 SSH 개인키 전체 내용
- `GCE_APP_DIR`: VM 안의 프로젝트 경로
- `GCE_DEPLOY_BRANCH`: 배포할 브랜치명, 비워두면 `main`
- `GCE_DASHBOARD_SERVICE`: 대시보드 systemd 서비스명
- `GCE_COLLECTOR_SERVICE`: 수집기 systemd 서비스명
- `GCE_DASHBOARD_HEALTH_URL`: 선택값, 배포 후 확인할 대시보드 URL

### 3-3. Google Cloud 준비 사항

- 서비스 계정은 최소한 VM 메타데이터 조회와 SSH 접속에 필요한 권한을 가져야 함
- GitHub Actions에서 사용할 SSH 개인키와 VM에 등록된 공개키가 서로 짝이 맞아야 함
- VM 방화벽과 OS Login 또는 메타데이터 SSH 설정이 GitHub Actions 접속 방식과 맞아야 함
- VM 안 `GCE_APP_DIR` 경로에 이미 git clone 되어 있어야 함
- VM에서 `python3`, `venv`, `git`, `systemd`, `curl` 사용 가능해야 함
- `GCE_DASHBOARD_SERVICE`, `GCE_COLLECTOR_SERVICE`는 실제 systemd 서비스명이어야 함
- 서비스의 `ExecStart`는 프로젝트 `.venv` 경로를 사용하도록 맞추는 편이 안전함

예시:

```ini
ExecStart=/home/ubuntu/naver-rank-dashboard/.venv/bin/python /home/ubuntu/naver-rank-dashboard/run_collector_loop.py
```

```ini
ExecStart=/home/ubuntu/naver-rank-dashboard/.venv/bin/streamlit run /home/ubuntu/naver-rank-dashboard/dashboard.py --server.port 8501
```

### 3-4. 배포 시 수행 작업

1. VM 접속
2. 지정 브랜치 최신 코드 가져오기
3. `.venv` 생성 및 `requirements.txt` 재설치
4. 대시보드/수집기 서비스 재시작
5. 서비스 active 상태 검증
6. `GCE_DASHBOARD_HEALTH_URL`이 있으면 HTTP 헬스체크 수행
