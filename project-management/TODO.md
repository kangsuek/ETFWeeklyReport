# TODO List

> **⚠️ 중요**: 각 Phase는 테스트 100% 완료 후 다음 단계로 진행합니다.  
> 자세한 완료 기준은 **[Definition of Done](../docs/DEFINITION_OF_DONE.md)** 참조

---

## ✅ 완료된 Phase 요약

### Phase 1: Backend Core (완료 - 2025-11-07)
- ✅ 61개 테스트 통과, 커버리지 82%
- ✅ API 5개 엔드포인트 (ETF 조회, 가격 수집)
- ✅ Naver Finance 스크래핑 (6개 종목)

### Phase 2: Data Collection Complete (완료 - 2025-11-08)
- ✅ 196개 테스트 통과, 커버리지 89%
- ✅ API 13개 엔드포인트 (ETF, News, Trading Flow, Reports)
- ✅ APScheduler 자동 수집, 네이버 뉴스 API 통합
- ✅ 데이터 완전성 100점 (6/6 종목)

### Phase 3: Frontend Foundation (완료 - 2025-11-09)
- ✅ 6개 종목 대시보드, React Query 연동
- ✅ 반응형 디자인, 성능 최적화 (88.73 kB gzip)
- ✅ 테스트 환경 구축 (Vitest, RTL, MSW)

### Phase 4: Charts & Visualization (완료 - 2025-11-11)
- ✅ 186개 테스트 통과, 커버리지 82.52%
- ✅ 가격 차트 (LineChart + BarChart), 매매 동향 차트 (StackedBarChart)
- ✅ 날짜 범위 선택기, 뉴스 타임라인
- ✅ 차트 반응형 처리, 성능 최적화 (145.57 kB gzip)
- ✅ 차트 X축 길이 통일, 스크롤 동기화

### Phase 4.5 Step 1: 백엔드 종목 관리 API ✅ (완료 - 2025-11-11)
- ✅ Task 1.1 완료: stocks.json 관리 유틸리티
- ✅ Task 1.2 완료: 종목 추가/수정/삭제 API 엔드포인트
- ✅ Task 1.3 완료: 네이버 금융 종목 정보 스크래핑
- ✅ Task 1.4 완료: 테스트 작성

### Phase 4.5 Step 2: 프론트엔드 Settings 페이지 ✅ (완료 - 2025-11-12)
- ✅ Task 2.1 완료: Settings 페이지 라우팅 (Settings.jsx, App.jsx, Header)
- ✅ Task 2.2 완료: 종목 관리 컴포넌트 (TickerManagementPanel, TickerForm, TickerDeleteConfirm)
- ✅ Task 2.3 완료: API 연동 (settingsApi, React Query mutations)
- ✅ Task 2.4 완료: 테스트 작성 (26개 테스트 통과, 81.98% 커버리지)

> **상세 달성 내용**: [PROGRESS.md](./PROGRESS.md) 참조

---

## ✅ Phase 4: Charts & Visualization (완료 - 2025-11-11)

**목표**: 인터랙티브 차트 구현 및 ETF Detail 페이지 완성

**주요 달성 사항**:
- ✅ 가격 차트 (LineChart + BarChart), 매매 동향 차트 (StackedBarChart)
- ✅ 날짜 범위 선택기 (7일/1개월/3개월/커스텀)
- ✅ ETF Detail 페이지 완성 (차트 + 정보 + 뉴스)
- ✅ 차트 반응형 처리 및 성능 최적화
- ✅ 186개 테스트 통과, 커버리지 82.52%
- ✅ 프로덕션 빌드 성공 (145.57 kB gzip)

> **상세 작업 내역**: [PROGRESS.md](./PROGRESS.md) 참조

---

#### Step 6: Phase 3에서 연기된 컴포넌트 테스트 작성 ✅ (완료 - 2025-11-11)

**목표**: Phase 3 Step 6에서 연기된 컴포넌트 테스트를 완료하여 전체 커버리지 70% 달성

**달성 결과**:
- ✅ 테스트 커버리지 **87.37%** 달성 (목표 70% 대비 +17.37%p)
- ✅ 총 **219개 테스트** 통과 (3개 스킵)
- ✅ 12개 테스트 파일 작성 완료

**주요 개선 사항**:
- ChartSkeleton: 0% → 100% (7개 테스트 추가)
- chartUtils: 30% → 100% (26개 테스트 추가)
- 전체 커버리지: 82.52% → 87.37% (+4.85%p)

- [x] 테스트 환경 확인
  - [x] Vitest 설정 확인 (vitest.config.js)
  - [x] React Testing Library 설정 확인
  - [x] MSW (Mock Service Worker) 설정 확인

- [x] ETFCard 컴포넌트 테스트 확장 (15개 테스트)
  - [x] 기본 렌더링 테스트
  - [x] 가격 데이터 표시 테스트
  - [x] 등락률 색상 테스트 (양수: 빨강, 음수: 파랑)
  - [x] 거래량 포맷팅 테스트 (K/M 단위)
  - [x] 뉴스 미리보기 테스트
  - [x] 클릭 이벤트 테스트 (Link 이동)
  - [x] 로딩 상태 테스트 (Skeleton)
  - [x] 에러 상태 테스트

- [x] Dashboard 페이지 테스트 확장 (9개 테스트)
  - [x] 6개 종목 렌더링 테스트
  - [x] 정렬 기능 테스트 (현재 구현 없음 - 스킵)
  - [x] 검색 기능 테스트 (현재 구현 없음 - 스킵)
  - [x] 새로고침 버튼 테스트
  - [x] 자동 새로고침 체크박스 테스트
  - [x] 로딩 상태 테스트
  - [x] 에러 상태 테스트
  - [x] 빈 데이터 상태 테스트

