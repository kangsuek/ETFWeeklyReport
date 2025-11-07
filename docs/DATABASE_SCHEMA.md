# 데이터베이스 스키마

## 개요

- **개발 환경**: SQLite
- **프로덕션**: PostgreSQL (권장)
- **ORM**: 없음 (직접 SQL 사용)

## 구현 상태

| 테이블 | 상태 | Phase | 설명 |
|--------|------|-------|------|
| `etfs` | ✅ 구현 완료 | Phase 1 | 종목 기본 정보 (6개 종목) |
| `prices` | ✅ 구현 완료 | Phase 1 | 가격 데이터 (시가/고가/저가/종가/거래량) |
| `trading_flow` | ⏳ 예정 | Phase 2 | 투자자별 매매 동향 (개인/기관/외국인) |
| `news` | ⏳ 예정 | Phase 2 | 뉴스 데이터 (제목/URL/관련도 점수) |

---

## ERD (Entity Relationship Diagram)

```
┌──────────────┐
│     etfs     │
│──────────────│
│ ticker (PK)  │
│ name         │
│ theme        │
│ launch_date  │
│ expense_ratio│
└──────┬───────┘
       │
       │ 1:N
       │
   ┌───┴─────────────┬─────────────────┬──────────────────┐
   │                 │                 │                  │
   ▼                 ▼                 ▼                  ▼
┌──────────┐  ┌──────────────┐  ┌────────────┐    ┌─────────┐
│  prices  │  │ trading_flow │  │    news    │    │ metrics │
│──────────│  │──────────────│  │────────────│    │─────────│
│ id (PK)  │  │ id (PK)      │  │ id (PK)    │    │ (future)│
│ ticker   │  │ ticker (FK)  │  │ ticker (FK)│    │         │
│ date     │  │ date         │  │ date       │    └─────────┘
│ close    │  │ individual   │  │ title      │
│ volume   │  │ institutional│  │ url        │
│ change%  │  │ foreign      │  │ source     │
└──────────┘  └──────────────┘  │ relevance  │
                                └────────────┘
```

---

## 테이블 정의

### 1. `etfs` (종목 기본 정보)

종목(ETF 및 주식)의 기본 정보를 저장하는 마스터 테이블

```sql
CREATE TABLE etfs (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(10) NOT NULL,
    theme VARCHAR(50),
    launch_date DATE,
    expense_ratio REAL
);
```

**컬럼 설명:**

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| ticker | VARCHAR(10) | 종목 코드 (PK) | "487240" |
| name | VARCHAR(100) | 종목 명칭 | "삼성 KODEX AI전력핵심설비 ETF" |
| type | VARCHAR(10) | 종목 유형 | "ETF" 또는 "STOCK" |
| theme | VARCHAR(50) | 투자 테마 | "AI/전력" |
| launch_date | DATE | 상장일 | "2024-03-15" |
| expense_ratio | REAL | 보수율 (소수, ETF만) | 0.0045 (0.45%) |

**초기 데이터:**

```sql
INSERT INTO etfs (ticker, name, type, theme, launch_date, expense_ratio) VALUES
-- ETF 4개
('487240', '삼성 KODEX AI전력핵심설비 ETF', 'ETF', 'AI/전력', '2024-03-15', 0.0045),
('466920', '신한 SOL 조선TOP3플러스 ETF', 'ETF', '조선', '2023-08-10', 0.0050),
('0020H0', 'KoAct 글로벌양자컴퓨팅액티브 ETF', 'ETF', '양자컴퓨팅', '2024-05-20', 0.0070),
('442320', 'KB RISE 글로벌원자력 iSelect ETF', 'ETF', '원자력', '2024-01-25', 0.0055),
-- 주식 2개
('042660', '한화오션', 'STOCK', '조선/방산', NULL, NULL),
('034020', '두산에너빌리티', 'STOCK', '에너지/전력', NULL, NULL);
```

---

### 2. `prices` (가격 데이터)

일별 가격 및 거래량 데이터

```sql
CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    close_price REAL,
    volume INTEGER,
    daily_change_pct REAL,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker),
    UNIQUE(ticker, date)
);
```

**컬럼 설명:**

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER | 자동 증가 PK | 1, 2, 3... |
| ticker | VARCHAR(10) | 종목 코드 (FK) | "487240" |
| date | DATE | 거래일 | "2025-11-01" |
| close_price | REAL | 종가 | 12500.0 |
| volume | INTEGER | 거래량 | 1250000 |
| daily_change_pct | REAL | 전일 대비 등락률 (%) | 2.5 |

**인덱스:**

```sql
CREATE INDEX idx_prices_ticker_date ON prices(ticker, date);
CREATE INDEX idx_prices_date ON prices(date);
```

**제약 조건:**

- `UNIQUE(ticker, date)`: 동일 티커의 동일 날짜 데이터 중복 방지

