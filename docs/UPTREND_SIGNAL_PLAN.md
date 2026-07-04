# 상승흐름 확정 알림 — 구현 플랜

> **📌 진행 상황 (2026-07-04):** Phase 0~3 **구현·검증·커밋 완료**. Phase 4(선택·데이터 축적 후)만 미착수.
> - 백엔드: `uv run pytest` **523 passed / 1 skipped**, 신규 코드 flake8 클린
> - 프론트: 신규 테스트 8종 통과, `npm run build` 성공, `npm run lint` exit 0
> - 회귀 개선: `renderWithProviders`에 누락된 `AlertProvider` 보강 → 기존 실패 테스트 12개 복구, 신규 회귀 0
> - 보류: SDK 파이썬 클라이언트 재생성(`openapi-python-client` 미설치 — `openapi.json` 스펙만 갱신),
>   실 데이터 스모크(앱 기동 시 따라잡기로 자연 실행), Phase 4

> **설계 정본:** [UPTREND_SIGNAL_DESIGN.md](./UPTREND_SIGNAL_DESIGN.md) · **브랜치:** `feature/macos-app`
> 이 문서는 설계를 **커밋 단위의 실행 단계**로 쪼갠 작업 순서다. 각 단계는 독립 커밋 가능하고,
> "완료 기준(DoD)"을 만족해야 다음으로 넘어간다.
>
> **공통 규칙 (매 커밋 전):**
> - 백엔드: `cd backend && uv run pytest && uv run flake8 app/` 통과 (uv 전용, `pip`/`python` 금지)
> - 프론트: `cd frontend && npm test && npm run lint && npm run build` 통과
> - 테스트는 임시 DB 격리(conftest.py) + Given-When-Then, 클래스 기반
> - 커밋은 단계별로 작게. 브랜치는 `feature/macos-app` 유지 (main 병렬 fork — 동기화 금지)

---

## Phase 0 ✅ — 착수 전 확정할 결정 (구현 아님)

코드 시작 전에 못 박아야 재작업이 없다.

| # | 결정 사항 | 기본 권장 | 영향 |
|---|-----------|-----------|------|
| D1 | uptrend 미읽음 UI 위치 (§3-5.4) | **Alerts 페이지 별도 "상승흐름 신호" 섹션 + nav 배지**. 기존 벨 드롭다운은 불변 | Phase 3 범위 |
| D2 | LV1 알림 노출 여부 | 기본 꺼짐(설계대로). MVP에서는 **LV1 UI 토글 생략**, LV2만 | Phase 2·3 축소 |
| D3 | 파라미터 기본값 (§2-6) | 설계값 그대로 시작, Phase 4에서 백테스트로 조정 | 없음(상수만) |
| D4 | `app_state` 신규 테이블 vs 기존 재사용 | **신규 `app_state(key,value)`** — 범용 키-값, 다른 마커도 수용 | Phase 2 |

> D1·D2는 사용자 확인 후 진행 권장. 나머지는 기본값으로 진행 가능.

---

## Phase 1 ✅ — 수집기 보강 (감지기의 데이터 전제 확보) ★선행

> 신호 감지기는 "연속·최신·수급 포함" 데이터를 전제한다. 감지기보다 먼저 데이터 파이프라인을 고친다.
> Phase 1은 **감지기 없이도 독립적으로 검증·머지 가능**하다.

