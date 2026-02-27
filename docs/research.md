# ETFWeeklyReport 프로젝트 심층 연구 보고서

이 보고서는 ETFWeeklyReport 프로젝트의 코드베이스를 심층 분석한 결과를 바탕으로 작성되었습니다. 본 프로젝트는 한국 ETF 시장의 데이터를 수집, 분석, 시각화하고 AI 에이전트와 연동할 수 있는 종합 금융 플랫폼입니다.

---

## 1. 시스템 아키텍처 및 데이터 흐름

### 1.1 전체 구조
프로젝트는 현대적인 4계층 아키텍처로 구성되어 있습니다.
- **Frontend**: React (Vite) 기반의 SPA (Single Page Application)
- **Backend**: FastAPI 기반의 비동기 REST API 서버
- **Database**: SQLite (개발/기본) 및 PostgreSQL (운영) 지원
- **Desktop & MCP**: Electron 패키징 및 Model Context Protocol 서버 제공

### 1.2 데이터 흐름 (Data Flow)
1. **수집**: `ETFDataCollector`가 Naver Finance 및 Naver Search API로부터 시세, 매매동향, 뉴스를 스크래핑합니다.
2. **저장**: 수집된 데이터는 검증(Validation) 및 정제(Cleaning) 과정을 거쳐 RDBMS에 저장됩니다.
3. **가공**: 백엔드 서비스 계층에서 수익률, 변동성, 샤프 지수 등 주요 메트릭을 계산합니다.
4. **소비**: 프런트엔드(React)는 차트와 테이블로 시각화하고, MCP 서버는 AI 에이전트(Claude 등)가 활용할 수 있는 도구(Tools)로 제공합니다.

---

## 2. 백엔드 (Backend) 기술 분석

### 2.1 데이터 수집 전략 (Smart Scraper)
`backend/app/services/data_collector.py`는 본 프로젝트의 핵심 엔진입니다.
- **중복 방지 (Smart Collection)**: 데이터베이스의 마지막 기록 날짜를 확인하여 누락된 기간만 선택적으로 수집합니다.
- **병렬 처리**: `ThreadPoolExecutor`를 사용하여 여러 종목의 데이터를 동시에 수집하여 성능을 극대화합니다.
- **안정성**: `RateLimiter`로 요청 속도를 제어하고, `retry_with_backoff` 데코레이터를 통해 네트워크 오류에 대응합니다.

### 2.2 API 설계 및 모델링
- **Pydantic V2**: 강력한 데이터 검증 및 스키마 정의를 위해 Pydantic을 전방위적으로 사용합니다.
- **비동기 처리**: FastAPI의 비동기 기능을 활용하여 효율적인 IO 처리를 수행합니다.
- **통합 로깅**: `structlog`를 사용하여 구조화된 로그를 남겨 운영 편의성을 높였습니다.

---

## 3. 프런트엔드 (Frontend) 및 시각화

### 3.1 기술 스택
- **React 18**: 컴포넌트 기반 UI 개발.
- **Tailwind CSS**: 유틸리티 우선 방식의 빠른 스타일링.
- **Recharts**: 금융 차트(캔들스틱, 선 그래프, 히트맵 등) 시각화의 핵심 라이브러리.
- **TanStack Query (v5)**: 서버 상태 관리 및 캐싱을 효율적으로 처리.

### 3.2 주요 UI 구성 요소
- **Dashboard**: 관심 종목의 주간 수익률 및 최신 뉴스를 한눈에 파악.
- **ETF Detail**: 상세 시세 차트, 매매동향(외인/기관), AI 인사이트 요약 제공.
- **Scanner**: 필터 조건을 조합하여 투자 대상 ETF를 발굴하는 강력한 도구.

---

## 4. MCP (Model Context Protocol) 서버

`mcp-server/`는 이 프로젝트를 단순한 웹 앱을 넘어 AI 생태계로 확장시키는 핵심 요소입니다.
- **도구 노출 (Tool Exposure)**: `list_stocks`, `get_etf_prices`, `simulate_portfolio` 등 15개 이상의 백엔드 기능을 MCP 도구로 변환합니다.
- **AI 연동**: Claude와 같은 LLM이 직접 실시간 시장 데이터를 조회하고 투자 시뮬레이션을 실행하여 리포트를 작성할 수 있게 합니다.

---

## 5. 특화 기능 (Special Features)

1. **투자 시뮬레이션**:
   - **일시 투자**: 특정 과거 시점에 매수했을 때의 수익률 계산.
   - **적립식(DCA)**: 매월 일정 금액 투자 시 코스트 에버리징 효과 분석.
   - **포트폴리오**: 여러 종목의 비중을 설정하여 가상의 포트폴리오 성과 측정.
2. **뉴스 감성 분석**: 수집된 뉴스 제목과 내용을 분석하여 시장의 심리 상태를 파악하는 기능(예정/구현 중).
3. **알림 시스템**: 설정한 목표가 도달 또는 이상 급등락 발생 시 사용자에게 알림 제공.

---

## 7. 상세 구현 기능 및 지표 계산식

본 섹션에서는 프로그램 내에서 사용되는 주요 금융 지표의 계산 로직을 설명합니다. (최근 분석을 통해 표준 거래일 기준으로 수정되었습니다.)

### 7.1 수익률 계산식 (Returns)
모든 수익률은 퍼센트(%) 단위로 계산되며, `(현재가 - 기준가) / 기준가 * 100` 공식을 따릅니다.

1.  **일별 수익률 (`daily_change_pct`)**:
    -   공식: `(당일 종가 - 전일 종가) / 전일 종가 * 100`
    -   데이터 소스: 네이버 금융의 전일비를 파싱하여 활용.
2.  **주간 수익률 (`1w`)**:
    -   공식: `(현재가 - 5거래일 전 종가) / 5거래일 전 종가 * 100`
    -   수정 사항: 기존 7데이터 포인트에서 표준 영업일인 **5거래일**로 수정됨.
3.  **월간 수익률 (`1m`)**:
    -   공식: `(현재가 - 20거래일 전 종가) / 20거래일 전 종가 * 100`
    -   수정 사항: 기존 30데이터 포인트에서 표준 영업일인 **20거래일**로 수정됨.
4.  **연간 수익률 (`ytd`)**:
    -   공식: `(현재가 - 올해 첫 거래일 종가) / 올해 첫 거래일 종가 * 100`
    -   기준일: 해당 연도 1월 1일 이후의 가장 빠른 거래일.

### 7.2 스캐너 (`/scanner`) 주요 지표
스캐너 화면에서 제공되는 실시간 및 집계 데이터의 정의는 다음과 같습니다.

-   **현재가 (`close_price`)**: 수집 시점의 최신 종가.
-   **등락률 (`daily_change_pct`)**: 전일 대비 당일 가격 변동폭(%).
-   **거래량 (`volume`)**: 당일 누적 거래량 (단위: 주).
-   **주간 수익률 (`weekly_return`)**:
    -   공식: `(현재가 - 5거래일 전 종가) / 5거래일 전 종가 * 100`
    -   상세 페이지 및 스캐너 페이지 모두 동일하게 **최근 5번째 거래일(1주일 전)** 데이터를 기준으로 하는 롤링 윈도우(Rolling Window) 방식을 사용합니다.
