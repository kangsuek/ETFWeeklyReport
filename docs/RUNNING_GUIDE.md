# 실행 가이드

## 서버 실행

### 백엔드 서버 시작
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

서버 확인: http://localhost:8000/api/health

### Swagger UI로 테스트
http://localhost:8000/docs

## 주요 테스트 시나리오

### 1. 전체 종목 목록 조회
```bash
curl http://localhost:8000/api/etfs/ | python3 -m json.tool
```

### 2. 데이터 수집
```bash
curl -X POST "http://localhost:8000/api/etfs/487240/collect?days=10"
```

### 3. 가격 데이터 조회
```bash
curl "http://localhost:8000/api/etfs/487240/prices?start_date=2025-11-01&end_date=2025-11-07"
```

## 데이터베이스 확인
```bash
cd backend
sqlite3 data/etf_report.db

# 전체 종목 목록
SELECT * FROM etfs;

# 특정 종목의 가격 데이터
SELECT * FROM prices WHERE ticker = '487240' ORDER BY date DESC LIMIT 10;
```

## 문제 해결

### 서버가 시작되지 않는 경우
- 포트가 이미 사용 중: 다른 포트 사용 (`--port 8001`)
- 가상환경 비활성화: `source venv/bin/activate`

### 데이터 수집이 실패하는 경우
- 네트워크 연결 확인: `curl https://finance.naver.com/`
- 종목 코드 확인: 데이터베이스에 종목이 등록되어 있는지 확인