### 1.1 ✅ `ensure_recent_history()` — 갭 보충 헬퍼 (+ 상수 선행 정의)
- **파일:** `backend/app/services/data_collector.py`, `backend/app/constants.py`
- **작업:**
  - `constants.py`에 `SIGNAL_MIN_DATA_DAYS = 30` **이 단계에서 먼저 정의**
    (나머지 `SIGNAL_*` 상수는 2.1 — Phase 1이 Phase 2에 의존하지 않도록 분리)
  - 신규 메서드 `ensure_recent_history(ticker, min_rows=SIGNAL_MIN_DATA_DAYS) -> bool`:
    1. `get_collection_status(ticker)`로 `last_price_date` 확인
    2. 오늘과의 달력일 간격을 구해 **캡 없이** `collect_and_save_prices(ticker, days=gap)` +
       `collect_and_save_trading_flow(ticker, days=gap)` 호출 (기존 `calculate_missing_days`의 1일 캡 우회)
    3. 보충 후 `prices` 행 수 조회 → `min_rows` 미만이면 **자기치유: `days=90` 1회 추가 요청**
       (이 기능 도입 전에 등록돼 부분 이력만 가진 종목 커버) → 그래도 미만이면 `False` 반환
  - 순수 조회/수집 조합이므로 블로킹 스크레이핑은 호출부에서 `asyncio.to_thread` 래핑 대상임을 주석 명시
- **DoD:**
  - 단위 테스트(임시 DB): (a) 갭 5일 → 5일 요청됨, (b) 최신 상태 → 수집 스킵,
    (c) 행 30 미만 → 90일 재요청 후 재판정, 여전히 미만이면 `False`,
    (d) 신규 종목(이력 0) → 요청량 = 기본 백필 일수
  - `uv run pytest tests/test_data_collector*.py` 통과
- **커밋:** `feat: 신호 감지용 데이터 갭 보충 헬퍼 ensure_recent_history`

### 1.2 ✅ 신규 종목 등록 시 초기 백필
- **파일:** `backend/app/routers/settings.py` (`create_stock`)
- **작업:** `stocks_manager.add_stock` 성공 후, 백그라운드로 `days=90`(달력일, 기존 `DEFAULT_BACKFILL_DAYS` 재사용)
  가격·매매동향 수집 트리거. `asyncio.to_thread` + fire-and-forget(응답 지연 없이). 실패는 로그만(등록 자체는 성공 처리).
- **DoD:**
  - 테스트: `create_stock` 호출 시 백필 함수가 해당 티커·일수로 스케줄되는지(모킹) 검증
  - 수동 확인: 종목 추가 → 잠시 후 `GET /api/etfs/{ticker}/prices`에 데이터 존재
- **커밋:** `feat: 종목 등록 시 히스토리 초기 백필 트리거`

### 1.3 ✅ 매매동향 최신일 기록 정확성 점검
- **파일:** `backend/app/services/data_collector.py`(`_collect_single_ticker`), `trading_flow_collector.py`
- **작업:** 매매동향 수집 시 `update_collection_status(..., trading_flow_date=...)`가 성공/실패를 정확히
  반영하는지 확인·보정(감지기가 `last_trading_flow_date`로 수급 신선도를 판정하므로). 실패를 조용히 삼키지 않도록
  상태 기록만 보강(수집 흐름 자체 로직은 최소 변경).
- **DoD:** 테스트: 매매동향 수집 성공/실패 시 `collection_status`의 해당 필드가 기대대로 갱신
- **커밋:** `fix: 매매동향 수집 상태 기록 정확성 보강`

**Phase 1 완료 판정:** `uv run pytest && uv run flake8 app/` 그린. 감지기 없이 데이터 보강만으로 회귀 없음.

---

## Phase 2 ✅ — 백엔드 감지기 + uptrend 이력 (핵심)

### 2.1 ✅ 상수 + 테이블 + 마이그레이션
- **파일:** `backend/app/constants.py`, `backend/app/database.py`
- **작업:**
  - `constants.py`의 `# 상승흐름 신호` 섹션에 §2-6의 나머지 `SIGNAL_*` 상수 9개 정의
    (`SIGNAL_MIN_DATA_DAYS`는 1.1에서 선행 정의됨)
  - `database.py` `init_db()`에 테이블 2개 (기존 `{text_type}` 등 placeholder idiom 사용):
    - `signal_events` (§3-2 스키마) + `idx_signal_events_status`
    - `app_state(key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP {timestamp_default})`
  - `CREATE TABLE IF NOT EXISTS`이므로 기존 DB 안전. `run_migrations()`는 no-op 유지.