- [x] Header 컴포넌트 테스트 (10개 테스트)
  - [x] 렌더링 테스트
  - [x] 네비게이션 링크 테스트
  - [x] 모바일 햄버거 메뉴 테스트 (토글)
  - [x] Active 링크 하이라이팅 테스트

- [x] Footer 컴포넌트 테스트 (9개 테스트)
  - [x] 렌더링 테스트
  - [x] 저작권 정보 표시 테스트
  - [x] 업데이트 시간 표시 테스트
  - [x] GitHub 링크 테스트

- [x] API 서비스 테스트 확장 (18개 테스트)
  - [x] etfApi.getAll() 테스트
  - [x] etfApi.getDetail() 테스트
  - [x] etfApi.getPrices() 테스트
  - [x] etfApi.getTradingFlow() 테스트
  - [x] newsApi.getByTicker() 테스트
  - [x] 에러 핸들링 테스트 (404, 500)
  - [x] 네트워크 에러 테스트

- [x] MSW 핸들러 작성 (handlers.js)
  - [x] GET /api/etfs - Mock 6개 종목 응답
  - [x] GET /api/etfs/:ticker - Mock 종목 정보
  - [x] GET /api/etfs/:ticker/prices - Mock 가격 데이터
  - [x] GET /api/etfs/:ticker/trading-flow - Mock 매매 동향
  - [x] GET /api/news/:ticker - Mock 뉴스

- [x] 차트 관련 테스트 추가
  - [x] ChartSkeleton 테스트 (7개 테스트, 100% 커버리지)
  - [x] chartUtils 테스트 (26개 테스트, 100% 커버리지)
  - [x] PriceChart 테스트 (18개 테스트)
  - [x] TradingFlowChart 테스트 (23개 테스트)
  - [x] DateRangeSelector 테스트 (14개 테스트)

- [x] 테스트 커버리지 확인
  - [x] `npm run test:coverage` 실행
  - [x] 목표: 70% 이상 ✅ (87.37% 달성)
  - [x] 커버리지 낮은 파일 확인 및 테스트 추가

**Acceptance Criteria**:
- [x] 전체 컴포넌트 테스트 통과 (219개 통과, 3개 스킵)
- [x] 테스트 커버리지 70% 이상 ✅ (87.37%)
- [x] MSW 핸들러 정상 작동
- [ ] CI/CD 파이프라인 통과 (Phase 7에서 진행 예정)

---

## 🟡 Phase 4.5: Settings & Ticker Management (신규 추가)

**목표**: 환경설정 메뉴 및 종목 관리 기능 구현 (`backend/config/stocks.json` 기반)

**예상 소요 시간**: 약 4-5시간

**핵심 개념**:
- **Single Source of Truth**: `backend/config/stocks.json` 파일이 종목 정보의 유일한 소스
- 데이터베이스(`etfs` 테이블)는 `stocks.json`에서 자동 동기화
- Settings UI는 `stocks.json` 파일을 읽고 쓰는 방식

**stocks.json 스키마**:
```json
{
  "ticker_code": {
    "name": "종목명 (필수)",
    "type": "ETF | STOCK (필수)",
    "theme": "테마/섹터 (필수)",
    "launch_date": "YYYY-MM-DD (ETF만 필수, STOCK은 null)",
    "expense_ratio": "0.0050 (ETF만 필수, STOCK은 null)",
    "search_keyword": "뉴스 검색 키워드",
    "relevance_keywords": ["키워드1", "키워드2", ...]
  }
}
```

**데이터 흐름** (개선됨):
```
1. 종목 추가 (자동 스크래핑)
Settings UI → 티커 입력 (005930)
    ↓ "네이버에서 자동 입력" 버튼 클릭
    ↓ GET /api/settings/stocks/{ticker}/validate ⬅ 변경됨
Backend → ticker_scraper.scrape_ticker_info()
    ↓ 네이버 금융 스크래핑
    ↓ stocks.json 형식 반환 (검증만, 저장 안 함)
Settings UI → 폼 자동 채움 → 사용자 확인/수정 → 저장
    ↓ POST /api/settings/stocks ⬅ 변경됨
Backend (settings.py router)
    ↓ 1. validate_stock_data() - 데이터 검증
    ↓ 2. stocks_manager.save_stocks() - stocks.json 저장 (원자적 쓰기 + 백업)
    ↓ 3. sync_stocks_to_db() - DB INSERT OR REPLACE
    ↓ 4. Config.reload_stock_config() - 캐시 갱신 ⬅ 중요!
Response: 201 Created
    ↓
Settings UI → React Query 캐시 무효화 (queryClient.invalidateQueries(['etfs']))
Dashboard → 자동 재조회 → 새 종목 표시

2. 종목 삭제 (CASCADE)
Settings UI → 삭제 버튼 클릭
    ↓ DELETE /api/settings/stocks/{ticker}
Backend
    ↓ 1. stocks.json에서 제거 + 백업
    ↓ 2. DB CASCADE 삭제 (prices, news, trading_flow)
    ↓ 3. Config.reload_stock_config() - 캐시 갱신
Response: { "deleted": { "prices": 150, "news": 20, ... } }
    ↓
Settings UI → 토스트 알림 → 캐시 무효화
Dashboard → 종목 사라짐

3. 서버 재시작 시
main.py startup event
    ↓ 1. init_db() - 테이블 생성
    ↓ 2. stocks_manager.sync_stocks_to_db() - stocks.json → DB 동기화 ⬅ 추가됨
    ↓ 3. Config.get_stock_config() - 캐시 로드
서버 준비 완료 (stocks.json이 항상 우선)
```