---

### 3. `trading_flow` (투자자별 매매 동향) ⏳ Phase 2

투자자 유형별 순매수/순매도 데이터  
**구현 예정**: Phase 2 - Step 3

```sql
CREATE TABLE trading_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    individual_net INTEGER,
    institutional_net INTEGER,
    foreign_net INTEGER,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker),
    UNIQUE(ticker, date)
);
```

**컬럼 설명:**

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER | 자동 증가 PK | 1, 2, 3... |
| ticker | VARCHAR(10) | 종목 코드 (FK) | "487240" |
| date | DATE | 거래일 | "2025-11-01" |
| individual_net | INTEGER | 개인 순매수 (주식 수) | -15000 (순매도) |
| institutional_net | INTEGER | 기관 순매수 (주식 수) | 8000 (순매수) |
| foreign_net | INTEGER | 외국인 순매수 (주식 수) | 7000 (순매수) |

**인덱스:**

```sql
CREATE INDEX idx_flow_ticker_date ON trading_flow(ticker, date);
```

**데이터 해석:**

- 양수(+): 순매수 (해당 투자자가 더 많이 매수)
- 음수(-): 순매도 (해당 투자자가 더 많이 매도)

---

### 4. `news` (뉴스 데이터) ⏳ Phase 2

종목 테마 관련 뉴스 기사  
**구현 예정**: Phase 2 - Step 4

```sql
CREATE TABLE news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    title TEXT,
    url TEXT,
    source VARCHAR(50),
    relevance_score REAL,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);
```

**컬럼 설명:**

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| id | INTEGER | 자동 증가 PK | 1, 2, 3... |
| ticker | VARCHAR(10) | 관련 종목 코드 (FK) | "487240" |
| date | DATE | 뉴스 발행일 | "2025-11-01" |
| title | TEXT | 뉴스 제목 | "AI 데이터센터 투자 급증" |
| url | TEXT | 뉴스 링크 | "https://news.naver.com/..." |
| source | VARCHAR(50) | 뉴스 출처 | "매일경제" |
| relevance_score | REAL | 관련도 점수 (0~1) | 0.85 |

**인덱스:**

```sql
CREATE INDEX idx_news_ticker_date ON news(ticker, date);
CREATE INDEX idx_news_date ON news(date DESC);
```

---

## 쿼리 예시

### 최근 7일 가격 데이터 조회

```sql
SELECT date, close_price, volume, daily_change_pct
FROM prices
WHERE ticker = '487240'
  AND date >= DATE('now', '-7 days')
ORDER BY date DESC;
```

### 특정 기간 투자자별 매매 합계

```sql
SELECT 
    SUM(individual_net) as total_individual,
    SUM(institutional_net) as total_institutional,
    SUM(foreign_net) as total_foreign
FROM trading_flow
WHERE ticker = '487240'
  AND date BETWEEN '2025-10-01' AND '2025-11-01';
```

### 종목별 최신 뉴스 5건

```sql
SELECT ticker, title, date, url, source
FROM news
WHERE ticker = '487240'
ORDER BY date DESC
LIMIT 5;
```

### 전체 종목 최근 가격

```sql
SELECT e.ticker, e.name, e.type, p.close_price, p.daily_change_pct
FROM etfs e
LEFT JOIN prices p ON e.ticker = p.ticker
WHERE p.date = (
    SELECT MAX(date) FROM prices WHERE ticker = e.ticker
);
```

---

## 데이터 정합성 규칙

1. **중복 방지**: `UNIQUE(ticker, date)` 제약으로 동일 날짜 데이터 중복 방지
2. **외래 키**: 모든 데이터는 `etfs` 테이블에 존재하는 티커만 참조 가능
3. **날짜 형식**: ISO 8601 형식 (YYYY-MM-DD)
4. **NULL 처리**: 
   - 필수 필드: `ticker`, `date`
   - 선택 필드: 데이터 수집 실패 시 NULL 허용

---

## 마이그레이션 (SQLite → PostgreSQL)

### PostgreSQL 스키마 변환

```sql
-- SQLite의 AUTOINCREMENT → PostgreSQL의 SERIAL
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    ...
);

-- REAL → NUMERIC(10,2) for 정확한 금액 표현
close_price NUMERIC(10,2),
```

---

## 백업 및 유지보수

### SQLite 백업

```bash
# 백업
sqlite3 etf_data.db ".backup etf_data_backup.db"

# 덤프
sqlite3 etf_data.db .dump > etf_data_dump.sql
```

### 테이블 크기 예상

- **prices**: 6개 종목 × 250 거래일 × 5년 = 약 7,500 rows
- **trading_flow**: 동일
- **news**: 6개 종목 × 5 뉴스/일 × 365일 = 약 10,950 rows/year

---

**Last Updated**: 2025-11-07

