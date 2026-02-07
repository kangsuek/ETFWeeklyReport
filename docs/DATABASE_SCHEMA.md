# 데이터베이스 스키마

## 개요
- **개발 환경**: SQLite (`backend/data/etf_data.db` 또는 `DATABASE_URL` 지정 경로)
- **프로덕션**: PostgreSQL 권장
- **ORM**: 없음 (직접 SQL 사용)
- **종목 마스터**: `backend/config/stocks.json` + DB `etfs` 테이블 동기화

## 테이블 목록

| 테이블 | 설명 |
|--------|------|
| `etfs` | 종목 기본 정보 (설정된 ETF·주식) |
| `prices` | 일봉 가격 데이터 (시가/고가/저가/종가, 거래량, 등락률) |
| `trading_flow` | 투자자별 매매 동향 (개인/기관/외국인 순매수) |
| `news` | 뉴스 데이터 |
| `stock_catalog` | 종목 목록 카탈로그 (코스피, 코스닥, ETF — 자동완성용) |
| `collection_status` | 종목별 수집 상태 (마지막 수집일, 건수, 실패 횟수 등) |
| `intraday_prices` | 분봉 데이터 (당일 또는 지정일) |

---

## ERD

```
┌──────────────────┐
│      etfs        │
│──────────────────│
│ ticker (PK)      │
│ name, type, theme│
│ purchase_date    │
│ purchase_price   │
│ quantity         │
│ search_keyword   │
│ relevance_keywords│
└────────┬─────────┘
         │ 1:N
         ├──────────────┬─────────────────┬────────────────┬─────────────────────┬──────────────────────┐
         ▼              ▼                   ▼                ▼                     ▼                      ▼
┌──────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────────┐ ┌─────────────────────┐
│   prices     │ │ trading_flow │ │    news     │ │ collection_status│ │  intraday_prices     │
│──────────────│ │──────────────│ │─────────────│ │──────────────────│ │─────────────────────│
│ id (PK)      │ │ id (PK)      │ │ id (PK)     │ │ ticker (PK, FK)  │ │ id (PK)             │
│ ticker (FK)  │ │ ticker (FK)  │ │ ticker (FK) │ │ last_price_date  │ │ ticker (FK)         │
│ date         │ │ date         │ │ date        │ │ last_trading_..  │ │ datetime            │
│ open_price   │ │ individual_net│ │ title, url  │ │ *_count, *_at    │ │ price, change_amount│
│ high_price   │ │ institutional │ │ source      │ │ consecutive_fail │ │ volume, bid, ask     │
│ low_price    │ │ foreign_net   │ │ relevance_  │ └──────────────────┘ └─────────────────────┘
│ close_price  │ └──────────────┘ │   score     │
│ volume       │                  └─────────────┘
│ daily_change_│
│   pct        │     ┌──────────────────┐
└──────────────┘     │  stock_catalog    │  (etfs와 독립, 검색용)
                     │──────────────────│
                     │ ticker (PK)       │
                     │ name, type, market│
                     │ sector, listed_  │
                     │   date, is_active │
                     └──────────────────┘
```

---

## 테이블 정의

### 1. `etfs` (종목 기본 정보)
종목 마스터. `stocks.json`과 동기화되며, 포트폴리오용 매입 정보 포함.

```sql
CREATE TABLE etfs (
    ticker TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    theme TEXT,
    purchase_date DATE,
    purchase_price REAL,
    quantity INTEGER,
    search_keyword TEXT,
    relevance_keywords TEXT   -- JSON 배열 문자열
);
```

### 2. `prices` (일봉 가격 데이터)
```sql
CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
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
    ticker TEXT NOT NULL,
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
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    title TEXT,
    url TEXT,
    source TEXT,
    relevance_score REAL,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);
```

### 5. `stock_catalog` (종목 목록 카탈로그)
자동완성·검색용. 코스피/코스닥/ETF 전체 수집 결과 저장.

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

### 6. `collection_status` (수집 상태)
종목별 마지막 수집일·건수·실패 횟수 등. 스마트 수집(중복 방지)에 사용.

```sql
CREATE TABLE collection_status (
    ticker TEXT PRIMARY KEY,
    last_price_date DATE,
    last_trading_flow_date DATE,
    last_news_collected_at TIMESTAMP,
    price_records_count INTEGER DEFAULT 0,
    trading_flow_records_count INTEGER DEFAULT 0,
    news_records_count INTEGER DEFAULT 0,
    last_collection_attempt TIMESTAMP,
    last_successful_collection TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);
```

### 7. `intraday_prices` (분봉 데이터)
분 단위 체결 데이터. 당일 또는 마지막 거래일 기준 저장.

```sql
CREATE TABLE intraday_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    datetime TIMESTAMP NOT NULL,
    price REAL NOT NULL,
    change_amount REAL,
    volume INTEGER,
    bid_volume INTEGER,
    ask_volume INTEGER,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker),
    UNIQUE(ticker, datetime)
);
```

---

## 인덱스

```sql
CREATE INDEX idx_prices_ticker_date ON prices(ticker, date DESC);
CREATE INDEX idx_trading_flow_ticker_date ON trading_flow(ticker, date DESC);
CREATE INDEX idx_news_ticker_date ON news(ticker, date DESC);
CREATE INDEX idx_stock_catalog_name ON stock_catalog(name);
CREATE INDEX idx_stock_catalog_type ON stock_catalog(type);
CREATE INDEX idx_stock_catalog_active ON stock_catalog(is_active);
CREATE INDEX idx_collection_status_last_dates ON collection_status(last_price_date, last_trading_flow_date);
CREATE INDEX idx_intraday_prices_ticker_datetime ON intraday_prices(ticker, datetime DESC);
```

---

## 쿼리 예제

### 전체 종목 목록
```sql
SELECT * FROM etfs;
```

### 특정 종목 최근 7일 가격
```sql
SELECT date, open_price, high_price, low_price, close_price, volume, daily_change_pct
FROM prices
WHERE ticker = '487240' AND date >= DATE('now', '-7 days')
ORDER BY date DESC;
```

### 특정 종목 분봉 (당일)
```sql
SELECT datetime, price, change_amount, volume
FROM intraday_prices
WHERE ticker = '487240' AND DATE(datetime) = DATE('now')
ORDER BY datetime ASC;
```

### 종목별 수집 상태
```sql
SELECT ticker, last_price_date, last_trading_flow_date, price_records_count
FROM collection_status;
```

### DB 초기화 시 삭제 대상
`DELETE /api/data/reset` 호출 시 다음 테이블만 비움: `prices`, `news`, `trading_flow`, `collection_status`, `intraday_prices`. `etfs`, `stock_catalog`는 유지.

---

## 참고
- PostgreSQL 사용 시 `init_db()`에서 SERIAL, ON CONFLICT 등으로 스키마가 동일하게 생성됨.
- 초기 종목 데이터는 `Config.get_stock_config()`(stocks.json)에서 읽어 `etfs`에 INSERT.