**개선 사항 요약**:
1. ✅ **API 경로 분리**: `/api/etfs` (조회) vs `/api/settings/stocks` (관리)
2. ✅ **Config 캐시 갱신**: 모든 CRUD 작업 후 `Config.reload_stock_config()` 호출
3. ✅ **원자적 파일 쓰기**: 임시 파일 → rename (데이터 손실 방지)
4. ✅ **CASCADE 삭제 통계**: 삭제된 레코드 수 반환
5. ✅ **서버 재시작 동기화**: startup event에서 자동 동기화

### Step 1: 백엔드 - 종목 관리 API 구현 ✅ (완료 - 2025-11-11)

**현재 진행 상황**:
- ✅ Task 1.1 완료: stocks.json 관리 유틸리티
- ✅ Task 1.2 완료: 종목 추가/수정/삭제 API 엔드포인트
- ✅ Task 1.3 완료: 네이버 금융 종목 정보 스크래핑
- ✅ Task 1.4 완료: 테스트 작성

#### Task 1.1: stocks.json 관리 유틸리티 ✅ (완료 - 2025-11-11)
- [x] `app/utils/stocks_manager.py` 유틸리티 생성
  - [x] `load_stocks()` - stocks.json 파일 읽기 (기존 `Config.get_stock_config()` 활용)
  - [x] `save_stocks(stocks_dict)` - stocks.json 파일 쓰기
    - [x] **자동 백업**: `stocks.json.backup.YYYYMMDD_HHMMSS` 형식
    - [x] **원자적 쓰기**: 임시 파일에 쓰고 rename (데이터 손실 방지)
    - [x] **JSON 포매팅**: indent=2, ensure_ascii=False (한글 유지)
  - [x] `validate_stock_data(stock_dict)` - 종목 데이터 검증
    - [x] 필수 필드 체크: ticker, name, type, theme
    - [x] 타입 검증: ETF는 launch_date, expense_ratio 필수
    - [x] 날짜 형식 검증: YYYY-MM-DD
  - [x] `sync_stocks_to_db()` - stocks.json → DB 동기화
    - [x] **기존 `init_db()` 로직 활용** (중복 방지)
    - [x] INSERT OR REPLACE 사용
    - [x] **Config 캐시 갱신**: `Config.reload_stock_config()` 호출
- [x] **서버 시작 시 자동 동기화** (`main.py`의 startup event)
  - [x] 기존 `init_db()` 다음에 `sync_stocks_to_db()` 호출

#### Task 1.2: 종목 추가/수정/삭제 API 엔드포인트 ✅ (완료 - 2025-11-11)

**⚠️ 중요 설계 결정**: `POST /api/etfs`를 `POST /api/settings/stocks`로 변경
- 이유: 기존 `GET /api/etfs`는 조회용, CRUD는 Settings 전용 엔드포인트로 분리
- `/api/settings/stocks` - 종목 관리 전용 (Create, Update, Delete)
- `/api/etfs` - 조회 전용 (Read only, 캐시 가능)

- [x] **새 라우터 추가**: `app/routers/settings.py`
- [x] `POST /api/settings/stocks` - 새 종목 추가
  - [x] Request Body: `{ ticker, name, type, theme, launch_date, expense_ratio, search_keyword, relevance_keywords }`
  - [x] 중복 티커 체크 (stocks.json, DB 모두)
  - [x] 데이터 검증 (Pydantic 모델)
  - [x] **stocks.json 파일에 추가** (stocks_manager.save_stocks 호출)
  - [x] **DB 동기화** (stocks_manager.sync_stocks_to_db)
  - [x] **Config 캐시 갱신** (Config.reload_stock_config)
  - [x] 응답: 생성된 종목 정보 반환
- [x] `PUT /api/settings/stocks/{ticker}` - 종목 정보 수정
  - [x] 존재하는 티커만 수정 가능 (404 반환)
  - [x] 부분 업데이트 지원 (PATCH 스타일)
  - [x] **stocks.json 파일 수정**
  - [x] **DB 동기화 + Config 캐시 갱신**
- [x] `DELETE /api/settings/stocks/{ticker}` - 종목 삭제
  - [x] **stocks.json 파일에서 제거**
  - [x] **DB CASCADE 삭제** (관련 prices, news, trading_flow 데이터)
    - [x] 삭제된 레코드 수 카운트
  - [x] **Config 캐시 갱신**
  - [x] 응답: 삭제된 데이터 통계 반환
    ```json
    {
      "ticker": "005930",
      "deleted": {
        "prices": 150,
        "news": 20,
        "trading_flow": 30
      }
    }
    ```

#### Task 1.3: 네이버 금융 종목 정보 스크래핑 ✅ (완료 - 2025-11-11)
- [x] `app/services/ticker_scraper.py` 유틸리티 생성
  - [x] `scrape_ticker_info(ticker: str)` - 네이버 금융에서 종목 정보 스크래핑
    - [x] **기본 정보 수집**:
      - [x] 종목명 (`title` 태그 또는 `.wrap_company h2`)
      - [x] 종목 타입 감지 (ETF/STOCK)
        - ETF: 종목명에 "ETF" 포함 또는 종목코드 길이 6자리
        - STOCK: 그 외
      - [x] 현재가, 시가총액 (선택사항)
    - [x] **테마/섹터 정보 수집** (가능한 경우):
      - [x] 종목 페이지의 "업종" 정보
      - [x] 종목 설명 텍스트에서 키워드 추출
    - [x] **ETF 전용 정보** (ETF인 경우):
      - [x] 상장일 (`launch_date`)
      - [x] 운용보수 (`expense_ratio`) - ETF 상세 페이지에서 수집
    - [x] **stocks.json 형식으로 자동 변환**
  - [x] `generate_keywords(name: str, theme: str)` - 키워드 자동 생성
    - [x] 종목명에서 핵심 키워드 추출
    - [x] 테마 기반 관련 키워드 생성