-   **월간 수익률 (`monthly_return`)**:
    -   공식: `(현재가 - 20거래일 전 종가) / 20거래일 전 종가 * 100`
    -   스캐너에서 최근 **20거래일(약 1개월)** 성과를 파악하기 위해 사용됩니다.
-   **연간 수익률 (`ytd_return`)**:
    -   공식: `(현재가 - 올해 첫 거래일 종가) / 올해 첫 거래일 종가 * 100`
    -   올해 초 대비 현재까지의 성과를 나타냅니다.
-   **외국인/기관 순매수 (`foreign_net`, `institutional_net`)**:
    -   최근 1거래일 동안의 투자자별 순매수 수량입니다.
    -   단위: **주(Quantity)**. (네이버 금융의 투자자별 매매동향 데이터 기반)

### 7.3 거래일(Trading Day)의 정의
본 프로그램에서 사용하는 '5거래일' 또는 '20거래일'은 달력상의 일수가 아닌 **주식 시장이 실제로 개장된 날**만을 카운트합니다.
-   **주말 및 공휴일 제외**: 토/일요일 및 시장 휴장일은 데이터 포인트에서 제외되므로, 자동으로 다음(혹은 이전) 영업일 데이터를 참조합니다.
-   **데이터 무결성**: 수집 시점에 5개 미만의 데이터만 존재할 경우(예: 신규 상장주), 가용한 가장 오래된 데이터를 기준가로 사용하여 오차를 최소화합니다.

---

## 8. 작업 스케줄링 및 취소 흐름 (Bug Report)

시스템의 백그라운드 데이터 수집(Catalog Data Collection) 흐름을 심층 분석한 결과, **사용자의 취소 요청(Cancel Request)이 무시되고 백그라운드 작업이 계속 실행되는 심각한 리소스 누수(좀비 태스크) 버그**가 발견되었습니다.

### 8.1 버그 원인 분석
데이터 수집 작업(`CatalogDataCollector.collect_all`)은 4개의 페이즈(Phase)로 나뉘어 실행됩니다.
1. ETF 가격 수집
2. ETF 수급 수집 (병렬)
3. DB 저장
4. **KOSPI/KOSDAQ 주식 가격+수급 업데이트** (문제 발생 구간)

Phase 1~3에서는 작업 단위 사이에 `is_cancelled(TASK_ID)`를 확인하여 정상적으로 프로세스를 중단하지만, 가장 부하가 큰 **Phase 4(`_update_stock_prices`) 내부에는 취소 확인 로직이 전무**합니다.

### 8.2 상세 문제점
1. **페이지네이션 루프 내 취소 부재**: Phase 4 초기에는 코스피/코스닥 전체 목록을 가져오기 위해 네이버 금융을 최대 190페이지(80+110) 순회합니다. 이 `while` 루프 중간에 취소 요청이 들어와도 루프는 멈추지 않습니다.
2. **병렬 워커(ThreadPool) 통제 불능**: 상위 500개 주식의 수급 데이터를 모으기 위해 `ThreadPoolExecutor`를 사용하지만, 각 워커 스레드나 `as_completed` 처리 루프 안에서 `is_cancelled`를 검사하지 않습니다.
3. **Future 취소 로직 누락**: 취소 이벤트 발생 시 대기열에 있는 작업을 폐기하는 `future.cancel()` 처리가 없어, 한 번 스케줄링된 500개의 네트워크 요청이 무조건 끝까지 실행됩니다.

### 8.3 시스템에 미치는 영향
- **네트워크 차단 위험**: 스크래퍼가 멈추지 않고 불필요한 트래픽을 계속 유발하여 네이버 금융 서버로부터 IP가 차단(Rate Limit)될 수 있습니다.
- **서버 리소스 고갈**: 취소 후 새로운 수집 작업을 다시 시작할 경우, 기존의 좀비 스레드와 새로운 스레드가 동시에 실행되어 서버의 메모리와 CPU를 급격히 소모합니다.

이 문제는 시스템의 안정성을 크게 저해하므로 `CatalogDataCollector` 및 `TickerCatalogCollector`의 긴 루프 및 스레드 풀 내부에 명시적인 취소 확인 및 방어 로직을 즉각 주입해야 합니다.

---

## 9. 최근 업데이트 및 시스템 수정 사항 (Recent Updates & Fixes)

이 섹션은 다른 LLM 에이전트나 개발자가 최근 코드베이스의 주요 변경 사항을 파악할 수 있도록 기록되었습니다.

### 9.1 스캐너(Scanner) 중장기 성과 지표 추가
- **요구사항**: 스캐너 화면에 주간 수익률 외에 '월간 수익률' 및 '연간 수익률(YTD)'을 추가.
- **DB 스키마 변경**: `stock_catalog` 테이블에 `monthly_return` 및 `ytd_return` 컬럼 추가.
- **백엔드 수집 로직 (`CatalogDataCollector._fetch_supply_data`)**:
  - 네이버 금융 `frgn.naver`에서 기존 1페이지 수집에서 **최대 2페이지(약 40거래일)**까지 수집하도록 확장.
  - 월간 수익률은 **최근 20번째 거래일(1개월)** 종가 대비 수익률로 계산.
  - 연간(YTD) 수익률은 **올해 첫 거래일** 종가 대비 수익률로 계산.
- **API 및 프런트엔드**:
  - `ScreeningItem` Pydantic 모델에 필드 추가.
  - 스캐너 검색 API(`/scanner`)에 `min_monthly_return`, `max_ytd_return` 등의 필터링 조건 추가 및 정렬(Sort) 지원.
  - React 프런트엔드(`ScreeningTable.jsx`, `ScreeningFilters.jsx`)에 해당 컬럼 및 필터 입력 UI 반영.

### 9.2 데이터 수집 스케줄러 '좀비 태스크' 버그 픽스
- **문제점**: 백그라운드 데이터 수집 중 사용자가 UI에서 취소를 요청해도, 가장 부하가 큰 코스피/코스닥 스크래핑(Phase 4)이 멈추지 않고 끝까지 실행되는 심각한 리소스 누수(Resource Leak) 발견.
- **해결책 (`ticker_catalog_collector.py`, `catalog_data_collector.py`)**:
  1. `_collect_sise_stocks` 함수 내의 190페이지 순회 `while` 루프에 `is_cancelled(task_id)` 검사 주입하여 즉시 `break` 가능하도록 조치.
  2. `_update_stock_prices` 함수의 상위 500개 종목 수급 병렬 수집(`ThreadPoolExecutor`) 로직 개선:
     - `fetch_supply` 작업 시작 전에 취소 여부 확인.
     - `as_completed(futures)` 루프 내에서 취소 감지 시 **남은 모든 Future를 명시적으로 취소(`f.cancel()`)**하고 루프 탈출.
