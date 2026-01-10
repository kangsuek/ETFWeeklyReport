# 데이터베이스 스키마

## 개요
- **개발 환경**: SQLite
- **프로덕션**: PostgreSQL (권장)
- **ORM**: 없음 (직접 SQL 사용)

## 구현 상태

| 테이블 | 상태 | Phase | 설명 |
|--------|------|-------|------|
| `etfs` | ✅ | Phase 1 | 종목 기본 정보 (6개 종목) |
| `prices` | ✅ | Phase 1 | 가격 데이터 |
| `trading_flow` | ✅ | Phase 2 | 투자자별 매매 동향 |
| `news` | ✅ | Phase 2 | 뉴스 데이터 |
| `stock_catalog` | ✅ | Phase 2.5 | 종목 목록 카탈로그 (코스피, 코스닥, ETF 전체) |

## ERD

```
┌──────────────┐
│     etfs     │
│──────────────│
│ ticker (PK)  │
│ name         │
│ type         │
│ theme        │
└──────┬───────┘
       │
       │ 1:N
       │
   ┌───┴─────────────┬─────────────────┬──────────────────┐
   │                 │                 │                  │
   ▼                 ▼                 ▼                  ▼
┌──────────┐  ┌──────────────┐  ┌────────────┐
│  prices  │  │ trading_flow │  │    news    │
│──────────│  │──────────────│  │────────────│
│ id (PK)  │  │ id (PK)      │  │ id (PK)    │
│ ticker   │  │ ticker (FK)  │  │ ticker (FK)│
│ date     │  │ date         │  │ date       │
│ close    │  │ individual │  │ title       │
│ volume   │  │ institutional│  │ url        │
└──────────┘  │ foreign      │  │ relevance │
              └──────────────┘  └────────────┘
```

## 테이블 정의

### 1. `etfs` (종목 기본 정보)
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

### 2. `prices` (가격 데이터)
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

### 3. `trading_flow` (투자자별 매매 동향)
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

### 4. `news` (뉴스 데이터)
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

### 5. `stock_catalog` (종목 목록 카탈로그)
```sql
CREATE TABLE stock_catalog (
    ticker TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    market TEXT,
    sector TEXT,
    listed_date DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);
```

**용도**: 전체 종목 목록을 미리 수집하여 저장. 자동완성 검색에 사용.

**데이터 소스**: 네이버 금융 (코스피, 코스닥, ETF)

**업데이트**: 수동 트리거 또는 스케줄러를 통한 정기 업데이트

## 인덱스
```sql
CREATE INDEX idx_prices_ticker_date ON prices(ticker, date);
CREATE INDEX idx_trading_flow_ticker_date ON trading_flow(ticker, date);
CREATE INDEX idx_news_ticker_date ON news(ticker, date);
CREATE INDEX idx_stock_catalog_name ON stock_catalog(name);
CREATE INDEX idx_stock_catalog_type ON stock_catalog(type);
CREATE INDEX idx_stock_catalog_active ON stock_catalog(is_active);
```

## 쿼리 예제

### 1. 전체 종목 목록 조회
```sql
SELECT * FROM etfs;
```

### 2. 특정 종목 정보 조회
```sql
SELECT * FROM etfs WHERE ticker = '487240';
```

### 3. 최근 7일 가격 데이터 조회
```sql
SELECT date, close_price, volume, daily_change_pct
FROM prices
WHERE ticker = '487240'
  AND date >= DATE('now', '-7 days')
ORDER BY date DESC;
```

### 4. 특정 기간 가격 데이터 조회
```sql
SELECT date, close_price, volume, daily_change_pct
FROM prices
WHERE ticker = '487240'
  AND date BETWEEN '2025-11-01' AND '2025-11-07'
ORDER BY date DESC;
```

### 5. 종목별 최신 가격 조회
```sql
SELECT e.ticker, e.name, e.type, p.close_price, p.daily_change_pct, p.date
FROM etfs e
LEFT JOIN prices p ON e.ticker = p.ticker
WHERE p.date = (
    SELECT MAX(date) FROM prices WHERE ticker = e.ticker
)
ORDER BY e.ticker;
```

### 6. 투자자별 매매 동향 조회
```sql
SELECT date, individual_net, institutional_net, foreign_net
FROM trading_flow
WHERE ticker = '487240'
  AND date >= DATE('now', '-7 days')
ORDER BY date DESC;
```

### 7. 특정 기간 투자자별 매매 합계
```sql
SELECT 
    SUM(individual_net) as total_individual,
    SUM(institutional_net) as total_institutional,
    SUM(foreign_net) as total_foreign
FROM trading_flow
WHERE ticker = '487240'
  AND date BETWEEN '2025-11-01' AND '2025-11-07';
```

### 8. 종목별 최신 뉴스 조회
```sql
SELECT ticker, title, date, url, source, relevance_score
FROM news
WHERE ticker = '487240'
ORDER BY date DESC, relevance_score DESC
LIMIT 10;
```

### 9. 종목별 데이터 통계
```sql
SELECT 
    ticker,
    COUNT(*) as price_count,
    MIN(date) as first_date,
    MAX(date) as last_date,
    MIN(close_price) as min_price,
    MAX(close_price) as max_price,
    AVG(close_price) as avg_price
FROM prices
GROUP BY ticker;
```

### 10. 수집된 데이터 확인
```sql
-- 종목별 가격 데이터 수
SELECT ticker, COUNT(*) as count 
FROM prices 
GROUP BY ticker;

-- 종목별 매매 동향 데이터 수
SELECT ticker, COUNT(*) as count 
FROM trading_flow 
GROUP BY ticker;

-- 종목별 뉴스 데이터 수
SELECT ticker, COUNT(*) as count 
FROM news 
GROUP BY ticker;
```

### 11. 전체 종목 최근 가격 및 등락률
```sql
SELECT 
    e.ticker,
    e.name,
    e.type,
    p.close_price,
    p.daily_change_pct,
    p.volume,
    p.date
FROM etfs e
INNER JOIN prices p ON e.ticker = p.ticker
WHERE p.date = (
    SELECT MAX(date) FROM prices WHERE ticker = e.ticker
)
ORDER BY p.daily_change_pct DESC;
```

### 12. Python으로 쿼리 실행 예제
```python
import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect('backend/data/etf_report.db')
cursor = conn.cursor()

# 전체 종목 조회
cursor.execute("SELECT * FROM etfs")
etfs = cursor.fetchall()
for etf in etfs:
    print(f"{etf[0]}: {etf[1]}")

# 특정 종목의 최근 가격 조회
cursor.execute("""
    SELECT date, close_price, daily_change_pct
    FROM prices
    WHERE ticker = '487240'
    ORDER BY date DESC
    LIMIT 10
""")
prices = cursor.fetchall()
for price in prices:
    print(f"{price[0]}: {price[1]:,.0f}원 ({price[2]:+.2f}%)")

conn.close()
```