- [x] `GET /api/settings/stocks/{ticker}/validate` - 종목 코드 유효성 검증 API
  - [x] **중요**: `/api/etfs/{ticker}/validate`가 아닌 `/api/settings/stocks/{ticker}/validate`
  - [x] Naver Finance에서 실제 존재 여부 확인
  - [x] `ticker_scraper.scrape_ticker_info()` 호출
  - [x] **stocks.json 형식으로 반환** (바로 추가 가능)
  - [x] **에러 처리**:
    - [x] 404: 종목을 찾을 수 없음 (네이버 금융에 없음)
    - [x] 500: 스크래핑 실패 (네트워크 에러, 파싱 실패 등)
  - [ ] 예시 응답:
    ```json
    {
      "ticker": "005930",
      "name": "삼성전자",
      "type": "STOCK",
      "theme": "반도체/전자",
      "launch_date": null,
      "expense_ratio": null,
      "search_keyword": "삼성전자",
      "relevance_keywords": ["삼성전자", "반도체", "전자", "IT"]
    }
    ```

#### Task 1.4: 테스트 작성 ✅ (완료 - 2025-11-11)
- [x] `test_stocks_manager.py` - stocks.json 관리 유틸리티 테스트
  - [x] load/save 테스트 (임시 파일 사용)
  - [x] 동기화 테스트
  - [x] 백업 테스트
- [x] `test_ticker_scraper.py` - 스크래핑 유틸리티 테스트
  - [x] 실제 종목 스크래핑 테스트 (005930, 487240 등)
  - [x] 존재하지 않는 종목 테스트
  - [x] ETF/STOCK 타입 감지 테스트
  - [x] 키워드 생성 테스트
- [x] `test_settings_api.py` - CRUD 엔드포인트 테스트
  - [x] 종목 추가 테스트 (성공, 중복, 검증 실패)
  - [x] 종목 수정 테스트 (성공, 404)
  - [x] 종목 삭제 테스트 (성공, CASCADE)
  - [x] **stocks.json 파일 변경 확인**
- [x] 검증 API 테스트 (test_settings_api.py에 포함)
  - [x] 실제 종목 검증 테스트
  - [x] stocks.json 형식 반환 확인

**Acceptance Criteria**:
- [x] **네이버 금융 스크래핑** 정상 작동 (코드 구현 완료)
- [x] **stocks.json 형식 자동 생성** 정상 작동
- [x] stocks.json CRUD 정상 작동
- [x] DB 동기화 정상 작동
- [x] 모든 테스트 작성 완료
- [x] API 문서 자동 생성 (Swagger)

---

### Step 2: 프론트엔드 - Settings 페이지 구현 ✅ (완료 - 2025-11-12)

#### Task 2.1: Settings 페이지 라우팅 ✅ (완료)
- [x] `pages/Settings.jsx` 페이지 생성
- [x] App.jsx에 라우트 추가 (`/settings`)
- [x] Header에 Settings 링크 추가 (톱니바퀴 아이콘)

#### Task 2.2: 종목 관리 컴포넌트 ✅ (완료)
- [x] `TickerManagementPanel.jsx` 컴포넌트 생성
  - [x] 현재 종목 목록 테이블 (6개)
  - [x] 각 행: 티커, 이름, 타입, 테마, 편집/삭제 버튼
  - [x] "새 종목 추가" 버튼
  - [x] "stocks.json에서 불러오기" 표시
- [x] `TickerForm.jsx` 모달 컴포넌트 생성
  - [x] **stocks.json 형식 기반 폼 필드**:
    - [x] `ticker` (필수, 읽기 전용 - 수정 시)
    - [x] `name` (필수)
    - [x] `type` (ETF/STOCK 선택)
    - [x] `theme` (필수)
    - [x] `launch_date` (ETF만 필수, STOCK은 null)
    - [x] `expense_ratio` (ETF만 필수, STOCK은 null)
    - [x] `search_keyword` (뉴스 검색용)
    - [x] `relevance_keywords` (배열, 쉼표 구분 입력)
  - [x] **"네이버에서 자동 입력" 버튼** ⭐ 신규
    - [x] 티커 코드 입력 후 버튼 클릭 시
    - [x] `GET /api/settings/stocks/{ticker}/validate` API 호출
    - [x] 응답 데이터로 폼 자동 채우기
    - [x] 로딩 스피너 표시
    - [x] 에러 처리 (존재하지 않는 종목)
    - [x] "자동 입력된 정보를 확인하고 수정하세요" 안내 메시지
  - [x] 저장/취소 버튼
- [x] `TickerDeleteConfirm.jsx` 확인 모달
  - [x] "정말 삭제하시겠습니까?" 메시지
  - [x] **"stocks.json 및 관련 데이터가 삭제됩니다" 경고**
  - [x] 삭제 시 관련 데이터 수 표시

#### Task 2.3: API 연동 ✅ (완료)
- [x] `services/api.js`에 새 settingsApi 객체 추가
  - [x] `createStock()` - POST /api/settings/stocks
  - [x] `updateStock()` - PUT /api/settings/stocks/{ticker}
  - [x] `deleteStock()` - DELETE /api/settings/stocks/{ticker}
  - [x] `validateTicker()` - GET /api/settings/stocks/{ticker}/validate