- **기타 수정**: 로컬 개발 시 코드 변경 사항이 백엔드 서버에 즉시 반영되도록 `run.sh`의 uvicorn 실행 명령어에 `--reload` 옵션 추가.

---

## 10. 신규 버그 분석 보고서 (Bug Investigation Report)

이 섹션은 최근 추가된 기능(9.1 스캐너 중장기 성과 지표, 9.2 좀비 태스크 픽스) 이후 코드베이스를 심층 분석하여 발견된 잠재적 버그 목록입니다.

---

### [BUG-01] 🔴 CRITICAL: YTD 수익률 — 연 후반부로 갈수록 기준일이 틀려짐

**파일**: `backend/app/services/catalog_data_collector.py`, 라인 567–574
**함수**: `_fetch_supply_data`

**문제 설명**:
YTD(연초 대비) 수익률 계산의 기준가로 "올해 첫 거래일의 종가"를 사용해야 하지만, 현재 코드는 `frgn.naver` 페이지를 최대 2페이지(약 40거래일)만 수집한다. 수집된 데이터 중 올해 날짜만 필터링한 뒤 가장 오래된 항목(`this_year_prices[-1]`)을 기준으로 삼는 구조이다.

```python
this_year_prices = [p for p in prices_with_date if p[0].year == current_year]
if len(this_year_prices) >= 2:
    base_val = this_year_prices[-1][1]   # 수집된 올해 데이터 중 가장 오래된 것
    ytd_return = calc_ret(current_val, base_val)
```

**언제 틀려지는가**:
연간 거래일은 약 252일이다. 40거래일(2페이지)을 소급하면 오늘부터 약 2개월 전까지밖에 도달하지 못한다.

| 날짜 | 연중 누적 거래일 | 40거래일 소급 결과 | YTD 기준일 정확 여부 |
|---|---|---|---|
| 2월 말 (오늘) | ~40일 | 1월 초 도달 | ✅ 아슬아슬하게 정확 |
| 3월 중순 | ~55일 | 1월 중순 도달 | ❌ 틀림 (1월 2일 미도달) |
| 6월 | ~120일 | 4월 도달 | ❌ 크게 틀림 |
| 12월 | ~240일 | 10월 도달 | ❌ 매우 크게 틀림 |

**영향**: 3월 이후 모든 KOSPI/KOSDAQ 상위 종목(KOSPI 200 + KOSDAQ 300)의 YTD 수익률이 실제 연초 대비가 아닌 불과 2개월 전 대비 수익률로 표시됨. 스캐너 YTD 필터 기반 전략이 무의미해짐.

**근본 원인**: `_fetch_supply_data`의 수집 범위(최대 2페이지 = ~40거래일)가 YTD 계산에 필요한 범위(최대 12개월 = ~252거래일)를 충족하지 못함.

---

### [BUG-02] 🟠 HIGH: 상위 N개 종목 UPDATE 시 monthly_return / ytd_return NULL 덮어쓰기

**파일**: `backend/app/services/catalog_data_collector.py`, 라인 297–316
**함수**: `_update_stock_prices`

**문제 설명**:
Phase 4에서 KOSPI/KOSDAQ 상위 N개 종목(`top_ticker_set`)을 업데이트할 때, `supply_map[ticker]`에서 가져온 값을 직접 SET한다. 만약 `_fetch_supply_data`가 데이터 부족으로 `monthly_return=None` 또는 `ytd_return=None`을 반환한 경우, 기존 DB에 저장된 유효한 값이 **NULL로 덮어써진다**.

```python
# 상위 N개 브랜치 (문제 있음)
cursor.execute(f"""
    UPDATE stock_catalog
    SET ...
        weekly_return = {p}, monthly_return = {p}, ytd_return = {p},  -- None이면 NULL 저장!
    ...
""", (..., sup.get("weekly_return"), sup.get("monthly_return"), sup.get("ytd_return"), ...))
```

반면, 하위 종목 브랜치는 COALESCE로 기존 값을 보호한다:
```python
# 하위 종목 브랜치 (올바른 처리)
"weekly_return = COALESCE({p}, weekly_return),"
```

**언제 발생하는가**:
- frgn.naver 페이지에서 해당 종목의 데이터가 20개 미만(월간 계산 불가)이거나 40개 미만(YTD 계산 불가)인 경우.
- 신규 상장 종목이나 거래량 극소 종목이 상위 N개에 포함된 경우.
- 네트워크 오류로 일부 페이지 수집이 실패한 경우.

**영향**: 이전 수집에서 정확하게 저장된 monthly_return / ytd_return 값이 다음 수집 사이클에서 NULL로 초기화됨.

---

### [BUG-03] 🟠 HIGH: 상위 N개 종목의 week_base_date가 항상 "오늘"로 재설정 → 하위 전락 시 주간수익률 0% 초기화

**파일**: `backend/app/services/catalog_data_collector.py`, 라인 303–312
**함수**: `_update_stock_prices`

**문제 설명**:
상위 N개 종목을 업데이트할 때 `week_base_price = close_price`(오늘 종가), `week_base_date = today_str`(오늘 날짜)로 강제 설정된다.

```python
cursor.execute(..., (
    ...
    close_price, today_str,   # week_base_price = 오늘 종가, week_base_date = "2026-02-26"
    ticker
))
```

하위 종목 브랜치의 weekly_return 계산 로직은 `week_base_date`가 "이번 주 월요일 날짜"(`target_base_str`)와 일치하는지 확인한다:

```python
target_base_str = target_base_date.isoformat()  # 예: "2026-02-23" (월요일)
if week_base_date == target_base_str and ...:
    # 기준일 일치 → 정상 계산
else:
    # 불일치 → weekly_return = 0.0으로 초기화!
    new_weekly_return = 0.0
```

**시나리오**:
1. 종목 A가 수집 시점에 상위 N개에 포함 → `week_base_date = "2026-02-26"`(수요일)로 설정됨.
2. 다음 수집 사이클에서 종목 A가 상위 N개에서 탈락 → 하위 브랜치로 처리.
3. `week_base_date("2026-02-26") != target_base_str("2026-02-23")` → weekly_return이 **0.0으로 리셋됨**.

**영향**: 시가총액 경계 근처의 종목들이 수집마다 상위/하위를 오가면서 주간수익률이 0%로 반복 초기화됨. 스캐너 주간수익률 필터가 이 종목들에 대해 신뢰할 수 없게 됨.

---

### [BUG-04] 🟡 MEDIUM: _collect_supply_demand의 progress total_steps가 3으로 잘못 하드코딩

**파일**: `backend/app/services/catalog_data_collector.py`, 라인 458–465
**함수**: `_collect_supply_demand`

**문제 설명**:
`collect_all()`은 전체 프로세스를 4단계(total_steps=4)로 정의하지만, Phase 2를 처리하는 `_collect_supply_demand()` 내부의 progress 업데이트는 `total_steps=3`을 사용한다.