- **DoD:** 앱 기동 시 테이블 생성 확인, [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) 갱신
- **커밋:** `feat: signal_events·app_state 테이블 및 신호 상수 추가`

### 2.2 ✅ 감지기 순수 함수 (`detect_breakout`, `update_pending`)
- **파일:** `backend/app/services/signal_detector.py` (신규)
- **작업:** DB 접근 없는 **순수 함수**로 판정 로직 구현:
  - `detect_breakout(prices, flows, as_of_idx) -> BreakoutSignal | None` — B1~B6 (§2-2)
  - `update_pending(event, prices, flows, as_of_idx) -> ('pending'|'confirmed'|'failed'|'expired', path)` — C1/C2/실패/만료 (§2-3, §2-4)
  - **as-of 슬라이싱**: 입력 배열을 `as_of_idx`까지만 보도록 강제 (미래 참조 금지)
- **DoD (가장 중요한 테스트 지점):** 합성 가격/수급 시리즈로 각 분기 단위 테스트
  - LV1 발생/미발생(B2·B3·B4·B5·B6 각각 경계), C1(재시험 성공·같은날·저가붕괴로 실패), C2(연속유지),
    failed(종가 붕괴), expired(윈도우 경과), 이중 pending 차단
- **커밋:** `feat: 상승흐름 신호 판정 순수 함수 (LV1/LV2 상태 전이)`

### 2.3 ✅ `scan_all(since)` — DB 연동 + 소급 재생 + 마커 + 알림 발신
- **파일:** `backend/app/services/signal_detector.py`
- **작업:**
  - 활성 `uptrend` 규칙 종목 순회 → 종목별 `ensure_recent_history`(Phase 1.1) → prices·flows 로드
  - `since`~오늘의 놓친 거래일을 **오래된 순서로 재생**, 각 날짜에 2.2 함수 적용 → `signal_events` UPSERT
  - 데이터/수급 결측 시 판정 보류(§4-4), 당일 16:40 이전이면 오늘분 제외(§4-1)
  - **알림 발신 (서비스 계층, 라우터 경유 없음):** LV2 확정 시 게이트(쿨다운·스테일 가드) 통과분만
    `alert_history`에 직접 기록 — `alert_type='uptrend'`, `rule_id`=해당 규칙,
    `triggered_at`=**확정 거래일**, message=설계 §3-3 문구(천 단위 콤마).
    발신 성공 시 `alert_rules.last_triggered_at` 갱신 → **쿨다운의 기준값이 여기서 만들어진다**
  - 전 종목 성공 시에만 `app_state.last_signal_scan_date` 갱신
- **DoD:** 통합 테스트 — 며칠치 소급 재생, 부분 실패 시 마커 미갱신, 멱등 재실행,
  쿨다운 내 재확정 시 이력 미기록 + `last_triggered_at` 불변
- **커밋:** `feat: scan_all 소급 재생·상태 관리·알림 발신`

### 2.4 ✅ alerts 라우터 — uptrend 규칙 수용 + signals 조회
- **파일:** `backend/app/routers/alerts.py`, `backend/app/models.py`
- **작업:**
  - `VALID_ALERT_TYPES`에 `uptrend` 추가, `_validate_rule`에서 `uptrend`는 `target_price` 검사 면제
  - `GET /api/alerts/signals/{ticker}` — 종목별 `signal_events` 조회
  - (이력 기록은 2.3의 서비스 계층 담당 — 라우터에는 두지 않는다)
- **DoD:** 테스트: uptrend 규칙 CRUD, signals 조회 응답 스키마
- **커밋:** `feat: alerts 라우터 uptrend 규칙·signals 조회 지원`

