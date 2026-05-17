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

## 3. 배포 메모

현재 레포에는 특정 클라우드 환경에 종속된 GitHub Actions 배포 설정이 포함되어 있지 않습니다.

Google Cloud에 올릴 경우에는 실제 배포 방식에 맞춰 별도의 설정을 추가하는 편이 안전합니다. 예를 들면 아래 중 하나입니다.

- Compute Engine + systemd
- Cloud Run
- GKE