```python
# collect_all() 내 Phase 1 업데이트
update_progress(TASK_ID, {"total_steps": 4, "step_index": 0, ...})

# _collect_supply_demand() 내 진행 업데이트 (잘못됨)
update_progress("catalog-data", {
    "total_steps": 3,   # ← 잘못된 값: 4여야 함
    "step_index": 1,
    ...
})
```

**영향**: 프론트엔드 진행률 표시가 Phase 2 중 갑자기 총 4단계에서 3단계로 변경되어 진행률 바가 불안정하게 점프하거나 100%를 초과하는 UI 버그 발생.

---

### [BUG-05] 🟡 MEDIUM: _fetch_supply_data — YTD 조건 len >= 2가 실질적으로 무의미

**파일**: `backend/app/services/catalog_data_collector.py`, 라인 571–574
**함수**: `_fetch_supply_data`

**문제 설명**:
YTD 수익률을 계산하기 위해 `len(this_year_prices) >= 2` 조건을 사용한다.

```python
this_year_prices = [p for p in prices_with_date if p[0].year == current_year]
if len(this_year_prices) >= 2:
    base_val = this_year_prices[-1][1]
    ytd_return = calc_ret(current_val, base_val)
```

올해 데이터가 2개 이상이라는 조건은 "올해 첫 거래일에 도달했다"는 것을 보장하지 않는다. 예를 들어 3월에 수집할 경우 `this_year_prices`에는 1~2월 데이터가 있지만, 가장 오래된 항목(`[-1]`)은 2월 초 데이터이지 1월 2일 데이터가 아니다. BUG-01과 연관된 세부 문제로, 조건 자체가 "올해 첫 거래일에 도달했는가"가 아닌 단순 수량 체크여서 **YTD 기준일이 틀려도 계산이 그냥 진행된다**.

**올바른 조건**: 수집된 데이터 중 올해 1월 1~15일 내의 날짜가 존재하는지 확인하거나, 페이지 수집 범위를 충분히 확장해야 함.

---

### [BUG-06] 🟢 MINOR: _collect_etf_prices — 보합(risefall='3') 등락률 0 처리 누락

**파일**: `backend/app/services/catalog_data_collector.py`, 라인 393–402
**함수**: `_collect_etf_prices`

**문제 설명**:
네이버 ETF JSON API의 `risefall` 필드 값은 `"2"`(상승), `"3"`(보합), `"5"`(하락)이다. 현재 코드는 `"5"`인 경우에만 음수 처리를 하고, `"3"`(보합)인 경우 `changeRate`를 명시적으로 0으로 설정하지 않는다.

```python
change_rate = item.get('changeRate')
if item.get('risefall') == '5' and change_rate is not None:
    change_rate = -abs(change_rate)
# risefall == '3' (보합)인 경우 changeRate가 non-zero면 그대로 통과됨
```

**영향**: 네이버 API가 보합 종목에 대해 미세하게 0이 아닌 `changeRate`를 반환할 경우(드문 케이스이나 API 오류 시 가능), 등락률이 ±0이 아닌 값으로 저장될 수 있음.

---

### [BUG-07] 🟢 MINOR: ScreeningFilters.jsx — onBlur 즉시 필터 적용이 검색 버튼과 중복 트리거

**파일**: `frontend/src/components/screening/ScreeningFilters.jsx`, 라인 61–73
**함수**: `applyNumberFilter`, `handleSearch`

**문제 설명**:
숫자 필터 입력 필드(주간/월간/연간 최소·최대 %)는 `onBlur` 이벤트에서 `applyNumberFilter`를 호출하여 즉시 `onFilterChange`를 트리거한다. 이 함수는 변경된 단일 키-값만을 전달하는 부분 업데이트 방식(`onFilterChange({ [key]: parsed })`)이다.

```javascript
onBlur={(e) => applyNumberFilter('min_monthly_return', e.target.value)}
// ...
const applyNumberFilter = (key, value) => {
    // ...
    onFilterChange({ [key]: parsed })  // 부분 업데이트 즉시 전송
}
```

반면, "검색" 버튼의 `handleSearch`는 모든 로컬 상태를 모아서 한 번에 전달한다. 이로 인해 사용자가 필터를 여러 개 입력하는 과정에서 불필요한 중간 API 호출이 최대 N-1회(N = 입력된 필터 수) 발생한다.

**영향**: 서버 부하 증가, 불필요한 쿼리 실행, UI에서 중간 결과가 순간적으로 깜빡이는 현상.

---

### 버그 우선순위 요약

| ID | 심각도 | 파일 | 함수 | 핵심 문제 |
|---|---|---|---|---|
| BUG-01 | 🔴 CRITICAL | `catalog_data_collector.py:567` | `_fetch_supply_data` | YTD 기준일, 3월 이후 틀린 값 |
| BUG-02 | 🟠 HIGH | `catalog_data_collector.py:297` | `_update_stock_prices` | monthly/ytd NULL 덮어쓰기 |
| BUG-03 | 🟠 HIGH | `catalog_data_collector.py:303` | `_update_stock_prices` | week_base_date 항상 오늘로 초기화 |
| BUG-04 | 🟡 MEDIUM | `catalog_data_collector.py:460` | `_collect_supply_demand` | progress total_steps 3 vs 4 불일치 |
| BUG-05 | 🟡 MEDIUM | `catalog_data_collector.py:571` | `_fetch_supply_data` | YTD len>=2 조건 불충분 |
| BUG-06 | 🟢 MINOR | `catalog_data_collector.py:393` | `_collect_etf_prices` | 보합 등락률 0 미처리 |
| BUG-07 | 🟢 MINOR | `ScreeningFilters.jsx:73` | `applyNumberFilter` | onBlur 중복 API 호출 |

---

## 11. 버그 수정 계획 (Fix Plan)

### 수정 원칙
- 각 버그는 독립적으로 수정하되, 연관된 BUG-01/05는 함께 처리한다.
- 기존 동작을 바꾸는 수정은 최소화하고, 추가 로직으로 방어한다.
- DB 스키마 변경 없이 코드 수정만으로 해결한다.

---

### FIX-01+05: YTD 기준일 수집 부족 문제 해결

**대상 버그**: BUG-01, BUG-05
**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_fetch_supply_data`

**수정 방향**: 2페이지 하드코딩을 없애고, YTD 계산에 필요한 충분한 데이터를 확보할 때까지 페이지를 동적으로 수집한다. 단, 무한 수집 방지를 위해 최대 페이지 수 상한을 설정한다.

**상세 계획**:
1. 페이지 루프 종료 조건을 `range(1, 3)` 고정값에서 `while` 루프로 변경한다.
2. 루프 계속 조건: 현재 연도(`current_year`)의 1월 1~15일 내의 날짜가 수집 목록에 포함될 때까지 반복.
3. 안전 상한: 최대 15페이지(약 300거래일, 1년치 이상)로 제한한다.
4. BUG-05 동시 수정: YTD 계산 조건을 `len >= 2`에서 **"올해 1월 1~15일 날짜를 가진 데이터가 존재하는가"** 로 교체한다.

**수정 후 로직 (의사 코드)**:
```python
MAX_PAGES = 15
current_year = date.today().year