### 2.5 ✅ uptrend 이력·읽음 API
- **파일:** `backend/app/routers/alerts.py`
- **작업 (⚠️ 라우트 등록 순서):** `GET /api/alerts/uptrend`를 **`GET /api/alerts/{ticker}`(현 alerts.py:134)보다 먼저 등록**
  - `GET /api/alerts/uptrend` — 이력 + `unread_count`(= `triggered_at > uptrend_last_read_at` 카운트), `limit`/`offset`
  - `POST /api/alerts/uptrend/read` — `app_state.uptrend_last_read_at = now`
  - `DELETE /api/alerts/uptrend/{id}` · `?before=` — 이력 정리
- **DoD:** 테스트: 미읽음 카운트 계산, read 후 0, **최초 실행(마커 부재) 시 전체가 미읽음**,
  라우트 순서(uptrend가 티커로 안 잡힘), 삭제
- **커밋:** `feat: uptrend 알림 이력·읽음(unread) API`

### 2.6 ✅ 스케줄러 — 크론 잡 + 앱 시작 따라잡기
- **파일:** `backend/app/services/scheduler.py`
- **작업:**
  - 크론 잡 `signal_scan`: 평일 16:40 KST → 오늘 가격·수급 재수집 후 `scan_all()`
    (재수집 시 잠정치 갱신은 `INSERT OR REPLACE` 저장 방식으로 보장됨 — 코드 확인 완료)
  - `_run_signal_scan_if_needed()`: `start()` 말미(`_collect_fundamentals_if_needed` 다음)에서
    **백그라운드 1회성 잡**으로 등록 → 기동 비블로킹. `last_signal_scan_date` 기준 소급.
- **DoD:** 테스트: 잡 등록 확인, 따라잡기가 놓친 구간에 `scan_all(since)` 호출(모킹). 앱 기동 스모크.
- **커밋:** `feat: 신호 스캔 스케줄러 잡 + 앱 시작 따라잡기`

### 2.7 🔶 백엔드 통합 검증 (SDK 클라이언트 재생성만 보류)
- **작업:** `verify` 스킬 또는 수동 — 실제 등록 종목으로 스캔 1회 강제 실행, `signal_events`·`alert_history`·API 확인
- **DoD:** `uv run pytest && uv run flake8 app/` 그린 + 실제 데이터 스모크. SDK 재생성 `bash sdk/generate.sh`
- **문서:** API_SPECIFICATION/MANUAL(신규 엔드포인트) + **METRICS_SPEC**(uptrend 판정 기준, 설계 링크) 갱신
- **커밋:** `chore: SDK 재생성 및 신호 API 문서 반영`

---

## Phase 3 ✅ — 프론트 신호 연동

### 3.1 ✅ API 클라이언트
- **파일:** `frontend/src/services/api.js`
- **작업:** `alertApi`에 `getUptrend`, `markUptrendRead`, `deleteUptrend`, `getSignals(ticker)` 추가
- **커밋:** `feat: 프론트 uptrend 알림 API 클라이언트`

### 3.2 ✅ PriceTargetPanel "상승흐름" 탭
- **파일:** `frontend/src/components/etf/PriceTargetPanel.jsx`
- **작업:** 4번째 탭 — uptrend 규칙 켜기/끄기 토글(생성·삭제), 현재 신호 상태 표시(`getSignals`)
- **DoD:** msw 목 + 컴포넌트 테스트
- **커밋:** `feat: 종목 상세에 상승흐름 알림 설정 탭`

### 3.3 ✅ 미읽음 배지 + 폴링
- **파일:** nav/Header 또는 신규 컴포넌트, uptrend 전용 훅
- **작업:** `getUptrend` **10분 폴링 — 앱 실행 중 상시**(신호는 16:40 장 마감 후·앱 시작 시 생기므로
  장중 한정 폴링은 당일 신호를 다음날까지 놓침), `unread_count`로 배지. **기존 `AlertContext`/벨 불변**(D1)