- [x] React Query mutation 사용
  - [x] `useMutation` for create/update/delete
  - [x] **성공 시 캐시 무효화**: `queryClient.invalidateQueries(['etfs'])`
  - [x] **alert 알림**: 성공/실패 메시지
  - [x] **에러 처리**: 네트워크 에러, 중복 티커, 404 등

#### Task 2.4: 테스트 작성 ✅ (완료)
- [x] `Settings.test.jsx` - 페이지 렌더링 테스트 (3개 테스트)
- [x] `TickerManagementPanel.test.jsx` - 컴포넌트 테스트 (2개 테스트)
- [x] `TickerForm.test.jsx` - 폼 유효성 검증 테스트 (10개 테스트)
- [x] `TickerDeleteConfirm.test.jsx` - 삭제 확인 모달 테스트 (11개 테스트)
- [x] MSW 핸들러 추가 (handlers.js)
  - [x] POST /api/settings/stocks
  - [x] PUT /api/settings/stocks/{ticker}
  - [x] DELETE /api/settings/stocks/{ticker}
  - [x] GET /api/settings/stocks/{ticker}/validate

**Acceptance Criteria**:
- [x] Settings 페이지 정상 렌더링
- [x] **"네이버에서 자동 입력" 기능 정상 작동** ⭐
- [x] 종목 추가/수정/삭제 정상 작동
- [x] 티커 검증 기능 작동
- [x] 모든 테스트 통과 (26개 테스트)
- [x] 모바일 반응형 동작

**달성 결과**:
- ✅ 총 **26개 Settings 관련 테스트** 통과
- ✅ **81.98% 테스트 커버리지** 유지
- ✅ Settings 페이지 완전히 작동
- ✅ 모바일 반응형 UI 완성

---

### Step 3: 추가 환경설정 옵션 (선택사항) (약 0.5-1시간)

#### Task 3.1: 일반 설정 패널 (0.5시간)
- [ ] `GeneralSettingsPanel.jsx` 컴포넌트 생성
  - [ ] 자동 새로고침 간격 설정 (1분/5분/10분/꺼짐)
  - [ ] 기본 날짜 범위 설정 (7일/1개월/3개월)
  - [ ] 테마 설정 (라이트/다크 모드) - Phase 7로 연기 가능
  - [ ] LocalStorage에 저장

#### Task 3.2: 데이터 관리 패널 (선택사항)
- [ ] `DataManagementPanel.jsx` 컴포넌트 생성
  - [ ] 전체 데이터 수집 트리거 버튼
  - [ ] 데이터베이스 초기화 버튼 (위험)
  - [ ] 데이터 통계 표시 (총 가격 레코드 수, 뉴스 수 등)

**Acceptance Criteria**:
- [ ] 설정 저장 및 불러오기 정상 작동
- [ ] LocalStorage 사용

---

## Phase 4.5 최종 완료 기준 (Definition of Done)

### 기능 요구사항 ✅ (완료)
- [x] **네이버 금융 스크래핑 구현** (`ticker_scraper.py`) ⭐
  - [x] 종목 정보 자동 수집 (이름, 타입, 테마, 상장일, 운용보수)
  - [x] stocks.json 형식 자동 변환
  - [x] 키워드 자동 생성
- [x] **stocks.json 관리 유틸리티 구현** (`stocks_manager.py`)
- [x] 종목 추가/수정/삭제 API 구현 (stocks.json 기반)
- [x] stocks.json ↔ DB 자동 동기화
- [x] Settings 페이지 구현 (종목 관리)
- [x] 티커 검증 API (stocks.json 형식 반환)

### 테스트 요구사항 (필수) ✅ (완료)
- [x] **네이버 스크래핑 유틸리티 테스트** (실제 종목으로)
- [x] stocks.json 관리 유틸리티 테스트
- [x] 백엔드 CRUD API 테스트 (유닛 + 통합)
- [x] stocks.json 파일 변경 확인 테스트
- [x] 프론트엔드 컴포넌트 테스트 (26개 테스트)
- [x] **모든 테스트 100% 통과**
- [x] **테스트 커버리지 81.98% (목표 70% 초과달성)**

### 문서화 (일부 남음)
- [ ] API 명세서 업데이트 (API_SPECIFICATION.md)
  - [ ] **새 섹션 추가**: "Settings API" (종목 관리)
  - [ ] `POST /api/settings/stocks` - 종목 추가
  - [ ] `PUT /api/settings/stocks/{ticker}` - 종목 수정
  - [ ] `DELETE /api/settings/stocks/{ticker}` - 종목 삭제 (CASCADE 통계 포함)
  - [ ] `GET /api/settings/stocks/{ticker}/validate` - 스크래핑 검증
- [ ] stocks.json 형식 문서화
  - [ ] 주석 추가 (JSON 파일 상단)
  - [ ] 필드 설명 (name, type, theme 등)
  - [ ] ETF vs STOCK 차이점
- [ ] 아키텍처 문서 업데이트 (ARCHITECTURE.md)
  - [ ] stocks.json의 역할 (Single Source of Truth)
  - [ ] Config 캐시 메커니즘
  - [ ] 데이터 동기화 흐름도
- [x] 진행 상황 업데이트 (PROGRESS.md, TODO.md)

### 검증 ✅ (완료)
- [x] **네이버 스크래핑 수동 테스트** ⭐
  - [x] 티커 입력 → "네이버에서 자동 입력" 클릭
  - [x] 종목 정보 자동 채움 확인 (이름, 타입, 테마 등)
  - [x] ETF 정보 확인 (상장일, 운용보수)
  - [x] 키워드 자동 생성 확인