def _has_ytd_base(prices_with_date, year):
    """올해 1월 1~15일 내의 데이터가 있으면 True (= 올해 첫 거래일에 도달했다는 근사 판단)"""
    for d, _ in prices_with_date:
        if d.year == year and d.month == 1 and d.day <= 15:
            return True
    return False

page = 1
while page <= MAX_PAGES:
    # ... 페이지 수집 ...
    if len(prices_with_date) >= 40 and _has_ytd_base(prices_with_date, current_year):
        break
    if not page_had_data:
        break
    page += 1

# YTD 계산
this_year_prices = [p for p in prices_with_date if p[0].year == current_year]
if _has_ytd_base(prices_with_date, current_year) and this_year_prices:
    base_val = this_year_prices[-1][1]
    ytd_return = calc_ret(current_val, base_val)
```

**주의사항**:
- 페이지 수가 늘어나므로 병렬 수집 시 요청 수 증가. `use_rate_limiter=False` 경로이므로 네이버 차단 위험 상승 → 호출 간격 조정 검토.
- ETF 수집(`_collect_supply_demand`)은 ETF 상장일이 연초보다 늦을 수 있으므로, 1월 데이터 미존재 시 수집된 가장 오래된 데이터를 YTD 기준으로 fallback 처리 추가.

---

### FIX-02: 상위 N개 종목 UPDATE 시 NULL 덮어쓰기 방지

**대상 버그**: BUG-02
**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_update_stock_prices`, 라인 297–316

**수정 방향**: 상위 N개 종목 UPDATE 쿼리에서 `monthly_return`, `ytd_return` 컬럼에 `COALESCE`를 적용하여, None(NULL)이 들어올 경우 기존 DB 값을 유지한다.

**수정 전**:
```sql
SET ...
    weekly_return = ?,
    monthly_return = ?,
    ytd_return = ?,
...
```

**수정 후**:
```sql
SET ...
    weekly_return  = COALESCE(?, weekly_return),
    monthly_return = COALESCE(?, monthly_return),
    ytd_return     = COALESCE(?, ytd_return),
...
```

**주의사항**:
- `weekly_return`도 동일하게 COALESCE 적용 고려 (frgn.naver에서 weekly 계산 실패 시 기존 값 보존).
- 이 수정은 "한 번 저장된 값은 명시적으로 NULL을 넣지 않는 한 지워지지 않는다"는 방어적 원칙을 일관되게 적용하는 것.

---

### FIX-03: week_base_date 재설정 로직 수정

**대상 버그**: BUG-03
**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_update_stock_prices`, 라인 303–312

**문제 핵심**: 상위 N개 종목을 업데이트할 때 `week_base_date = today_str`으로 설정하면, 하위 브랜치의 기준일 비교(`== target_base_str`, 즉 이번 주 월요일)에서 항상 불일치가 발생한다.

**수정 방향**: 상위 N개 종목의 `week_base_date`도 하위 종목과 동일하게 `target_base_str`(이번 주 월요일)을 사용하고, `week_base_price`는 `target_base_str` 시점의 가격을 사용해야 한다. 그러나 `_fetch_supply_data`로 수집한 가격 시계열에서 해당 날짜의 가격을 역산하기가 복잡하므로, 다음과 같은 실용적 접근을 취한다.

**수정 방향 (2단계)**:
1. **week_base_date를 `target_base_str`로 변경**: `today_str` 대신 `target_base_str`(이번 주 월요일) 저장.
2. **week_base_price는 현재 close_price 유지**: 월요일 가격을 역산하는 것은 복잡하므로, 첫 수집 시는 오늘 가격을 기준으로 삼고 다음 수집부터 안정화. 이렇게 해도 BUG-03의 핵심인 "상위→하위 전락 시 0%로 리셋"은 해결된다.

**수정 전**:
```python
week_base_price = close_price, week_base_date = today_str
```

**수정 후**:
```python
week_base_price = close_price, week_base_date = target_base_str
```

**주의사항**:
- `target_base_str`은 `_update_stock_prices` 함수 상단에 이미 계산되어 있으므로 코드 변경 범위가 최소화된다.
- 월요일 이전에 수집된 경우 `target_base_str`이 지난 주 월요일을 가리키므로 주간 수익률이 1주일 이상의 기간을 반영할 수 있다. 이는 허용 가능한 오차로 간주한다.

---

### FIX-04: total_steps 값 수정

**대상 버그**: BUG-04
**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_collect_supply_demand`, 라인 460

**수정 방향**: 단순 상수 수정. `"total_steps": 3` → `"total_steps": 4`로 변경.

**수정 전**:
```python
update_progress("catalog-data", {
    "status": "in_progress",
    "step": "supply_demand",
    "step_index": 1,
    "total_steps": 3,   # ← 잘못됨
    ...
})
```

**수정 후**:
```python
update_progress("catalog-data", {
    "status": "in_progress",
    "step": "supply_demand",
    "step_index": 1,
    "total_steps": 4,   # ← 수정
    ...
})
```

---

### FIX-06: 보합 등락률 0 처리 추가

**대상 버그**: BUG-06
**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_collect_etf_prices`, 라인 393–402

**수정 방향**: `risefall == '3'`(보합) 케이스를 명시적으로 처리하여 `change_rate = 0`으로 강제 설정한다.

**수정 전**:
```python
change_rate = item.get('changeRate')
if item.get('risefall') == '5' and change_rate is not None:
    change_rate = -abs(change_rate)
```

**수정 후**:
```python
change_rate = item.get('changeRate')
risefall = item.get('risefall')
if risefall == '5' and change_rate is not None:
    change_rate = -abs(change_rate)
elif risefall == '3':
    change_rate = 0.0
