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
| `stock_catalog` | 종목 목록 카탈로그 (코스피, 코스닥, ETF — 검색·스크리닝용, 가격·수급 포함) |
| `collection_status` | 종목별 수집 상태 (마지막 수집일, 건수, 실패 횟수 등) |
| `intraday_prices` | 분봉 데이터 (당일 또는 지정일) |
| `alert_rules` | 알림 규칙 (목표가, 급등/급락, 매매 시그널) |
| `alert_history` | 알림 트리거 이력 |
| `etf_fundamentals` | ETF 펀더멘털 (NAV, AUM, 추적오차, 총보수) |
| `etf_rebalancing` | ETF 리밸런싱 이력 (편입/편출/조정) |
| `etf_distributions` | ETF 분배금 이력 (기준일, 지급일, 주당 금액, 배당수익률) |
| `etf_holdings` | ETF 구성종목 (비중, 주식수, 시가총액, 섹터) |
| `stock_fundamentals` | 주식 펀더멘털 (PER, PBR, ROE, EPS, 매출/이익, 부채비율 등) |
| `stock_distributions` | 주식 배당 이력 (기준일, 지급일, 주당 배당금, 배당수익률) |

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
         ├──────────────┬────────────────┬────────────────┬──────────────────┬───────────────────┬────────────────┐
         ▼              ▼                ▼                ▼                  ▼                   ▼                │
┌──────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────────┐ ┌─────────────────┐ ┌──────────────┐  │
│   prices     │ │ trading_flow │ │    news     │ │ collection_status│ │ intraday_prices │ │ alert_rules  │  │
│──────────────│ │──────────────│ │─────────────│ │──────────────────│ │─────────────────│ │──────────────│  │
│ id (PK)      │ │ id (PK)      │ │ id (PK)     │ │ ticker (PK, FK)  │ │ id (PK)         │ │ id (PK)      │  │
│ ticker (FK)  │ │ ticker (FK)  │ │ ticker (FK) │ │ last_price_date  │ │ ticker (FK)     │ │ ticker (FK)  │  │
│ date         │ │ date         │ │ date        │ │ last_trading_..  │ │ datetime        │ │ alert_type   │  │
│ open_price   │ │ individual_net│ │ title, url  │ │ *_count, *_at    │ │ price           │ │ direction    │  │
│ high_price   │ │ institutional │ │ source      │ │ consecutive_fail │ │ change_amount   │ │ target_price │  │
│ low_price    │ │ foreign_net   │ │ relevance_  │ └──────────────────┘ │ volume, bid,ask │ │ memo         │  │
│ close_price  │ └──────────────┘ │   score     │                      └─────────────────┘ │ is_active    │  │
│ volume       │                  └─────────────┘                                           │ last_trigger │  │
│ daily_change_│                                                                            └──────┬───────┘  │
│   pct        │                                                                                   │ 1:N      │
└──────────────┘     ┌───────────────────────┐                                             ┌───────▼───────┐  │
                     │  stock_catalog         │  (etfs와 독립, 스크리닝·검색용)               │ alert_history │  │
                     │───────────────────────│                                             │───────────────│  │
                     │ ticker (PK)            │                                             │ id (PK)       │  │
                     │ name, type, market     │                                             │ rule_id (FK)  │  │
                     │ sector, listed_date    │                                             │ ticker        │  │
                     │ is_active              │                                             │ alert_type    │  │
                     │ close_price, volume    │  ← 스크리닝 수집 컬럼                         │ message       │  │
                     │ daily_change_pct       │                                             │ triggered_at  │  │
                     │ weekly_return          │                                             └───────────────┘  │
                     │ foreign_net            │                                                                │
                     │ institutional_net      │                                                                │
                     │ catalog_updated_at     │                                                                │
                     └───────────────────────┘                                                                │
                                                                                                              │
         │ 1:N (ETF 펀더멘털·운용)                                                                             │
         ├────────────────┬────────────────┬────────────────┬────────────────┐                               │
         ▼                ▼                ▼                ▼                │                               │
