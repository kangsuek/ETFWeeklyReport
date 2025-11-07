# 🚀 Phase 1 실행 및 테스트 가이드

Phase 1까지 완료된 백엔드 기능을 실제로 실행하고 테스트하는 방법을 안내합니다.

---

## 📋 목차

1. [서버 실행](#1️⃣-서버-실행)
2. [Swagger UI로 테스트](#2️⃣-swagger-ui로-테스트)
3. [cURL로 테스트](#3️⃣-curl로-테스트)
4. [Python으로 테스트](#4️⃣-python으로-테스트)
5. [데이터베이스 확인](#5️⃣-데이터베이스-확인)
6. [문제 해결](#6️⃣-문제-해결)

---

## 1️⃣ 서버 실행

### 백엔드 서버 시작

```bash
# 프로젝트 루트에서
cd backend

# 가상환경 활성화
source venv/bin/activate

# 환경 변수 설정 (필요시)
export PYTHONPATH=/Users/kangsuek/pythonProject/ETFWeeklyReport/backend

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**서버가 정상적으로 시작되면 다음 메시지가 표시됩니다:**

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 서버 상태 확인

```bash
curl http://localhost:8000/api/health
```

**예상 결과:**
```json
{
  "status": "healthy",
  "message": "ETF Report API is running"
}
```

---

## 2️⃣ Swagger UI로 테스트

**가장 쉽고 추천하는 방법입니다!**

### 1. 웹 브라우저 열기

```
http://localhost:8000/docs
```

### 2. API 엔드포인트 테스트

Swagger UI에서 다음을 수행할 수 있습니다:

#### ✅ 전체 종목 목록 조회
1. `GET /api/etfs/` 섹션 클릭
2. **"Try it out"** 버튼 클릭
3. **"Execute"** 버튼 클릭
4. 6개 종목 목록 확인 (ETF 4개 + 주식 2개)

#### ✅ 특정 종목 정보 조회
1. `GET /api/etfs/{ticker}` 섹션 클릭
2. **"Try it out"** 버튼 클릭
3. ticker에 `487240` 입력
4. **"Execute"** 버튼 클릭

#### ✅ 데이터 수집 (Naver Finance)
1. `POST /api/etfs/{ticker}/collect` 섹션 클릭
2. **"Try it out"** 버튼 클릭
3. ticker에 `487240` 입력
4. days에 `10` 입력 (10일치 데이터)
5. **"Execute"** 버튼 클릭
6. 수집 결과 확인

#### ✅ 가격 데이터 조회
1. `GET /api/etfs/{ticker}/prices` 섹션 클릭
2. **"Try it out"** 버튼 클릭
3. ticker에 `487240` 입력
4. 날짜 범위 설정 (선택 사항)
5. **"Execute"** 버튼 클릭
6. 수집된 가격 데이터 확인

---

## 3️⃣ cURL로 테스트

터미널에서 직접 API를 호출하여 테스트할 수 있습니다.

### 1. 전체 종목 목록 조회

```bash
curl -X GET "http://localhost:8000/api/etfs/" | python3 -m json.tool
```

**예상 결과:**
```json
[
  {
    "ticker": "487240",
    "name": "삼성 KODEX AI전력핵심설비 ETF",
    "type": "ETF",
    "theme": "AI/전력",
    "launch_date": "2024-03-15",
    "expense_ratio": 0.0045
  },
  {
    "ticker": "466920",
    "name": "신한 SOL 조선TOP3플러스 ETF",
    "type": "ETF",
    "theme": "조선",
    "launch_date": "2023-08-10",
    "expense_ratio": 0.005
  }
  // ... 4개 더
]
```

### 2. 특정 종목 정보 조회

```bash
curl -X GET "http://localhost:8000/api/etfs/487240" | python3 -m json.tool
```

### 3. 데이터 수집 (Naver Finance)

```bash
# KODEX AI전력핵심설비 ETF - 10일치
curl -X POST "http://localhost:8000/api/etfs/487240/collect?days=10" | python3 -m json.tool

# 한화오션 - 5일치
curl -X POST "http://localhost:8000/api/etfs/042660/collect?days=5" | python3 -m json.tool

# 두산에너빌리티 - 5일치
curl -X POST "http://localhost:8000/api/etfs/034020/collect?days=5" | python3 -m json.tool
```

**예상 결과:**
```json
{
  "ticker": "487240",
  "collected": 10,
  "message": "Successfully collected 10 price records"
}
```

### 4. 가격 데이터 조회

```bash
# 기본 조회 (최근 7일)
curl -X GET "http://localhost:8000/api/etfs/487240/prices" | python3 -m json.tool

# 날짜 범위 지정
curl -X GET "http://localhost:8000/api/etfs/487240/prices?start_date=2025-11-01&end_date=2025-11-07" | python3 -m json.tool
```

**예상 결과:**
```json
[
  {
    "date": "2025-11-07",
    "open_price": 24350.0,
    "high_price": 25810.0,
    "low_price": 24350.0,
    "close_price": 25695.0,
    "volume": 1705721,
    "daily_change_pct": -0.27
  },
  {
    "date": "2025-11-06",
    "open_price": 26705.0,
    "high_price": 26965.0,
    "low_price": 25410.0,
    "close_price": 25765.0,
    "volume": 8225769,
    "daily_change_pct": 0.8
  }
  // ... 더 많은 데이터
]
```

### 5. 에러 테스트

```bash
# 존재하지 않는 종목 (404 에러)
curl -X GET "http://localhost:8000/api/etfs/999999"

# 잘못된 날짜 형식 (422 에러)
curl -X GET "http://localhost:8000/api/etfs/487240/prices?start_date=invalid-date"
```

---

## 4️⃣ Python으로 테스트

Python 스크립트로 API를 호출할 수 있습니다.

### 테스트 스크립트 작성

`test_api.py` 파일을 만들어주세요:

```python
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """헬스 체크"""
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

def test_get_all_etfs():
    """전체 종목 목록 조회"""
    response = requests.get(f"{BASE_URL}/api/etfs/")
    print(f"\n전체 종목 수: {len(response.json())}")
    for etf in response.json():
        print(f"- {etf['ticker']}: {etf['name']} ({etf['type']})")

def test_collect_data(ticker, days=10):
    """데이터 수집"""
    print(f"\n{ticker} 데이터 수집 중...")
    response = requests.post(f"{BASE_URL}/api/etfs/{ticker}/collect?days={days}")
    result = response.json()
    print(f"수집 완료: {result['collected']}개 레코드")
    return result

def test_get_prices(ticker):
    """가격 데이터 조회"""
    response = requests.get(f"{BASE_URL}/api/etfs/{ticker}/prices")
    prices = response.json()
    print(f"\n{ticker} 가격 데이터 ({len(prices)}개):")
    for price in prices[:3]:  # 최근 3일치만 출력
        print(f"  {price['date']}: {price['close_price']:,}원 ({price['daily_change_pct']:+.2f}%)")

if __name__ == "__main__":
    # 1. 헬스 체크
    print("=== 1. Health Check ===")
    test_health()
    
    # 2. 전체 종목 목록
    print("\n=== 2. 전체 종목 목록 ===")
    test_get_all_etfs()
    
    # 3. 데이터 수집
    print("\n=== 3. 데이터 수집 ===")
    test_collect_data("487240", days=10)
    test_collect_data("042660", days=5)
    
    # 4. 가격 데이터 조회
    print("\n=== 4. 가격 데이터 조회 ===")
    test_get_prices("487240")
    test_get_prices("042660")
```

### 스크립트 실행

```bash
python test_api.py
```

---

## 5️⃣ 데이터베이스 확인

SQLite 데이터베이스를 직접 확인할 수 있습니다.

### SQLite CLI로 확인

```bash
cd backend
sqlite3 data/etf_report.db

# 전체 종목 목록
SELECT * FROM etfs;

# 특정 종목의 가격 데이터
SELECT * FROM prices WHERE ticker = '487240' ORDER BY date DESC LIMIT 10;

# 수집된 데이터 통계
SELECT ticker, COUNT(*) as count FROM prices GROUP BY ticker;

# 종료
.quit
```

### Python으로 확인

```python
import sqlite3

conn = sqlite3.connect('backend/data/etf_report.db')
cursor = conn.cursor()

# 전체 종목 수
cursor.execute("SELECT COUNT(*) FROM etfs")
print(f"전체 종목 수: {cursor.fetchone()[0]}")

# 수집된 가격 데이터 수
cursor.execute("SELECT ticker, COUNT(*) FROM prices GROUP BY ticker")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}개 레코드")

conn.close()
```

---

## 6️⃣ 문제 해결

### 서버가 시작되지 않는 경우

1. **포트가 이미 사용 중인 경우**
   ```bash
   # 다른 포트로 실행
   uvicorn app.main:app --reload --port 8001
   ```

2. **가상환경이 활성화되지 않은 경우**
   ```bash
   source venv/bin/activate
   ```

3. **PYTHONPATH 설정 확인**
   ```bash
   export PYTHONPATH=/Users/kangsuek/pythonProject/ETFWeeklyReport/backend
   ```

### 데이터 수집이 실패하는 경우

1. **네트워크 연결 확인**
   ```bash
   curl https://finance.naver.com/
   ```

2. **로그 확인**
   - 서버 터미널에서 에러 메시지 확인
   - Naver Finance 접속 가능 여부 확인

3. **종목 코드 확인**
   - 정확한 종목 코드인지 확인
   - 데이터베이스에 종목이 등록되어 있는지 확인

### API 호출이 실패하는 경우

1. **서버 실행 여부 확인**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **CORS 에러 (프론트엔드에서 호출 시)**
   - `app/main.py`의 CORS 설정 확인
   - 프론트엔드 URL이 허용 목록에 있는지 확인

---

## 📊 테스트 시나리오

### 기본 플로우

1. **서버 시작**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **헬스 체크**
   ```bash
   curl http://localhost:8000/api/health
   ```

3. **종목 목록 확인**
   ```bash
   curl http://localhost:8000/api/etfs/ | python3 -m json.tool
   ```

4. **데이터 수집 (6개 종목)**
   ```bash
   # ETF 4개
   curl -X POST "http://localhost:8000/api/etfs/487240/collect?days=10"
   curl -X POST "http://localhost:8000/api/etfs/466920/collect?days=10"
   curl -X POST "http://localhost:8000/api/etfs/0020H0/collect?days=10"
   curl -X POST "http://localhost:8000/api/etfs/442320/collect?days=10"
   
   # 주식 2개
   curl -X POST "http://localhost:8000/api/etfs/042660/collect?days=10"
   curl -X POST "http://localhost:8000/api/etfs/034020/collect?days=10"
   ```

5. **데이터 조회**
   ```bash
   curl "http://localhost:8000/api/etfs/487240/prices" | python3 -m json.tool
   ```

---

## 🎯 성공 기준

Phase 1 기능이 정상적으로 작동하면 다음이 가능해야 합니다:

- ✅ 서버가 정상적으로 시작됨
- ✅ Swagger UI 접속 가능
- ✅ 6개 종목 목록 조회 가능
- ✅ Naver Finance에서 데이터 수집 가능 (6개 종목 모두)
- ✅ 수집된 데이터 조회 가능
- ✅ 에러 상황에서 적절한 에러 메시지 반환 (404, 500, 422)

---

## 📝 다음 단계

Phase 1 기능이 정상적으로 작동하는 것을 확인했다면:

1. **Phase 2: Data Collection Complete**
   - 투자자별 매매 동향 데이터 수집
   - 뉴스 스크래핑
   - 스케줄러 구현

2. **Phase 3: Frontend Basic**
   - React 앱 구축
   - Dashboard 구현
   - 백엔드 API 연동

---

**Last Updated**: 2025-11-07