```

---

### FIX-07: onBlur 중복 API 호출 제거

**대상 버그**: BUG-07
**파일**: `frontend/src/components/screening/ScreeningFilters.jsx`
**함수**: `applyNumberFilter`

**수정 방향**: `applyNumberFilter`에서 `onFilterChange` 호출을 제거하고, 로컬 상태 업데이트만 수행하도록 한다. API 호출은 "검색" 버튼 클릭(`handleSearch`) 또는 Enter 키 제출로만 발생하도록 통일한다.

**수정 전**:
```javascript
const applyNumberFilter = (key, value) => {
    // ... 로컬 상태 업데이트 ...
    onFilterChange({ [key]: parsed })  // ← 제거 대상
}
```

**수정 후**:
```javascript
const applyNumberFilter = (key, value) => {
    // ... 로컬 상태 업데이트만 수행, onFilterChange 호출 없음 ...
}
```

**주의사항**: `applyNumberFilter`가 `onFilterChange`를 호출하지 않으면, 사용자가 blur 후 검색 버튼을 누르지 않으면 필터가 적용되지 않는다. UX 관점에서는 검색 버튼 클릭을 명확한 액션으로 삼는 것이 더 직관적이므로 이 변경은 UX 개선이기도 하다.

---

### 수정 작업 순서 및 범위

| 순서 | 수정 ID | 파일 | 변경 규모 | 설명 |
|---|---|---|---|---|
| 1 | FIX-04 | `catalog_data_collector.py` | 1줄 | 가장 단순, 리스크 없음 |
| 2 | FIX-06 | `catalog_data_collector.py` | 2줄 추가 | 단순 방어 코드 추가 |
| 3 | FIX-02 | `catalog_data_collector.py` | SQL 3줄 수정 | COALESCE 추가 |
| 4 | FIX-03 | `catalog_data_collector.py` | 1줄 수정 | today_str → target_base_str |
| 5 | FIX-07 | `ScreeningFilters.jsx` | 1줄 제거 | onFilterChange 호출 제거 |
| 6 | FIX-01+05 | `catalog_data_collector.py` | 30~40줄 변경 | 가장 복잡, 동적 페이지 수집 |

FIX-01+05는 요청 수 증가 및 로직 변경 범위가 크므로 나머지를 먼저 적용한 후 마지막에 작업한다.

---

## 12. 버그 수정 구현 결과 (2026-02-26)

계획(11절)에 따라 6개 항목 모두 수정 완료.

### 12.1 FIX-04 — `total_steps` 3→4 수정

**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_collect_supply_demand`

진행률 표시 단계 수가 3으로 잘못 설정되어 진행바가 올바르게 표시되지 않던 문제를 수정했다.

```python
# BEFORE
update_progress(self.task_id, {'phase': 'supply_demand', 'total_steps': 3, ...})

# AFTER
update_progress(self.task_id, {'phase': 'supply_demand', 'total_steps': 4, ...})
```

---

### 12.2 FIX-06 — 보합 등락률 `0.0` 처리 추가

**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_collect_etf_prices`

Naver ETF 시세 파싱 시 `risefall='3'`(보합) 케이스에서 `change_rate`가 `None`으로 저장되던 문제를 수정했다.

```python
# BEFORE (risefall='3' 케이스 없음 → change_rate = None)
if risefall == '2':   # 상승
    change_rate = float(...)
elif risefall == '5': # 하락
    change_rate = -float(...)

# AFTER
if risefall == '2':
    change_rate = float(...)
elif risefall == '5':
    change_rate = -float(...)
elif risefall == '3': # 보합
    change_rate = 0.0
```

---

### 12.3 FIX-02 + FIX-03 — 상위N 종목 UPDATE COALESCE 적용 및 week_base_date 수정

**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_update_stock_prices` (상위N 종목 UPDATE 블록)

두 버그가 동일한 SQL 블록에 위치하므로 한 번에 수정했다.

**FIX-02**: `weekly_return`, `monthly_return`, `ytd_return`을 `COALESCE`로 감싸 수급 수집 성공분만 갱신하고, 실패 시 기존 DB 값을 보존하도록 했다.

**FIX-03**: `week_base_date` 바인딩 인수가 `today_str`(오늘)이었던 것을 `target_base_str`(해당 주 월요일)로 수정했다.

```python
# BEFORE
SET
    weekly_return  = {p},
    monthly_return = {p},
    ytd_return     = {p},
    week_base_price = {p}, week_base_date = {p},
...
(close_price, weekly_ret, monthly_ret, ytd_ret, close_price, today_str, ticker)

# AFTER
SET
    weekly_return  = COALESCE({p}, weekly_return),
    monthly_return = COALESCE({p}, monthly_return),
    ytd_return     = COALESCE({p}, ytd_return),
    week_base_price = {p}, week_base_date = {p},
...
(close_price, weekly_ret, monthly_ret, ytd_ret, close_price, target_base_str, ticker)
```

---

### 12.4 FIX-07 — ScreeningFilters onBlur 중복 API 호출 제거

**파일**: `frontend/src/components/screening/ScreeningFilters.jsx`
**함수**: `applyNumberFilter`

숫자 필터 입력 후 포커스 이탈(blur) 시 `onFilterChange`가 즉시 호출되어 API가 중복 호출되던 문제를 수정했다. `applyNumberFilter`는 로컬 상태 업데이트만 수행하고, API 호출은 "검색" 버튼 클릭(`handleSearch`)으로만 발생하도록 통일했다.

```javascript
// BEFORE
const applyNumberFilter = (key, value) => {
    // ... 로컬 상태 업데이트 ...
    onFilterChange({ [key]: parsed })  // ← 제거
}

// AFTER
const applyNumberFilter = (key, value) => {
    // ... 로컬 상태 업데이트만 수행 ...
    // 검색 버튼(handleSearch)으로만 API 호출 — blur 시 중복 호출 방지 (FIX-07)
}
```

---

### 12.5 FIX-01+05 — YTD 동적 페이지 수집 및 기준일 검증

**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_fetch_supply_data`

BUG-01(페이지 2개 고정)과 BUG-05(YTD 기준일 미검증)는 근본 원인이 동일하여 함께 수정했다.

**핵심 변경 사항**:
1. 고정 `for page in range(1, 3)` → 동적 `while page <= MAX_SUPPLY_PAGES(15)` 루프
2. `_has_ytd_base()` 내부 헬퍼 추가 — 올해 1월 1~15일 데이터 존재 여부 확인
3. 루프 종료 조건: 데이터 없거나(`page_data_count == 0`), 20개 이상 + YTD 기준일 도달
4. YTD 계산: `_has_ytd_base()` True일 때만 정식 계산, 아니면 fallback 로직(신규 상장 대비)

```python
# BEFORE
for page in range(1, 3):  # 2페이지(약 40거래일)만 수집
    ...
# YTD: len >= 2면 무조건 계산 (기준일 미검증)
if len(prices_with_date) >= 2:
    ytd_return = calc_ret(current_val, prices_with_date[-1][1])

# AFTER
MAX_SUPPLY_PAGES = 15  # 최대 15페이지(약 300거래일)

def _has_ytd_base(prices):
    """수집 목록에 올해 1월 1~15일 데이터가 있으면 True"""
    for d, _ in prices:
        if d.year == current_year and d.month == 1 and d.day <= 15:
            return True
    return False

page = 1
while page <= MAX_SUPPLY_PAGES:
    # ... 페이지 수집 ...
    if page_data_count == 0:
        break
    if len(prices_with_date) >= 20 and _has_ytd_base(prices_with_date):
        break
    page += 1

# YTD: 실제 1월 데이터 도달 확인 후 계산
this_year_prices = [p for p in prices_with_date if p[0].year == current_year]
if this_year_prices and _has_ytd_base(prices_with_date):
    ytd_return = calc_ret(current_val, this_year_prices[-1][1])
elif this_year_prices:
    # fallback: 신규 상장 또는 연말 수집 실패 대비
    ytd_return = calc_ret(current_val, this_year_prices[-1][1])
    logger.debug(f"[{ticker}] YTD fallback: 1월 데이터 미도달")