- **DoD:** 테스트: 미읽음 표시, read 호출 시 0
- **커밋:** `feat: 상승흐름 신호 미읽음 배지`

### 3.4 ✅ Alerts 페이지 "상승흐름 신호" 이력 섹션
- **파일:** `frontend/src/pages/Alerts.jsx`
- **작업:** 별도 섹션 — 서버 이력(페이지네이션), 읽음/삭제. 기존 3종 이력(메모리)과 분리 렌더
- **DoD:** 컴포넌트 테스트(빈 상태·목록·삭제)
- **커밋:** `feat: Alerts 페이지 상승흐름 신호 이력 섹션`

### 3.5 ✅ ETFDetail 확정 배지
- **파일:** `frontend/src/pages/ETFDetail.jsx`
- **작업:** 확정 신호 있으면 헤더 근처 "상승흐름 확정 (MM/DD)" 배지
- **커밋:** `feat: 종목 상세 상승흐름 확정 배지`

**Phase 3 완료 판정:** `npm test && npm run lint && npm run build` 그린. 기존 벨/AlertContext 회귀 없음.
**문서:** FEATURES(uptrend 알림·이력·배지)·ARCHITECTURE(신규 서비스·스케줄러 잡) 갱신.

---

## Phase 4 ⬜ — 검증·조정 (선택, 데이터 축적 후 · 미착수)

### 4.1 신호 재현(replay) 스크립트
- 등록 종목 과거 1년치로 `detect_breakout`/`update_pending` 재생 → 신호 빈도·확정률·확정 후 N일 수익률 리포트

### 4.2 파라미터 튜닝
- 4.1 결과로 `VOL_MULT`·`CONFIRM_WINDOW`·`OVERHEAT_5D` 등 조정. 시뮬레이션 기능과 교차 검증.

---

## 진행 체크리스트

```
Phase 0  [x] D1·D2 사용자 확인 (D1 별도 섹션+배지 / D2 LV2만 / D3 설계값 / D4 신규 app_state)
Phase 1  [x] 1.1 ensure_recent_history  [x] 1.2 신규종목 백필  [x] 1.3 수급 상태기록
Phase 2  [x] 2.1 테이블·상수  [x] 2.2 순수함수  [x] 2.3 scan_all  [x] 2.4 규칙·signals
         [x] 2.5 이력·읽음 API  [x] 2.6 스케줄러  [~] 2.7 통합·문서(SDK 클라이언트 재생성만 보류)
Phase 3  [x] 3.1 api.js  [x] 3.2 설정탭  [x] 3.3 배지  [x] 3.4 이력섹션  [x] 3.5 상세배지
Phase 4  [ ] 4.1 replay  [ ] 4.2 튜닝   (선택 — 데이터 축적 후)
```

**커밋 매핑** (`feature/macos-app`):
`f468020`(1.1) · `b99cd5b`(1.2) · `6feeb7c`(1.3) · `f9cb3e1`(2.1) · `7ab2fef`(2.2) ·
`b2417bc`(2.3) · `1af4a3d`(2.4) · `b2dedea`(2.5) · `30b5f2b`(2.6) · `3f77cd1`(2.7 문서·OpenAPI) ·
`b7718ea`(3.1) · `32b09ed`(3.2) · `f3baafe`(3.3) · `d016072`(3.4) · `0c25291`(3.5) · `0eacb63`(3 문서)

**의존성 요약:** Phase 1 → 2 (감지기가 1.1 헬퍼 사용) → 3 (프론트가 2의 API 사용).
Phase 1 내부는 병렬 가능. Phase 2 내부는 2.1 → 2.2 → 2.3 순서 필수(알림 발신 포함 — 2.4에 비의존),
2.4/2.5는 2.3과 병렬 가능, 2.6은 2.3 이후.