- [x] Settings 페이지 수동 테스트
- [x] 종목 추가 → stocks.json 업데이트 → 대시보드 반영 확인
- [x] 종목 수정 → stocks.json 업데이트 → DB 동기화 확인
- [x] 종목 삭제 → stocks.json 삭제 → 데이터 CASCADE 확인
- [x] 서버 재시작 시 stocks.json → DB 동기화 확인
- [x] 모바일 반응형 확인
- [ ] 프로덕션 빌드 성공

**Phase 4.5는 핵심 기능이 모두 완료되었습니다. 문서화 작업은 선택사항으로 Phase 5 진행 가능합니다.**

---

## 작업 우선순위

1. **High Priority** (필수)
   - **네이버 금융 스크래핑** (`ticker_scraper.py`) ⭐ 신규
   - 백엔드 CRUD API 구현 (stocks.json 기반)
   - 종목 관리 UI 구현
   - "네이버에서 자동 입력" 버튼 구현
   - 테스트 작성

2. **Medium Priority** (권장)
   - 키워드 자동 생성 로직
   - 일반 설정 패널 (자동 새로고침, 날짜 범위)

3. **Low Priority** (선택사항)
   - 다크 모드 (Phase 7로 연기)
   - 데이터 관리 패널

---

**예상 총 소요 시간**: 5-6시간 (스크래핑 기능 추가로 +1시간)
**목표 완료일**: 2025-11-12 (1일 작업 기준)

---

## 🟢 Phase 5: Detail & Comparison Pages (진행 중)

**목표**: 종목 상세 페이지 완성 및 비교 페이지 구현

**예상 소요 시간**: 약 8-10시간

### 현재 상태 분석

#### ✅ 이미 완료된 기능 (Phase 4)
- ✅ ETF Detail 페이지 기본 구조
- ✅ 가격 차트 (PriceChart) 통합
- ✅ 매매 동향 차트 (TradingFlowChart) 통합
- ✅ 날짜 범위 선택기
- ✅ 뉴스 타임라인
- ✅ 기본 정보 패널

#### 🔄 Phase 5에서 추가할 기능
- 🔄 Detail 페이지 강화 (일별 데이터 테이블, 통계)
- 🔄 Comparison 페이지 완성 (비교 테이블, 정규화 차트)
- 🔄 UI/UX 개선 (에러 바운더리, 토스트 알림)

---

### Step 1: Detail 페이지 강화 (약 3-4시간)

**목표**: 일별 데이터 테이블 및 통계 정보 추가

#### Task 1.1: 일별 데이터 테이블 컴포넌트 구현 (1.5시간)
- [ ] `PriceTable.jsx` 컴포넌트 생성
  - [ ] 일별 가격 데이터 테이블 (날짜, 시가, 고가, 저가, 종가, 거래량, 등락률)
  - [ ] 정렬 기능 (날짜, 종가, 거래량, 등락률)
  - [ ] 페이지네이션 (10/25/50/100 rows)
  - [ ] 반응형 테이블 (모바일: 카드 형태)
  - [ ] 등락률 색상 표시 (양수: 빨강, 음수: 파랑)
- [ ] ETFDetail 페이지에 테이블 통합

#### Task 1.2: 통계 요약 패널 구현 (1시간)
- [ ] `StatsSummary.jsx` 컴포넌트 생성
  - [ ] 기간 내 통계 (최고가, 최저가, 평균 거래량)
  - [ ] 수익률 (7일, 1개월, 3개월)
  - [ ] 변동성 (표준편차)
  - [ ] 샤프 비율 (선택사항)
- [ ] `utils/statistics.js` 유틸리티 함수 작성
  - [ ] `calculateReturns()` - 기간별 수익률 계산
  - [ ] `calculateVolatility()` - 변동성 계산
  - [ ] `calculateSharpeRatio()` - 샤프 비율 계산 (무위험 수익률 가정)

#### Task 1.3: 테스트 작성 (0.5-1시간)
- [ ] `PriceTable.test.jsx` - 테이블 렌더링, 정렬, 페이지네이션 테스트
- [ ] `StatsSummary.test.jsx` - 통계 계산 및 표시 테스트
- [ ] `utils/statistics.test.js` - 유틸리티 함수 유닛 테스트

**Acceptance Criteria**:
- [ ] 일별 데이터 테이블이 정상 표시됨
- [ ] 정렬 및 페이지네이션이 정상 작동함
- [ ] 통계 요약이 정확하게 계산됨
- [ ] 모든 테스트 통과 (목표 커버리지 70% 이상)
- [ ] 모바일 반응형 동작 확인

---

### Step 2: Comparison 페이지 구현 (약 4-5시간)

**목표**: 6개 종목 비교 기능 완성

#### Task 2.1: 백엔드 API 확인 및 수정 (0.5시간)
- [ ] `GET /api/etfs/compare` 엔드포인트 구현 여부 확인
- [ ] 없으면 간단한 구현 추가 (기존 가격 데이터 조회 활용)
- [ ] 프론트엔드 API 서비스 함수 추가 (`etfApi.compare()`)

#### Task 2.2: 정규화된 가격 차트 구현 (1.5시간)
- [ ] `NormalizedPriceChart.jsx` 컴포넌트 생성
  - [ ] 6개 종목 가격을 100 기준으로 정규화
  - [ ] 다중 라인 차트 (Recharts LineChart)
  - [ ] 범례 (ticker별 색상 구분)
  - [ ] 툴팁 (날짜, 정규화된 가격)
  - [ ] 날짜 범위 선택기 통합