```

---

### 12.6 수정 완료 요약

| 수정 ID | 버그 등급 | 파일 | 상태 |
|---------|-----------|------|------|
| FIX-04 | MEDIUM | `catalog_data_collector.py` | ✅ 완료 |
| FIX-06 | MINOR | `catalog_data_collector.py` | ✅ 완료 |
| FIX-02 | HIGH | `catalog_data_collector.py` | ✅ 완료 |
| FIX-03 | HIGH | `catalog_data_collector.py` | ✅ 완료 |
| FIX-07 | MINOR | `ScreeningFilters.jsx` | ✅ 완료 |
| FIX-01+05 | CRITICAL+MEDIUM | `catalog_data_collector.py` | ✅ 완료 |

---

## 14. 스캐너 주간수익률 0.0% 버그 심층 분석 (2026-02-27)

### 개요

`/scanner` 화면에서 티커 `144600` (KODEX 은선물(H) ETF)의 주간수익률이 `0.0%`로 표시되는 반면, `/etf/144600` 상세 페이지에서는 정상적인 수익률이 조회된다. 원인 분석을 위해 수익률 계산 경로를 전수 추적한 결과, 두 가지 독립적인 버그를 발견했다.

---

### [BUG-08] 🔴 CRITICAL: Phase 4에서 KOSPI 상장 ETF의 weekly_return이 0.0으로 덮어써짐

**파일**: `backend/app/services/catalog_data_collector.py`, 라인 324–354
**함수**: `_update_stock_prices`
**발견 날짜**: 2026-02-27

#### 문제 설명

`collect_all()`의 Phase 4(`_update_stock_prices`)는 KOSPI/KOSDAQ 종목의 가격 및 수급을 업데이트한다. 이때 네이버 `sise_market_sum.naver?sosok=0` (KOSPI 시총 순위)에서 종목 목록을 수집하는데, **ETF도 KOSPI에 상장되어 있어 이 목록에 포함**된다.

문제는 Phase 4의 기존 DB 조회 쿼리가 ETF 레코드를 제외한다는 점이다:

```python
# Step 2: DB에서 기존 상태 일괄 조회 (라인 221~239)
cursor.execute("""
    SELECT ticker, close_price, week_base_price, week_base_date, weekly_return
    FROM stock_catalog
    WHERE market IN ('KOSPI', 'KOSDAQ')   ← ETF (market='ETF')는 조회되지 않음!
""")
existing_db = { row["ticker"]: row for row in rows }
```

KOSPI 상장 ETF (예: `144600`, `market='ETF'`)는 `price_map`(sise_market_sum에서 수집됨)에는 존재하지만 `existing_db`에는 없다. 이후 루프에서:

```python
for ticker, s in price_map.items():
    db_row = existing_db.get(ticker, {})   # ETF는 {} 반환

    if ticker in top_ticker_set and ticker in supply_map:
        # 수급 수집 성공 → 정상 업데이트
    else:
        # ETF가 top_ticker_set에 없거나 수급 수집 실패 시 여기로 진입
        week_base_date = db_row.get("week_base_date")   # None (db_row가 빈 dict)

        if week_base_date == target_base_str and ...:   # None == "2026-02-23" → False
            ...
        else:
            new_weekly_return = 0.0   # ← 강제로 0.0 설정!

        cursor.execute("""
            UPDATE stock_catalog
            SET weekly_return = COALESCE(?, weekly_return),   # COALESCE(0.0, old) = 0.0 !!
            ...
            WHERE ticker = ?   # ← ETF 행에도 매칭됨 (market 필터 없음)
        """, (..., new_weekly_return, ..., ticker))
```

`COALESCE(0.0, weekly_return)`은 `0.0`이 NULL이 아니므로 항상 `0.0`을 반환한다. Phase 2+3에서 올바르게 계산·저장된 ETF의 `weekly_return`이 Phase 4에 의해 `0.0`으로 덮어써진다.

#### 재현 조건

- ETF가 KOSPI `sise_market_sum` 목록에 포함됨 (KOSPI 상장 ETF 전체 해당)
- 해당 ETF가 `top_ticker_set`에 미포함 (KOSPI 상위 200개 밖), 또는 수급 수집 실패

#### 수정 방향 (FIX-08)

**방안 A (권장)**: Phase 4의 UPDATE WHERE 절에 `AND market NOT IN ('ETF')` 추가

```sql
UPDATE stock_catalog
SET ...
WHERE ticker = ?
  AND market NOT IN ('ETF')   ← ETF 행은 Phase 4에서 수정하지 않음
```

**방안 B**: `existing_db` 조회 범위를 확장하거나, `price_map`에서 ETF 티커를 사전에 제외

```python
# sise_market_sum에서 수집한 목록에서 ETF 제외
# (DB에서 ETF 티커 목록을 조회하여 price_map에서 제거)
```

---

### [BUG-09] 🟠 HIGH: 스캐너와 ETF 상세 페이지의 주간수익률 계산 방식 불일치

**관련 파일**:
- 스캐너: `backend/app/services/catalog_data_collector.py`, 라인 590 (`_fetch_supply_data`)
- ETF 상세: `backend/app/routers/etfs.py`, 라인 860–872 (배치 요약 엔드포인트)

**발견 날짜**: 2026-02-27

#### 문제 설명

두 화면이 `weekly_return`을 서로 다른 방식으로 계산한다.

| 구분 | 계산 방식 | 기준 |
|------|-----------|------|
| **스캐너** (`stock_catalog.weekly_return`) | frgn.naver 4거래일 전 종가 대비 | `prices_with_date[4]` (0-indexed, 4일 전) |
| **ETF 상세** (실시간 계산) | 이번 주 첫 거래일(월요일) 종가 대비 | DB 가격 히스토리에서 당주 월요일 종가 조회 |

```python
# 스캐너 (catalog_data_collector.py:590)
weekly_return = calc_ret(current_val, prices_with_date[4][1])
# prices_with_date[4] = 4거래일 전 종가 (고정 롤링 4일 윈도우)

