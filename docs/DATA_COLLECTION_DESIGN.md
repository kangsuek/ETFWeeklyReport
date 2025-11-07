# 데이터 수집 기능 설계

## 개요

6개 종목(ETF 4개 + 주식 2개)의 가격 데이터를 Naver Finance에서 스크래핑하여 수집하는 기능 설계

---

## 대상 종목

| 구분 | 종목코드 | 종목명 |
|-----|---------|-------|
| ETF | 487240 | 삼성 KODEX AI전력핵심설비 ETF |
| ETF | 466920 | 신한 SOL 조선TOP3플러스 ETF |
| ETF | 0020H0 | KoAct 글로벌양자컴퓨팅액티브 ETF |
| ETF | 442320 | KB RISE 글로벌원자력 iSelect ETF |
| 주식 | 042660 | 한화오션 |
| 주식 | 034020 | 두산에너빌리티 |

---

## 데이터 소스

### Naver Finance 일별 시세 페이지

**URL**: `https://finance.naver.com/item/sise_day.naver?code={종목코드}&page={페이지}`

**특징**:
- 페이지당 10개 데이터 행
- 최신 데이터부터 역순 정렬
- HTML 테이블 형식 (`<table class="type2">`)
- 6개 종목 모두 수집 가능 확인 ✅

---

## 수집할 데이터 필드

### HTML 구조 분석

```html
<table class="type2">
  <tr>
    <td class="date">2025.11.07</td>
    <td class="num">25,765</td>      <!-- 종가 -->
    <td><img>상승205</td>            <!-- 전일대비 -->
    <td class="num">26,000</td>      <!-- 시가 -->
    <td class="num">26,500</td>      <!-- 고가 -->
    <td class="num">25,500</td>      <!-- 저가 -->
    <td class="num">8,225,769</td>   <!-- 거래량 -->
  </tr>
</table>
```

### 수집 필드

| 필드 | 타입 | 설명 | 예시 |
|-----|------|------|------|
| `date` | DATE | 거래일 | "2025-11-07" |
| `close_price` | FLOAT | 종가 | 25765.0 |
| `open_price` | FLOAT | 시가 | 26000.0 |
| `high_price` | FLOAT | 고가 | 26500.0 |
| `low_price` | FLOAT | 저가 | 25500.0 |
| `volume` | INTEGER | 거래량 | 8225769 |
| `daily_change_pct` | FLOAT | 전일대비 등락률 (%) | 0.8 |

**주의사항**:
- 금액 필드에서 콤마(`,`) 제거 필요
- 날짜 형식: `YYYY.MM.DD` → `YYYY-MM-DD` 변환
- 등락률: "상승205" → +0.8%, "하락205" → -0.8% 계산

---

## 데이터 수집 로직

### 함수 설계: `fetch_price_data_from_naver()`

```python
def fetch_price_data_from_naver(
    ticker: str,
    num_days: int = 10
) -> List[PriceData]:
    """
    Naver Finance에서 가격 데이터 스크래핑
    
    Args:
        ticker: 종목 코드 (예: "487240")
        num_days: 수집할 일수 (기본 10일)
    
    Returns:
        PriceData 리스트 (최신순)
    
    Raises:
        requests.exceptions.RequestException: 네트워크 오류
        ValueError: HTML 파싱 실패
    """
```

### 처리 흐름

```
1. HTTP 요청
   ↓
2. HTML 파싱 (BeautifulSoup4)
   ↓
3. 테이블 추출 (<table class="type2">)
   ↓
4. 데이터 행 파싱 (각 <tr>)
   ↓
5. 데이터 정제
   - 콤마 제거
   - 날짜 포맷 변환
   - 타입 변환 (str → float/int)
   ↓
6. PriceData 모델 생성
   ↓
7. 리스트 반환
```

---

## 날짜 범위 처리

### 기본 설정
- **기본 수집 일수**: 10일 (약 2주)
- **최대 수집 가능**: 페이지 단위로 제한 없음
- **페이지네이션**: `page` 파라미터로 제어

### 날짜 범위 옵션

```python
# 옵션 1: 일수 기반 (권장)
fetch_price_data_from_naver(ticker="487240", num_days=10)

# 옵션 2: 날짜 범위 지정
fetch_price_data_by_date_range(
    ticker="487240",
    start_date=date(2025, 10, 1),
    end_date=date(2025, 11, 7)
)
```

### 페이지 계산 로직