- [ ] `utils/normalize.js` 유틸리티 함수 작성
  - [ ] `normalizePrices()` - 가격 정규화 (첫 날 = 100)
  - [ ] `calculateRelativeReturns()` - 상대 수익률 계산

#### Task 2.3: 비교 테이블 구현 (1.5시간)
- [ ] `ComparisonTable.jsx` 컴포넌트 생성
  - [ ] 6개 종목 성과 비교 테이블
  - [ ] 컬럼: 티커, 이름, 현재가, 수익률 (7일/1개월/3개월), 변동성, 샤프 비율
  - [ ] 정렬 기능 (수익률, 변동성 등)
  - [ ] 등락률 색상 표시
  - [ ] 각 행 클릭 시 Detail 페이지 이동

#### Task 2.4: 상관관계 매트릭스 (선택사항) (1시간)
- [ ] `CorrelationMatrix.jsx` 컴포넌트 생성
  - [ ] 6x6 상관관계 히트맵
  - [ ] 색상: 빨강(양의 상관관계) ~ 파랑(음의 상관관계)
  - [ ] 툴팁 (종목 쌍, 상관계수)
- [ ] `utils/correlation.js` 유틸리티 함수 작성
  - [ ] `calculateCorrelation()` - 피어슨 상관계수 계산

#### Task 2.5: Comparison 페이지 통합 (0.5시간)
- [ ] `Comparison.jsx` 페이지에 컴포넌트 통합
  - [ ] 날짜 범위 선택기
  - [ ] 정규화된 가격 차트
  - [ ] 비교 테이블
  - [ ] 상관관계 매트릭스 (선택사항)
- [ ] 로딩/에러 상태 처리

#### Task 2.6: 테스트 작성 (1시간)
- [ ] `NormalizedPriceChart.test.jsx` - 차트 렌더링 테스트
- [ ] `ComparisonTable.test.jsx` - 테이블 렌더링, 정렬 테스트
- [ ] `CorrelationMatrix.test.jsx` - 매트릭스 렌더링 테스트 (선택사항)
- [ ] `Comparison.test.jsx` - 페이지 통합 테스트
- [ ] `utils/normalize.test.js`, `utils/correlation.test.js` - 유틸리티 함수 테스트

**Acceptance Criteria**:
- [ ] 6개 종목 비교 차트가 정상 표시됨
- [ ] 비교 테이블이 정확하게 계산됨
- [ ] 상관관계 매트릭스가 정상 표시됨 (선택사항)
- [ ] 모든 테스트 통과 (목표 커버리지 70% 이상)
- [ ] 크로스 브라우저 테스트 통과

---

### Step 3: UI/UX 개선 (약 1.5-2시간)

**목표**: 에러 처리 및 사용자 피드백 강화

#### Task 3.1: 에러 바운더리 구현 (0.5시간)
- [ ] `ErrorBoundary.jsx` 컴포넌트 생성
  - [ ] React Error Boundary 패턴 구현
  - [ ] 에러 로깅 (console.error)
  - [ ] 폴백 UI (에러 메시지, 새로고침 버튼)
- [ ] App.jsx에 ErrorBoundary 적용
- [ ] 주요 페이지별 ErrorBoundary 적용

#### Task 3.2: 토스트 알림 구현 (0.5-1시간)
- [ ] `Toast.jsx` 컴포넌트 생성
  - [ ] 성공/에러/정보 타입별 스타일
  - [ ] 자동 사라짐 (3초)
  - [ ] 닫기 버튼
- [ ] `useToast.js` 커스텀 훅 작성
  - [ ] `showToast()`, `hideToast()` 함수
  - [ ] Context API로 전역 상태 관리
- [ ] 주요 액션에 토스트 적용
  - [ ] 데이터 수집 성공/실패
  - [ ] API 에러

#### Task 3.3: 접근성 개선 (0.5시간)
- [ ] ARIA 라벨 추가 (버튼, 링크, 폼)
- [ ] 키보드 네비게이션 개선 (Tab, Enter, Escape)
- [ ] 색상 대비 확인 (WCAG AA 기준)
- [ ] 스크린 리더 테스트 (VoiceOver, NVDA)

#### Task 3.4: 테스트 작성 (0.5시간)
- [ ] `ErrorBoundary.test.jsx` - 에러 처리 테스트
- [ ] `Toast.test.jsx` - 토스트 렌더링, 자동 사라짐 테스트
- [ ] `useToast.test.js` - 훅 테스트

**Acceptance Criteria**:
- [ ] 에러 바운더리가 정상 작동함
- [ ] 토스트 알림이 정상 표시됨
- [ ] 접근성 체크리스트 통과 (WCAG AA)
- [ ] 모든 테스트 통과

---

### Step 4: E2E 테스트 및 최종 검증 (약 1-2시간)

**목표**: 전체 사용자 플로우 E2E 테스트

#### Task 4.1: Playwright 설정 (0.5시간)
- [ ] Playwright 설치 및 설정
  - [ ] `npm install -D @playwright/test`
  - [ ] `playwright.config.js` 작성
  - [ ] `.github/workflows/e2e.yml` CI 설정 (선택사항)

#### Task 4.2: E2E 테스트 시나리오 작성 (1-1.5시간)
- [ ] `e2e/dashboard.spec.js` - 대시보드 플로우
  - [ ] 6개 종목 카드 표시 확인
  - [ ] 종목 클릭 → Detail 페이지 이동