# ETF 상세 (etfs.py:860-872)
week_start = end_date - timedelta(days=end_date.weekday())  # 이번 주 월요일
week_prices = [p for p in prices if p.date >= week_start]  # 이번 주 가격들
current_price = week_prices[0].close_price   # 최신 종가
base_price    = week_prices[-1].close_price  # 이번 주 첫 거래일(월요일) 종가
summary.weekly_return = (current_price - base_price) / base_price * 100
```

#### 수요일 기준 예시

| 지표 | 스캐너 | ETF 상세 |
|------|--------|----------|
| 현재가 기준 | 수요일 종가 | 수요일 종가 |
| 기준가 | **지난주 금요일** 종가 (4거래일 전) | **이번 주 월요일** 종가 |
| 수익률 의미 | 금~수 5일 성과 | 월~수 3일 성과 |

요일에 따라 두 수치의 차이가 최대 수 퍼센트포인트까지 벌어질 수 있다.

#### 영향

- 사용자가 스캐너에서 보는 주간수익률과 ETF 상세에서 보는 주간수익률이 달라 혼란 유발
- research.md 섹션 7.2 "스캐너 주간수익률 = 최근 5번째 거래일 롤링 윈도우"라는 기존 문서도 **사실상 부정확** (실제로는 4거래일 전)
  - `prices_with_date[4]` (0-indexed) = 4거래일 전 = **4일** 롤링 윈도우
  - 5거래일 전을 기준으로 하려면 `prices_with_date[5]`를 사용해야 함

#### 수정 방향 (FIX-09)

스캐너의 `weekly_return`을 ETF 상세와 동일한 "이번 주 월요일 대비" 방식으로 통일하거나, 아니면 명확하게 두 방식의 차이를 문서화하고 UI에 표기법을 구분하는 것을 권장.

---

### 버그 우선순위 업데이트

| ID | 심각도 | 함수 | 핵심 문제 | 상태 |
|----|--------|------|-----------|------|
| BUG-08 | 🔴 CRITICAL | `_update_stock_prices` | ETF weekly_return이 Phase 4에서 0.0으로 덮어써짐 | ✅ 완료 |
| BUG-09 | 🟠 HIGH | `_fetch_supply_data` / `etfs.py 배치요약` | 스캐너 vs 상세 주간수익률 계산 방식 불일치 | ✅ 완료 |

---

## 13. YTD 기준일 표시 기능 추가 (2026-02-26)

YTD 수익률이 언제부터 계산된 것인지를 UI에 표시하는 기능을 추가했다. 신규 상장 종목이나 데이터 수집 실패로 fallback 계산이 이루어진 경우, 사용자가 기준일을 알 수 있도록 스크리닝 테이블에 날짜를 함께 노출한다.

### 13.1 배경

FIX-01+05에서 YTD는 올해 첫 거래일(1월)을 기준으로 계산되도록 수정했다. 그러나 신규 상장 종목이나 연초 데이터 수집 실패 종목의 경우, 1월 데이터에 도달하지 못하고 수집된 가장 오래된 데이터를 fallback 기준으로 삼는다. 이 경우 YTD 수치는 연초 대비가 아닌 상장일(또는 복구일) 대비 수익률이 되므로, 사용자에게 기준일 정보가 없으면 오해를 유발할 수 있다.

### 13.2 변경 파일 및 내용

**`backend/app/services/catalog_data_collector.py`**
- `_fetch_supply_data` 반환 dict에 `ytd_base_date` 키 추가 (형식: `"YYYY.MM.DD"`).
- ETF INSERT (`ON CONFLICT DO UPDATE`): `ytd_base_date = COALESCE(EXCLUDED.ytd_base_date, stock_catalog.ytd_base_date)`.
- KOSPI/KOSDAQ UPDATE: `ytd_base_date = COALESCE({p}, ytd_base_date)`.

**`backend/app/database.py`**
- `screening_columns` 리스트에 `("ytd_base_date", "TEXT")` 추가 → 서버 재시작 시 마이그레이션 자동 실행.

**`backend/app/models.py`**
- `ScreeningItem`에 `ytd_base_date: Optional[str] = None` 필드 추가.

**`backend/app/routers/scanner.py`**
- SELECT 쿼리에 `sc.ytd_base_date` 추가.
- `_row_to_screening_item()`에 `ytd_base_date=row.get('ytd_base_date')` 매핑 추가.

**`frontend/src/components/screening/ScreeningTable.jsx`**
- YTD 셀을 `flex flex-col items-end`로 변경.
- `ytd_base_date`가 있고 해당 연도의 1월이 아닌 경우, 수익률 아래에 `MM.DD ~` 형식으로 기준일을 작은 회색 글씨로 표시.

```jsx
{item.ytd_base_date && !item.ytd_base_date.startsWith(`${new Date().getFullYear()}.01`) && (
  <span className="text-xs text-gray-400 dark:text-gray-500 font-normal">
    {item.ytd_base_date.slice(5)} ~
  </span>
)}
```

### 13.3 표시 예시

| 상황 | 표시 결과 |
|------|-----------|
| 정상 (1월 기준) | `5.25%` |
| fallback (예: 3월 15일 기준) | `5.25%` + 아래에 `03.15 ~` (회색 소자) |

---

## 15. BUG-08/09 수정 구현 결과 (2026-02-27)

### 15.1 FIX-08 — Phase 4에서 ETF 티커 제외

**파일**: `backend/app/services/catalog_data_collector.py`
**함수**: `_update_stock_prices`

Phase 4의 `sise_market_sum` 수집 결과(`price_map`)에 KOSPI 상장 ETF가 포함되어, Phase 1~3에서 올바르게 저장된 `weekly_return`이 0.0으로 덮어써지는 문제를 수정했다. Step 4+5 루프 진입 전에 DB에서 ETF 티커 목록을 조회하여 `price_map`에서 제외한다.

```python
# BEFORE
price_map = {s["ticker"]: s for s in kospi_stocks + kosdaq_stocks}

# AFTER
price_map = {s["ticker"]: s for s in kospi_stocks + kosdaq_stocks}
# DB에서 ETF 티커 조회 후 price_map에서 제외
etf_tickers = {row["ticker"] for row in cursor.execute("SELECT ticker FROM stock_catalog WHERE market = 'ETF'")}
price_map = {t: s for t, s in price_map.items() if t not in etf_tickers}
```

---

### 15.2 FIX-09 — 주간수익률 공식 통일 (5거래일 전 종가 기준)

주간수익률 공식을 **(현재가 - 5거래일 전 종가) / 5거래일 전 종가 * 100**으로 통일했다.

**파일 1**: `backend/app/services/catalog_data_collector.py` (`_fetch_supply_data`)

```python
# BEFORE: 4거래일 전 (0-indexed index 4)
weekly_return = calc_ret(current_val, prices_with_date[4][1] if len(prices_with_date) >= 5 else None)

# AFTER: 5거래일 전 (0-indexed index 5)
weekly_return = calc_ret(current_val, prices_with_date[5][1] if len(prices_with_date) >= 6 else None)
```

**파일 2**: `backend/app/routers/etfs.py` (배치 요약 엔드포인트)

```python
# BEFORE: 이번 주 월요일 대비 (캘린더 주 방식)
week_start = end_date - timedelta(days=end_date.weekday())
week_prices = [p for p in prices if p.date >= week_start]
summary.weekly_return = ((week_prices[0].close_price - week_prices[-1].close_price) / week_prices[-1].close_price) * 100

# AFTER: DB 가격 히스토리에서 5거래일 전 종가 사용
if len(prices) >= 6:
    current_price = prices[0].close_price
    base_price = prices[5].close_price
    summary.weekly_return = ((current_price - base_price) / base_price) * 100
```

---

### 15.3 수정 완료 요약

| 수정 ID | 버그 등급 | 파일 | 상태 |
|---------|-----------|------|------|
| FIX-08 | CRITICAL | `catalog_data_collector.py` | ✅ 완료 |
| FIX-09 | HIGH | `catalog_data_collector.py`, `etfs.py` | ✅ 완료 |