```python
# 10일 데이터 = 1페이지
# 30일 데이터 = 3페이지
# 100일 데이터 = 10페이지

pages_needed = (num_days + 9) // 10  # 올림
```

---

## 에러 처리

### 예상 에러 케이스

| 에러 | 원인 | 대응 |
|------|------|------|
| `requests.exceptions.Timeout` | 네트워크 타임아웃 | 재시도 (3회, exponential backoff) |
| `requests.exceptions.HTTPError` | HTTP 오류 (404, 500 등) | 로그 기록 + 빈 리스트 반환 |
| `AttributeError` | HTML 구조 변경 | 로그 기록 + 예외 발생 |
| 빈 데이터 | 신규 상장 종목 등 | 경고 로그 + 빈 리스트 반환 |

### 재시도 로직

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def _fetch_with_retry(url: str) -> requests.Response:
    """재시도 가능한 HTTP 요청"""
    pass
```

---

## Rate Limiting

### Naver Finance 서버 부하 방지

```python
import time

class RateLimiter:
    def __init__(self, calls_per_minute: int = 10):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = 0.0
    
    def wait_if_needed(self):
        """필요 시 대기"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
```

**설정**:
- **최대 요청 속도**: 10 requests/minute (6초당 1회)
- **동시 수집 시**: 6개 종목 × 1 페이지 = 약 36초 소요

---

## 데이터 검증

### 검증 규칙

```python
def validate_price_data(data: dict) -> bool:
    """데이터 유효성 검증"""
    
    # 1. 필수 필드 존재 확인
    required_fields = ['date', 'close_price', 'volume']
    if not all(field in data for field in required_fields):
        return False
    
    # 2. 가격 양수 확인
    if data['close_price'] <= 0:
        return False
    
    # 3. 거래량 음수 아님 확인
    if data['volume'] < 0:
        return False
    
    # 4. 날짜 형식 확인
    try:
        datetime.strptime(data['date'], '%Y-%m-%d')
    except ValueError:
        return False
    
    return True
```

---

## 데이터베이스 저장

### UPSERT 로직

```python
def save_price_data(ticker: str, price_data: List[PriceData]):
    """
    가격 데이터를 DB에 저장 (중복 시 업데이트)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for data in price_data:
        cursor.execute("""
            INSERT INTO prices (ticker, date, close_price, volume, daily_change_pct)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                close_price = excluded.close_price,
                volume = excluded.volume,
                daily_change_pct = excluded.daily_change_pct
        """, (ticker, data.date, data.close_price, data.volume, data.daily_change_pct))
    
    conn.commit()
    conn.close()
```

**특징**:
- `UNIQUE(ticker, date)` 제약으로 중복 방지
- 중복 시 자동 업데이트 (최신 데이터 반영)

---

## 테스트 전략

### 유닛 테스트

```python
# tests/test_data_collector.py

def test_fetch_price_data_success():
    """정상 데이터 수집 테스트"""
    collector = ETFDataCollector()
    data = collector.fetch_price_data_from_naver("487240", num_days=10)
    
    assert len(data) > 0
    assert data[0].ticker == "487240"
    assert data[0].close_price > 0

def test_fetch_price_data_invalid_ticker():
    """잘못된 종목코드 테스트"""
    collector = ETFDataCollector()
    data = collector.fetch_price_data_from_naver("INVALID", num_days=10)
    
    assert len(data) == 0  # 빈 리스트 반환
```

### 통합 테스트

```python
def test_full_collection_workflow():
    """전체 수집 워크플로우 테스트"""
    ticker = "487240"
    
    # 1. 수집
    data = fetch_price_data_from_naver(ticker, num_days=10)
    
    # 2. 저장
    save_price_data(ticker, data)
    
    # 3. 조회
    saved_data = get_price_data(ticker, start_date, end_date)
    
    assert len(saved_data) == len(data)
```

---

## 성능 목표

| 항목 | 목표 |
|-----|------|
| 1개 종목 수집 시간 | < 2초 |
| 6개 종목 수집 시간 | < 40초 (Rate Limiting 포함) |
| DB 저장 시간 | < 1초 |
| 메모리 사용량 | < 50MB |

---

## 다음 단계 (Step 2)

1. `fetch_price_data_from_naver()` 함수 구현
2. HTML 파싱 로직 구현
3. 데이터 정제 및 변환
4. 유닛 테스트 작성
5. 1개 종목 테스트 (487240)

---

**작성일**: 2025-11-06  
**작성자**: AI Assistant  
**상태**: 설계 완료 ✅