┌──────────────────┐ ┌──────────────────┐ ┌─────────────────┐ ┌──────────────────┐                           │
│ etf_fundamentals │ │ etf_rebalancing  │ │etf_distributions│ │ etf_holdings     │                           │
│ ticker, date(PK) │ │ id, ticker, date │ │ id, ticker,     │ │ ticker, date,    │                           │
│ nav, aum,        │ │ action, stock_   │ │ record_date,   │ │ stock_code (PK),  │                           │
│ tracking_error,  │ │ weight_before/   │ │ amount_per_    │ │ weight, shares,  │                           │
│ expense_ratio    │ │ after, shares_   │ │ share, yield_  │ │ market_value,    │                           │
└──────────────────┘ └──────────────────┘ │   pct           │ │ sector           │                           │
                                         └─────────────────┘ └──────────────────┘                           │
         │ 1:N (주식 펀더멘털·배당)                                                                           │
         ├────────────────────────────────────────┐                                                          │
         ▼                                        ▼                                                          │
┌──────────────────────┐              ┌──────────────────────┐                                               │
│  stock_fundamentals  │              │  stock_distributions │                                               │
│  ticker, date (PK)   │              │  id (PK)             │                                               │
│  per, pbr, roe, roa  │              │  ticker, record_date │                                               │
│  eps, bps            │              │  UNIQUE(ticker,      │                                               │
│  revenue,            │              │    record_date)       │                                               │
│  operating_profit,   │              │  payment_date,       │                                               │
│  net_profit          │              │  ex_date             │                                               │
│  operating_margin,   │              │  amount_per_share,   │                                               │
│  net_margin          │              │  distribution_type,  │                                               │
│  debt_ratio,         │              │  yield_pct           │                                               │
│  current_ratio,      │              └──────────────────────┘                                               │
│  dividend_yield,     │                                                                                     │
│  payout_ratio        │                                                                                     │
└──────────────────────┘                                                                                     │
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
검색·스크리닝용. 코스피/코스닥/ETF 전체 수집 결과 + 가격·수급 데이터 저장.

```sql
CREATE TABLE stock_catalog (
    ticker TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    market TEXT,
    sector TEXT,
    listed_date DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    -- 스크리닝용 컬럼 (ALTER TABLE로 추가)
    close_price REAL,
    daily_change_pct REAL,
    volume INTEGER,
    weekly_return REAL,
    foreign_net INTEGER,
    institutional_net INTEGER,
    catalog_updated_at TIMESTAMP
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

### 8. `alert_rules` (알림 규칙)
종목별 목표가·급등급락·매매시그널 알림 규칙.

```sql
CREATE TABLE alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL,      -- buy, sell, price_change, trading_signal
    direction TEXT NOT NULL,       -- above, below, both
    target_price REAL NOT NULL,    -- 목표가(buy/sell) 또는 임계%(price_change)
    memo TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);
```

### 9. `alert_history` (알림 트리거 이력)
프론트엔드에서 감지한 알림 트리거 기록.

```sql
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
);
```

### 10. `etf_fundamentals` (ETF 펀더멘털: NAV, AUM)
ETF별 일자 단위 NAV, AUM, 추적오차, 총보수 등. AI 보고서·분석용.

```sql
CREATE TABLE etf_fundamentals (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    nav REAL,
    nav_change_pct REAL,
    aum REAL,
    tracking_error REAL,
    expense_ratio REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);
```

### 11. `etf_rebalancing` (ETF 리밸런싱 이력)
편입/편출/조정 일자, 종목코드·종목명, 비중·주식수 변화.

```sql
CREATE TABLE etf_rebalancing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    rebalance_date DATE NOT NULL,
    action TEXT NOT NULL,
    stock_code TEXT,
    stock_name TEXT,
    weight_before REAL,
    weight_after REAL,
    shares_change INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);
