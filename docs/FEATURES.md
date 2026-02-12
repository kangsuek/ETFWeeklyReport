# 제공 기능

ETF Weekly Report의 백엔드 API와 프론트엔드 기능을 정리한 문서입니다.

## 목차
- [백엔드 API](#백엔드-api) — ETF, 뉴스, 데이터, 설정, 알림, 스크리닝, 시뮬레이션
- [프론트엔드 기능](#프론트엔드-기능) — 대시보드, 상세, 비교, 포트폴리오, 종목 발굴, 시뮬레이션, 알림, 설정
- [데이터 수집](#데이터-수집)
- [캐시 및 성능 최적화](#캐시-및-성능-최적화)

---

## 백엔드 API

### 1. ETF/주식 종목 관리 (`/api/etfs`)

#### 1.1 종목 조회
- **GET `/api/etfs`** - 전체 종목 목록 조회
  - 등록된 모든 ETF·주식 종목 반환 (종목 수는 설정에 따라 가변)
  - 캐시: 5분 (정적 데이터)

- **GET `/api/etfs/{ticker}`** - 특정 종목 상세 정보
  - 종목 코드, 이름, 타입(ETF/STOCK), 테마, 매입일, 매입가, 수량, 검색 키워드, 관련 키워드
  - 캐시: 5분 (정적 데이터)

#### 1.2 가격 데이터
- **GET `/api/etfs/{ticker}/prices`** - 가격 데이터 조회
  - 시가, 고가, 저가, 종가, 거래량, 일간 등락률
  - 쿼리: `start_date`, `end_date`, `days`
  - 자동 수집 지원: 데이터 부족 시 네이버 금융에서 수집
  - 캐시: 30초

- **POST `/api/etfs/{ticker}/collect`** - 가격·매매동향 수집 트리거
  - 네이버 금융에서 수동 수집
  - 쿼리: `days` (기본값: 10일)
  - API Key 권장

#### 1.3 투자자별 매매동향
- **GET `/api/etfs/{ticker}/trading-flow`** - 매매동향 조회
  - 개인, 기관, 외국인 순매수
  - 쿼리: `start_date`, `end_date`
  - 자동 수집 지원
  - 캐시: 30초

- **POST `/api/etfs/{ticker}/collect-trading-flow`** - 매매동향 수집
  - 쿼리: `days` (1–90일, 기본값: 10일)
  - API Key 권장

#### 1.4 분봉(인트라데이)
- **GET `/api/etfs/{ticker}/intraday`** - 분봉 데이터 조회
  - 쿼리: `target_date`, `auto_collect`, `force_refresh`
  - 캐시: 30초

- **POST `/api/etfs/{ticker}/collect-intraday`** - 분봉 수집
  - 쿼리: `pages` (수집할 페이지 수)
  - API Key 권장

#### 1.5 종목 지표
- **GET `/api/etfs/{ticker}/metrics`** - 주요 지표 조회
  - 수익률 (1주, 1개월, YTD), 연환산 변동성, MDD, 샤프 비율 등
  - 캐시: 1분

#### 1.6 종목 인사이트
- **GET `/api/etfs/{ticker}/insights`** - 종목 인사이트 조회
  - 쿼리: `period` (1w, 1m, 3m, 6m, 1y, 기본값: 1m)
  - 투자 전략(단기/중기/장기), 종합 추천, 핵심 포인트, 리스크 요약
  - 캐시: 1분

#### 1.7 종목 비교
- **GET `/api/etfs/compare`** - 여러 종목 비교
  - 쿼리: `tickers` (2–6개, 쉼표 구분), `start_date`, `end_date`
  - 정규화 가격(시작일=100), 종목별 통계, 상관관계 행렬
  - 캐시: 1분

#### 1.8 배치 요약
- **POST `/api/etfs/batch-summary`** - 여러 종목 요약 일괄 조회
  - Body: `tickers`, `price_days`, `news_limit`
  - 종목별 최신 가격, 차트용 가격, 매매동향, 뉴스 반환 (N+1 최적화)
  - 캐시: 30초

### 2. 뉴스 (`/api/news`)

- **GET `/api/news/{ticker}`** - 종목별 뉴스 조회
  - 쿼리: `start_date`, `end_date`
  - 제목, URL, 출처, 날짜, 관련도 점수
  - 캐시: 1분

- **POST `/api/news/{ticker}/collect`** - 뉴스 수집
  - 네이버 검색 API 활용, 쿼리: `days` (1–30일, 기본값: 7일)
  - API Key 권장

### 3. 데이터 수집·상태 (`/api/data`)

#### 3.1 일괄 수집
- **POST `/api/data/collect-all`** - 전체 종목 일괄 수집
  - 쿼리: `days` (기본값: 1일, 최대: 365일)
  - 가격, 매매동향, 뉴스 수집
  - API Key 필요

- **POST `/api/data/backfill`** - 히스토리 백필
  - 쿼리: `days` (기본값: 90일, 최대: 365일)
  - API Key 필요

#### 3.2 상태 조회
- **GET `/api/data/status`** - 종목별 수집 상태
  - 최근 데이터 개수, 최신 날짜 등
  - 캐시: 10초

- **GET `/api/data/scheduler-status`** - 스케줄러 상태
  - 실행 여부, 마지막 수집 시각
  - 캐시: 10초

- **GET `/api/data/stats`** - DB 통계
  - 테이블별 레코드 수, DB 크기, 마지막 수집 시각
  - 캐시: 1분

#### 3.3 캐시 관리
- **GET `/api/data/cache/stats`** - 캐시 통계 (히트율, 미스율, 크기)
- **DELETE `/api/data/cache/clear`** - 캐시 전체 삭제 (API Key 필요)

#### 3.4 데이터베이스 관리
- **DELETE `/api/data/reset`** - DB 초기화 (위험)
  - 삭제: `prices`, `news`, `trading_flow`, `collection_status`, `intraday_prices`
  - 유지: `etfs`, `stock_catalog`, `alert_rules`, `alert_history`
  - API Key 필요

### 4. 설정·종목 관리 (`/api/settings`)

#### 4.1 종목 CRUD
- **GET `/api/settings/stocks`** - 종목 목록 조회 (stocks.json 기반)
- **POST `/api/settings/stocks`** - 종목 추가
  - Body: `ticker`, `name`, `type`, `theme`, `purchase_date`, `purchase_price`, `quantity`, `search_keyword`, `relevance_keywords`
  - stocks.json 및 DB 동기화
  - API Key 필요

- **PUT `/api/settings/stocks/{ticker}`** - 종목 수정 (부분 업데이트)
  - API Key 필요

- **DELETE `/api/settings/stocks/{ticker}`** - 종목 삭제
  - Cascade: 해당 종목 가격, 뉴스, 매매동향 등 삭제
  - API Key 필요

- **POST `/api/settings/stocks/reorder`** - 종목 순서 변경
  - Body: `tickers` 배열
  - API Key 필요

#### 4.2 검증·검색
- **GET `/api/settings/stocks/{ticker}/validate`** - 티커 검증
  - 네이버 금융 스크래핑 후 stocks 형식 반환

- **GET `/api/settings/stocks/search`** - 종목 검색 (자동완성)
  - 쿼리: `q` (최소 2자), `type` (STOCK/ETF/ALL)
  - `stock_catalog` 기반, 최대 20건

#### 4.3 종목 카탈로그
- **POST `/api/settings/ticker-catalog/collect`** - 전체 종목 목록 수집
  - 코스피, 코스닥, ETF → `stock_catalog` 저장
  - API Key 필요

### 5. 알림 (`/api/alerts`)

#### 5.1 알림 규칙 CRUD
- **GET `/api/alerts/{ticker}`** - 종목별 알림 규칙 목록
  - 쿼리: `active_only` (bool, 기본 true)
  - 활성/전체 규칙 조회

- **POST `/api/alerts/`** - 알림 규칙 생성
  - Body: `ticker`, `alert_type` (buy/sell/price_change/trading_signal), `direction` (above/below/both), `target_price`, `memo`
  - alert_type별 유효성 검증 (buy/sell: 목표가 > 0, price_change: 0~100%)

- **PUT `/api/alerts/{rule_id}`** - 알림 규칙 수정
  - 부분 업데이트: `alert_type`, `direction`, `target_price`, `memo`, `is_active`

- **DELETE `/api/alerts/{rule_id}`** - 알림 규칙 삭제
  - 관련 `alert_history` 레코드도 함께 삭제

#### 5.2 알림 트리거·이력
- **POST `/api/alerts/trigger`** - 알림 트리거 기록
  - Body: `rule_id`, `ticker`, `alert_type`, `message`
  - 프론트엔드에서 감지한 알림을 히스토리에 저장

- **GET `/api/alerts/history/{ticker}`** - 종목별 알림 이력
  - 쿼리: `limit` (1~100, 기본 20)
  - 최신순 정렬

### 6. 종목 발굴 · 스크리닝 (`/api/screening`)

#### 6.1 조건 검색
- **GET `/api/screening`** - 조건 기반 종목 검색
  - 쿼리: `q`(검색어), `type`(ETF/STOCK/ALL), `sector`, `min_weekly_return`, `max_weekly_return`, `foreign_net_positive`, `institutional_net_positive`, `sort_by`, `sort_dir`, `page`, `page_size`
  - `stock_catalog` 테이블 기반, 캐시: 60초
  - 응답: `items`, `total`, `page`, `page_size`

#### 6.2 테마·추천
- **GET `/api/screening/themes`** - 섹터/테마별 그룹
  - 섹터별 종목 수, 평균 주간수익률, top 3 종목
  - 캐시: 60초

- **GET `/api/screening/recommendations`** - 추천 프리셋
  - 쿼리: `limit` (1~10, 기본 5)
  - 주간 상위, 외국인 매수, 기관 매수, 거래량 상위, 주간 하락 상위
  - 캐시: 60초

#### 6.3 데이터 수집
- **POST `/api/screening/collect-data`** - 카탈로그 데이터 수집 시작
  - 백그라운드 실행, 중복 실행 방지
  - `stock_catalog`에 가격·수급·주간수익률 업데이트

- **GET `/api/screening/collect-progress`** - 수집 진행률
  - status: idle / in_progress / completed / cancelled / error
  - percent, message 포함

- **POST `/api/screening/cancel-collect`** - 수집 중지 요청

### 7. 시뮬레이션 (`/api/simulation`)

#### 7.1 일시 투자
- **POST `/api/simulation/lump-sum`** - 일시 투자 시뮬레이션
  - Body: `ticker`, `buy_date`, `amount`
  - 응답: 매수 주수, 잔여금, 현재 평가액, 수익률, 최대 수익/손실, 가격 시리즈
  - 자동 수집 지원, 캐시: 5분

#### 7.2 적립식(DCA)
- **POST `/api/simulation/dca`** - 적립식 투자 시뮬레이션
  - Body: `ticker`, `monthly_amount`, `start_date`, `end_date`, `buy_day`(1~28)
  - 응답: 총 투자금, 평가액, 평균 매수가, 총 주수, 월별 상세(매수가·주수·누적 평가액·수익률)
  - 미투자 잔액 누적 반영, 캐시: 5분

#### 7.3 포트폴리오
- **POST `/api/simulation/portfolio`** - 포트폴리오 시뮬레이션
  - Body: `holdings`(ticker+weight 배열, 비중 합계 1.0), `amount`, `start_date`, `end_date`
  - 응답: 종목별 결과(배정금·매수가·주수·현재가·수익률), 일별 포트폴리오 가치 시리즈
  - 중복 티커 검증, forward-fill 적용, 캐시: 5분

### 8. 시스템

- **GET `/api/health`** - 헬스 체크

---

## 프론트엔드 기능

### 1. 대시보드 (`/`)

#### 기본 기능
- 등록 종목 카드 그리드 + **히트맵** (PortfolioHeatmap)
- 히트맵: 종목별 종가·일간 변동률·주간 수익률, 투자/관심 구분(테두리·크기)
- 종목별 최신 가격, 등락률, 거래량, 주간 수익률 미니 차트
- 최근 뉴스 미리보기, 최근 매매동향(개인/기관/외국인)

#### 정렬 및 카드 순서
- 정렬: 설정 순서, 타입, 이름, 테마, 사용자 지정 순서
- 정렬 방향: 오름차순/내림차순
- 사용자 지정 순서: 드래그로 카드 순서 변경 후 설정에 저장(cardOrder)

#### 자동 갱신
- 자동 갱신 토글 및 간격 설정(30초/1분/5분/10분)
- 수동 새로고침 버튼

#### 데이터·UI
- 배치 API(batch-summary)로 N+1 최적화
- 스켈레톤 로딩, 에러 바운더리
- 오늘 날짜, 마지막 수집 시간, 화면 업데이트 시간 표시

### 2. 종목 상세 (`/etf/:ticker`)

#### 기본 정보
- 종목명, 티커, 타입, 테마
- 매입일·매입가·보유 수량, 매입 대비 수익률·평가 금액(입력된 경우)

#### 인사이트
- **StrategySummary**: 단기/중기/장기 투자 의견, 종합 추천, 핵심 포인트, 리스크 요약(간소화)
- **InsightSummary**: API 인사이트 기반 요약

#### 날짜 범위
- 프리셋: 7일, 1개월, 3개월 / 커스텀 날짜
- 설정에서 기본값(7D/1M/3M) 변경 가능

#### 통계·차트
- **StatsSummary**: 기간 수익률, 연환산 수익률, 최대/최소 가격, 평균 거래량, 변동성, MDD, 샤프 비율
- **PriceChart**: 캔들스틱(시고저종), 거래량 토글, 반응형, 스크롤 동기화
- **TradingFlowChart**: 개인/기관/외국인 순매수 막대 차트, 가격 차트와 스크롤 동기화
- **IntradayChart**: 분봉 차트(당일/지정일)
- 고급 분석: RSI, MACD, 지지/저항 (토글)

#### 테이블·뉴스
- **PriceTable**: 일자, 시가, 고가, 저가, 종가, 거래량, 등락률, 페이지네이션·정렬
- **NewsTimeline**: 최근 뉴스, 제목·출처·URL(새 탭)

#### 로딩·에러
- 스켈레톤, 에러 폴백, 재시도, 데이터 부족 시 수집 안내

### 3. 종목 비교 (`/compare`)

- **TickerSelector**: 드롭다운 멀티 셀렉트, 2–6개, 종목별 색상
- 날짜 범위: 프리셋(7일/1개월/3개월), 커스텀
- **NormalizedPriceChart**: 시작일=100 정규화 라인 차트, 툴팁
- **ComparisonTable**: 수익률, 연환산 수익률, 변동성, MDD, 샤프, 데이터 개수, 색상 코딩
- 상관관계 행렬(히트맵)

### 4. 포트폴리오 (`/portfolio`)

- **투자/관심 분류**: 매입가·수량이 있는 종목은 투자, 없으면 관심만
- **PortfolioSummaryCards**: 총 투자금, 평가금, 수익률 등 요약 카드
- **AllocationPieChart**: 종목별 비중 파이 차트
- **PortfolioTrendChart**: 일별 포트폴리오 추이
- **ContributionTable**: 종목별 기여도 테이블
- **PortfolioAnalysisReport**: 분석 리포트 토글

### 5. 종목 발굴 (`/screening`)

#### 조건 검색 탭
- **ScreeningFilters**: 검색어, 타입(ETF/STOCK/ALL), 섹터, 주간수익률 범위, 외국인/기관 순매수 필터
- **ScreeningTable**: 테이블 뷰 — 종목명, 현재가, 등락률, 거래량, 주간수익률, 외국인, 기관 컬럼 정렬, 페이지네이션
- **ScreeningHeatmap**: 히트맵 뷰 — Treemap(거래량=크기, 주간수익률=색상), 등록 종목 하이라이트
- 뷰 모드 토글(테이블/히트맵), 정렬 드롭다운

#### 테마 탐색 탭
- **ThemeExplorer**: 섹터별 카드(평균 수익률, 종목 수), top 3 종목, 클릭 시 조건 검색 연동

#### 데이터 수집
- 수집 버튼 + 진행률 배너(퍼센트 바, 메시지), 중지 버튼
- 페이지 진입 시 수집 상태 자동 확인, 완료 시 Toast + 데이터 갱신

### 6. 시뮬레이션 (`/simulation`)

3탭 구성 — 일시 투자 / 적립식 투자 / 포트폴리오

#### 일시 투자 (LumpSumSimulation)
- 폼: 종목 선택, 매수일, 투자금(3자리 콤마)
- 결과: 투자금·평가액·수익률·매수 주수 카드, 최대 수익/손실, 평가액 추이 LineChart(투자금 기준선)

#### 적립식 투자 (DCASimulation)
- 폼: 종목, 월 투자금(콤마), 매수일(1~28), 시작일, 종료일
- 결과: 총 투자금·평가액·수익률·평균 매수가·총 주수 카드, 누적 투자금 vs 평가액 AreaChart, 월별 매수 내역 테이블

#### 포트폴리오 (PortfolioSimulation)
- 폼: 동적 종목 추가/삭제, 비중(%) 입력, 균등 배분, 비중 합계 검증(100%), 중복 종목 방지
- 결과: 투자금·평가액·수익률 카드, 종목별 결과 테이블, 포트폴리오 가치 추이 LineChart

### 7. 알림 (`/alerts`)

- 종목별 목표가 알림 규칙 설정 (상한/하한)
- 알림 타입: 매수(buy), 매도(sell), 급등급락(price_change), 매매시그널(trading_signal)
- 알림 이력 조회
- AlertContext에서 가격 데이터와 규칙 비교, 트리거 시 Toast + 서버 기록

### 8. 설정 (`/settings`)

#### 일반 설정 (GeneralSettingsPanel)
- **테마**: 라이트 / 다크 / 시스템 설정 따르기
- **기본 날짜 범위**: 7일 / 1개월 / 3개월
- **자동 갱신**: 활성화·비활성화, 간격(30초/1분/5분/10분)
- **표시**: 거래량 차트 표시, 매매동향 차트 표시
- 기본값으로 초기화 버튼

#### 종목 관리 (TickerManagementPanel)
- 종목 목록 테이블(티커, 이름, 타입, 테마, 매입가, 수량 등)
- 종목 추가 폼: 티커 검증(네이버 금융), 자동완성(search), 필수: 티커·이름·타입·테마, 선택: 매입일·매입 평균 금액·수량·검색 키워드·관련 키워드
- 종목 수정(인라인), 종목 삭제(확인 모달)
- 종목 카탈로그 수집 버튼

#### 데이터 관리 (DataManagementPanel)
- 전체 수집, 백필 버튼
- DB 통계, 캐시 통계, 캐시 클리어, DB 초기화(위험)

#### 저장
- 설정은 LocalStorage 저장, 실시간 반영

### 9. 공통 기능

#### 레이아웃
- 반응형(모바일·태블릿·데스크탑), 헤더·푸터, 다크 모드

#### 상태·캐시
- TanStack Query(서버 상태), SettingsContext·ToastContext·AlertContext, LocalStorage(설정)

#### UI/UX
- 로딩(스피너·스켈레톤), 에러 바운더리, 토스트, 모달·툴팁

#### 성능
- Lazy Loading(페이지), Code Splitting(Vite), 메모이제이션(useMemo, useCallback)

---

## 데이터 수집

### 자동 수집(스케줄러)
- **실행**: 평일 15:50 (KST) 장 마감 후
- **대상**: 등록된 모든 종목
- **내용**: 당일 가격, 매매동향
- **재시도**: 실패 시 5분 후 재시도(최대 3회)

### 수동 수집
- **POST `/api/data/collect-all`**: 1–365일(기본 1일), API Key 필요
- **POST `/api/data/backfill`**: 히스토리(기본 90일), API Key 필요

### 자동 수집 지원(온디맨드)
- 가격·매매동향 요청 시 구간 데이터 없으면 자동 수집
- 분봉: `intraday` 요청 시 `auto_collect` 옵션으로 수집 가능

### 데이터 소스
- **네이버 금융**: 가격, 매매동향, 분봉
- **네이버 검색 API**: 뉴스

---

## 캐시 및 성능 최적화

### 백엔드 캐시
- 메모리 LRU 캐시
- TTL: 정적(5분), 가격·매매동향·배치(30초), 뉴스·지표·인사이트(1분), 상태(10초)
- 수집 후 관련 캐시 무효화
- `/api/data/cache/stats`로 모니터링

### 프론트엔드
- TanStack Query: staleTime/gcTime 설정, 리페치 전략
- 배치 API로 N+1 방지(대시보드·포트폴리오)

### Rate Limiting
- 읽기 전용·기본·수집·검색·위험 작업별 제한, 429 반환

---

## 보안

- **API Key**: 수집·설정 변경·DB 초기화·캐시 삭제 등에서 `X-API-Key` 헤더 사용, 환경 변수 `API_KEY`
- **CORS**: 허용 Origin 설정, Credentials·메서드 허용
- **Rate Limiting**: IP 기반, 엔드포인트별 제한

---

## 테스트

- **백엔드**: pytest, 라우터·서비스·유틸리티
- **프론트엔드**: Vitest + React Testing Library, 컴포넌트·유틸·컨텍스트
- **E2E**: 준비 중

---

## 배포

- **백엔드**: FastAPI, Uvicorn, SQLite(개발)/PostgreSQL(프로덕션), APScheduler
- **프론트엔드**: Vite 빌드, 정적 파일 서빙, `.env` 환경 변수

---

## 문서

- [README.md](../README.md) - 프로젝트 개요
- [CLAUDE.md](../CLAUDE.md) - 문서 인덱스
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 시스템 아키텍처
- [API_SPECIFICATION.md](./API_SPECIFICATION.md) - API 명세
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - DB 스키마
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - 개발 가이드
- [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) - 파일 구조
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - 환경 설정·실행
- [INTRADAY.md](./INTRADAY.md) - 분봉 조회·수집
- [TECH_STACK.md](./TECH_STACK.md) - 기술 스택
- [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) - Render.com 배포
- [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) - 보안 체크리스트