- [ ] `e2e/etf-detail.spec.js` - Detail 페이지 플로우
  - [ ] 차트 렌더링 확인
  - [ ] 날짜 범위 선택 → 차트 업데이트
  - [ ] 데이터 테이블 정렬 테스트
- [ ] `e2e/comparison.spec.js` - Comparison 페이지 플로우
  - [ ] 비교 차트 렌더링 확인
  - [ ] 비교 테이블 정렬 테스트

**Acceptance Criteria**:
- [ ] 모든 E2E 테스트 통과
- [ ] 전체 사용자 플로우 검증 완료
- [ ] 크로스 브라우저 테스트 통과 (Chrome, Safari, Firefox)

---

## Phase 5 최종 완료 기준 (Definition of Done)

### 기능 요구사항
- [x] Detail 페이지 완성 (Phase 4에서 기본 완료)
- [ ] Detail 페이지 강화 (일별 데이터 테이블, 통계 요약)
- [ ] Comparison 페이지 완성 (비교 차트, 테이블, 상관관계)
- [ ] UI/UX 개선 (에러 바운더리, 토스트 알림)

### 테스트 요구사항 (필수) ⭐
- [ ] **페이지별 통합 테스트** (Detail, Comparison)
- [ ] **데이터 테이블 정렬/필터링 테스트**
- [ ] **비교 로직 테스트** (정규화, 상관관계)
- [ ] **E2E 테스트** (Playwright 권장)
- [ ] **모든 테스트 100% 통과**
- [ ] **테스트 커버리지 70% 이상 유지** (현재 87.37%)

### 문서화
- [ ] 새로운 컴포넌트 JSDoc 주석 추가
- [ ] API 변경 사항 반영 (API_SPECIFICATION.md)
- [ ] 진행 상황 업데이트 (PROGRESS.md, TODO.md)

### 검증
- [ ] 전체 사용자 플로우 수동 테스트
- [ ] 크로스 브라우저 테스트 (Chrome, Safari, Firefox)
- [ ] 모바일 반응형 확인
- [ ] 접근성 테스트 (WCAG AA)
- [ ] 성능 테스트 (Lighthouse 점수 > 90)
- [ ] 프로덕션 빌드 성공 (`npm run build`)

### 성능 목표
- [ ] 번들 크기 < 200 kB (gzip)
- [ ] 페이지 로딩 시간 < 3초
- [ ] API 응답 시간 < 1초

**완료 기준 미달 시: Phase 6로 진행 불가**

---

## 작업 우선순위

1. **High Priority** (필수)
   - Detail 페이지 강화 (일별 데이터 테이블)
   - Comparison 페이지 기본 구현 (비교 차트, 테이블)
   - 테스트 작성 (모든 Step)

2. **Medium Priority** (권장)
   - 상관관계 매트릭스
   - E2E 테스트
   - 접근성 개선

3. **Low Priority** (선택사항)
   - 샤프 비율 계산
   - CI/CD 파이프라인 설정 (Phase 7에서 진행 가능)

---

## 리스크 및 대응 방안

### 리스크 1: 백엔드 API 부족
- **문제**: `GET /api/etfs/compare` 엔드포인트가 구현되지 않음
- **대응**: 프론트엔드에서 개별 API 호출 후 클라이언트 사이드 계산

### 리스크 2: 성능 저하
- **문제**: 6개 종목 × 100+ 데이터 포인트 렌더링 시 느려짐
- **대응**: 데이터 샘플링 (기존 chartUtils.js 활용), React.memo 적용

### 리스크 3: 시간 초과
- **문제**: 예상 시간 초과
- **대응**: 상관관계 매트릭스, E2E 테스트를 Phase 7로 연기

---

**예상 총 소요 시간**: 8-10시간
**목표 완료일**: 2025-11-13 (2일 작업 기준)

---

## 🟣 Phase 6: Report Generation (Priority: Low)

**목표**: 리포트 다운로드 기능

- [ ] Markdown 리포트 생성기
  - [ ] 템플릿 작성
  - [ ] 데이터 집계
  - [ ] 파일 생성
- [ ] PDF 생성 (선택사항)
  - [ ] HTML to PDF 변환
  - [ ] 차트 이미지 포함
- [ ] 다운로드 UI
  - [ ] 리포트 설정 폼
  - [ ] 다운로드 버튼
- [ ] 이메일 전송 (선택사항)

---

## 🔵 Phase 7: Optimization & Deployment (Priority: Medium)

**목표**: 프로덕션 배포 준비

- [ ] 성능 최적화
  - [ ] 프론트엔드 번들 크기 최적화
  - [ ] 이미지 최적화
  - [ ] Code Splitting
  - [ ] React.memo 적용
- [ ] 테스트
  - [ ] 백엔드 유닛 테스트 (pytest)
  - [ ] 프론트엔드 컴포넌트 테스트
- [ ] Docker 설정
  - [ ] Dockerfile 최적화
  - [ ] docker-compose 테스트
- [ ] 배포
  - [ ] 프론트엔드: Vercel
  - [ ] 백엔드: Render/Railway
  - [ ] 데이터베이스: PostgreSQL 마이그레이션
- [ ] 모니터링 설정
  - [ ] 로깅 설정
  - [ ] 에러 추적 (Sentry 등)

---

## 📝 Additional Tasks (선택사항)

- [ ] AI 분석 섹션
  - [ ] GPT API 통합
  - [ ] 주간 트렌드 요약 생성
- [ ] 사용자 인증 (필요 시)
- [ ] 즐겨찾기 기능
- [ ] 모바일 앱 (React Native)
- [ ] 다국어 지원 (i18n)

---