```

### 12. `etf_distributions` (ETF 분배금 이력)
분배금 기준일·지급일·주당 금액·유형·배당수익률.

```sql
CREATE TABLE etf_distributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    record_date DATE NOT NULL,
    payment_date DATE,
    ex_date DATE,
    amount_per_share REAL NOT NULL,
    distribution_type TEXT,
    yield_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker),
    UNIQUE(ticker, record_date)
);
```

### 13. `etf_holdings` (ETF 구성종목)
ETF별 일자별 보유 종목·비중·주식수·시가총액·섹터. 상위 종목 스냅샷용.

```sql
CREATE TABLE etf_holdings (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    weight REAL,
    shares INTEGER,
    market_value REAL,
    sector TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date, stock_code),
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);
```

### 14. `stock_fundamentals` (주식 펀더멘털)
주식 종목의 재무지표. 네이버 금융 기업실적분석 테이블 기준, 수집일 단위 스냅샷.
단위: 매출/영업이익/순이익 → 억원, 비율(%) → 소수점 2자리.

```sql
CREATE TABLE stock_fundamentals (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    per REAL,               -- 주가수익비율
    pbr REAL,               -- 주가순자산비율
    roe REAL,               -- 자기자본이익률 (%)
    roa REAL,               -- 총자산이익률 (%)
    eps REAL,               -- 주당순이익 (원)
    bps REAL,               -- 주당순자산 (원)
    revenue REAL,           -- 매출액 (억원)
    operating_profit REAL,  -- 영업이익 (억원)
    net_profit REAL,        -- 당기순이익 (억원)
    operating_margin REAL,  -- 영업이익률 (%)
    net_margin REAL,        -- 순이익률 (%)
    debt_ratio REAL,        -- 부채비율 (%)
    current_ratio REAL,     -- 당좌비율 (%)
    dividend_yield REAL,    -- 시가배당률 (%)
    payout_ratio REAL,      -- 배당성향 (%)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);
```

### 15. `stock_distributions` (주식 배당 이력)
주식 배당금 기준일·지급일·주당 배당금·유형·배당수익률.

```sql
CREATE TABLE stock_distributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    record_date DATE NOT NULL,
    payment_date DATE,
    ex_date DATE,
    amount_per_share REAL,
    distribution_type TEXT,  -- 현금배당, 주식배당 등
    yield_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker),
    UNIQUE(ticker, record_date)
);
```

---

## 인덱스

```sql
CREATE INDEX idx_prices_ticker_date ON prices(ticker, date DESC);
CREATE INDEX idx_trading_flow_ticker_date ON trading_flow(ticker, date DESC);
CREATE INDEX idx_news_ticker_date ON news(ticker, date DESC);
CREATE UNIQUE INDEX idx_news_ticker_url ON news(ticker, url);
CREATE INDEX idx_stock_catalog_name ON stock_catalog(name);
CREATE INDEX idx_stock_catalog_type ON stock_catalog(type);
CREATE INDEX idx_stock_catalog_active ON stock_catalog(is_active);
CREATE INDEX idx_stock_catalog_screening ON stock_catalog(type, is_active, weekly_return);
CREATE INDEX idx_stock_catalog_sector ON stock_catalog(sector, is_active);
CREATE INDEX idx_stock_catalog_catalog_updated ON stock_catalog(catalog_updated_at);
CREATE INDEX idx_collection_status_last_dates ON collection_status(last_price_date, last_trading_flow_date);
CREATE INDEX idx_intraday_prices_ticker_datetime ON intraday_prices(ticker, datetime DESC);
CREATE INDEX idx_alert_rules_ticker ON alert_rules(ticker, is_active);
CREATE INDEX idx_alert_history_ticker ON alert_history(ticker, triggered_at DESC);
CREATE INDEX idx_etf_fundamentals_ticker_date ON etf_fundamentals(ticker, date DESC);
CREATE INDEX idx_etf_rebalancing_ticker_date ON etf_rebalancing(ticker, rebalance_date DESC);
CREATE INDEX idx_etf_distributions_ticker_date ON etf_distributions(ticker, record_date DESC);
CREATE INDEX idx_etf_holdings_ticker_date ON etf_holdings(ticker, date DESC);
CREATE INDEX idx_etf_holdings_weight ON etf_holdings(ticker, date, weight DESC);
CREATE INDEX idx_stock_fundamentals_ticker_date ON stock_fundamentals(ticker, date DESC);
CREATE INDEX idx_stock_distributions_ticker_date ON stock_distributions(ticker, record_date DESC);
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
`DELETE /api/data/reset` 호출 시 다음 테이블만 비움: `prices`, `news`, `trading_flow`, `collection_status`, `intraday_prices`. `etfs`, `stock_catalog`, `alert_rules`, `alert_history`, `etf_fundamentals`, `etf_rebalancing`, `etf_distributions`, `etf_holdings`, `stock_fundamentals`, `stock_distributions`는 유지.

---

## 참고
- PostgreSQL 사용 시 `init_db()`에서 SERIAL, ON CONFLICT 등으로 스키마가 동일하게 생성됨.
- 초기 종목 데이터는 `Config.get_stock_config()`(stocks.json)에서 읽어 `etfs`에 INSERT.
