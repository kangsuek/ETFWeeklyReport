# 개선 백로그 (소스코드 분석 결과)

> **분석일:** 2026-07-03 · **분석 브랜치:** `feature/macos-app`
> **목적:** 새로운 세션에서 이 문서만 보고 개선 작업을 진행할 수 있도록 미사용 코드와 개선 필요 항목을 정리.
> **분석 방법:** 전체 엔드포인트 ↔ 소비자(frontend `services/api.js`, `mcp-server`) 교차 대조, 함수별 호출부 grep, `vulture` 정적 분석(80%+ 신뢰 항목만 채택, 60% 항목은 수동 검증).

---

## ⚠️ 작업 전 필독

1. **브랜치 주의:** 이 분석은 `feature/macos-app` 기준. `main`은 뒤처진 게 아니라 **병렬로 갈라진 브랜치**(웹 파일 64개 차이)이므로, 여기서 찾은 항목이 main에도 있다고 가정하지 말 것. main 수정 시 개별 확인 필수. 기계적 merge/sync 금지.
2. **테스트 격리:** 백엔드 테스트는 `backend/`에서 `uv run pytest`로 실행 (conftest.py가 임시 DB로 격리함). `pip`/`python` 직접 호출 금지 — **uv 전용**.
3. **삭제 전 재검증:** 각 항목의 "검증" 명령을 실행해 여전히 0 참조인지 확인 후 삭제할 것 (분석 시점 이후 코드가 변했을 수 있음).
4. **커밋 단위:** 항목별(또는 섹션별)로 작게 커밋. 커밋 전 `uv run pytest`(백엔드) / `npm test && npm run build`(프론트) 통과 확인.

---

## P1 — 동작/안정성 개선 (우선)

### 1.1 async 엔드포인트가 블로킹 스크레이핑을 직접 호출 → 이벤트 루프 정지
`requests` 기반 수집 함수를 `async def` 핸들러에서 동기 호출하고 있어, 수집 중 서버 전체가 응답 불가.

| 위치 | 문제 호출 |
|---|---|
| `backend/app/routers/etfs.py:425` (`POST /{ticker}/collect`) | `collector.collect_and_save_prices(...)` 직접 호출 |
| `backend/app/routers/etfs.py:549` (`POST /{ticker}/collect-trading-flow`) | `collector.collect_and_save_trading_flow(...)` 직접 호출 |
| `backend/app/routers/news.py:168` (`POST /{ticker}/collect`) | `scraper.collect_and_save_news(...)` 직접 호출 |

**수정:** `await asyncio.to_thread(...)`로 감싸기. 같은 파일 내 선례 있음 — `etfs.py`의 collect-fundamentals(`asyncio.to_thread` 사용), `data.py`(5곳 사용)와 동일 패턴으로.

### 1.2 `X-No-Cache` 헤더가 캐시 전체를 삭제
`backend/app/main.py:82-86` — 헤더가 있으면 `cache.clear()`로 **전체 캐시** 삭제. 한 클라이언트의 새로고침이 모든 사용자/모든 엔드포인트 캐시를 날림.
**수정:** 요청 경로에서 티커/도메인을 추출해 `cache.invalidate_pattern(...)`으로 범위 축소, 또는 최소한 해당 요청의 캐시 키만 우회(bypass)하도록 변경.

### 1.3 FastAPI deprecated API 사용
`backend/app/main.py:106,131` — `@app.on_event("startup"/"shutdown")`는 deprecated. **lifespan context manager**로 교체.
이때 함께 수정: shutdown에서 스케줄러만 멈추고 **DB 커넥션 풀을 닫지 않음** → lifespan shutdown에서 `ConnectionPool.close_all()`(`database.py:84`, 현재 미호출) 호출 추가.

### 1.4 라우터가 `sqlite3.Error`를 직접 catch (DB 계층 결합)
`etfs.py`(10곳), `data.py`(6곳), `news.py`(2곳)에서 `except sqlite3.Error` 사용. HTTP 계층이 SQLite 구현에 결합됨.
**수정:** 서비스/DB 계층에서 `DatabaseException`(`app/exceptions.py:11`)으로 변환해 raise하고, 라우터는 그것만 catch. (1.5의 방향 결정과 함께 진행)

### 1.5 DB 추상화의 방향 결정 필요 (문서와 코드 불일치)
`backend/app/database.py:12` — 현재 코드는 **"SQLite 전용 빌드"**(Non-SQLite DATABASE_URL은 무시). 그런데:
- CLAUDE.md는 "SQLite와 PostgreSQL 추상화"라고 기술 (main 브랜치 기준 설명으로 추정)
- `param_placeholder = "?"` 하드코딩 잔재가 여러 곳에 남아 있음 (`database.py:160,658,739`, `perplexity_service.py` 등) — 멀티 DB 지원 흔적

**결정 후 수정:** (a) SQLite 전용으로 확정 → placeholder 잔재 제거 + CLAUDE.md의 이 브랜치 설명 수정, 또는 (b) PostgreSQL 지원 복원. Mac 앱 브랜치 특성상 (a) 권장.

---

## P2 — 미사용 코드 제거

### 2.1 Perplexity API 호출부 전체가 데드코드 (~250줄)
`backend/app/services/perplexity_service.py` (총 1,027줄) 중 실제 사용되는 것은 **프롬프트 생성**(`get_prompt`:708, `get_multi_prompt`:727)뿐. 라우터(`etfs.py:1185,1221`)는 프롬프트만 반환하고 API를 호출하지 않음.

미사용:
- `analyze()` (:850), `analyze_multi()` (:942), 내부 `replace_citation` (:931, :1018)
- 상수 `PERPLEXITY_API_URL`, `PERPLEXITY_MODEL`, `PERPLEXITY_TIMEOUT`, `PERPLEXITY_TEMPERATURE` (:22-25)
- **연쇄 항목:** Settings 화면과 `settings.py:627,672`의 `PERPLEXITY_API_KEY` 저장 기능 — 키를 저장해도 사용하는 코드가 없음. UI에서 제거하거나, 반대로 `analyze` 엔드포인트를 만들어 살리거나 결정 필요.

**검증:** `grep -rn "\.analyze(\|analyze_multi" backend/app backend/tests` → 0건이면 삭제.

### 2.2 함수/메서드 단위 데드코드

| 위치 | 항목 | 비고 |
|---|---|---|
| `backend/app/services/data_collector.py:1362` | `get_latest_prices_batch()` | 호출부 0 (테스트 `tests/test_batch_queries.py:103`만 존재 → 테스트도 함께 삭제) |
| `backend/app/utils/cache.py:193` | `get_or_set()` | 호출부 0 (테스트 포함) |
| `backend/app/middleware/auth.py:43` | `APIKeyAuth.is_public_endpoint()` | 호출부 0 |
| `backend/app/models.py:60` | `ETFDetailResponse` 클래스 | 사용처 없음 (`etfs.py:5`에서 import만 하고 미사용) |
| `backend/app/exceptions.py:26,31` | `DataNotFoundException`, `ExternalServiceException` | raise/catch 0곳 |
| `backend/app/database.py:84` | `close_all()` | 현재 미호출 — **삭제 말고 P1-1.3에서 lifespan shutdown에 연결 권장** |

### 2.3 미사용 import / 변수 (기계적 정리)

| 위치 | 항목 |
|---|---|
| `backend/app/middleware/rate_limit.py:13` | `Response` import |
| `backend/app/routers/data.py:8` | `DatabaseException` import (1.4 진행 시 사용하게 되면 유지) |
| `backend/app/routers/etfs.py:5,12` | `ETFDetailResponse`, `DatabaseException` import |
| `backend/app/services/ticker_catalog_collector.py:189` | 지역변수 `sosok` |
| `backend/app/config.py:16-17` | `API_HOST`, `API_PORT` — config.py 외 참조 0 (실행 스크립트는 uvicorn 인자 직접 사용) |
| `frontend/src/pages/ETFDetail.jsx:127` | `queryClient` 미사용 (기존 lint 경고) |

### 2.4 미사용 constants (`backend/app/constants.py`)
참조 0건 확인됨: `DEFAULT_DATE_RANGE_DAYS`(:116), `NAVER_NEWS_MAX_RESULTS`(:159), `NEWS_DEFAULT_DISPLAY_COUNT`(:176), `ERROR_NOT_FOUND`(:249), `ERROR_NOT_FOUND_STOCK`(:250), `ERROR_INTERNAL_CREATE_STOCK`~`ERROR_INTERNAL_VALIDATE_TICKER`(:270-273), `DEFAULT_CACHE_TTL`(:280).
**검증:** 각각 `grep -rn "<이름>" backend/app backend/tests` 후 삭제.

### 2.5 소비자 없는 API 엔드포인트 (frontend/MCP 모두 미호출)

| 엔드포인트 | 위치 | 비고 |
|---|---|---|
| `POST /api/etfs/{ticker}/collect-fundamentals` | `etfs.py:1259` | 스케줄러는 collector를 직접 호출하므로 이 HTTP 경로는 미사용 |
| `POST /api/data/collect-fundamentals` | `data.py:485` | 위와 동일 |
| `DELETE /api/data/cache/clear` | `data.py:533` | frontend는 `/data/cache/stats`만 사용 |

**결정 필요:** 수동 트리거용으로 UI에 연결할 가치가 있으면 유지(문서화), 아니면 제거. 제거 시 `docs/API_SPECIFICATION.md`·SDK 재생성(`bash sdk/generate.sh`) 동반.

---

## P3 — 구조 개선 / 중복 제거

### 3.1 백엔드↔프론트 지표 계산 중복 (실제 버그 유발 이력 있음)
같은 지표를 양쪽에서 따로 계산해 **불일치가 이미 발생했었음** (변동성 라벨 사건: 백엔드 1년 연환산 vs 프론트 최근 N일 일간 — 2026-07-03 기간 명시로 임시 해결).

| 지표 | 백엔드 | 프론트엔드 |
|---|---|---|
| 수익률/변동성/MDD/샤프 | `data_collector.get_etf_metrics`(:481), `comparison_service.py` | `utils/returns.js`, `utils/insights.js` |
| 기술지표(RSI/MACD 등) | (main 브랜치에 존재) | `utils/technicalIndicators.js` |
| 뉴스 감성 분석 | `services/news_analyzer.py` | `utils/newsAnalyzer.js` |

**방향:** 계산은 백엔드로 일원화하고 프론트는 표시만 담당하는 것을 권장. 최소한 산식·기간(연환산 vs 일간, 표본 기간)을 문서로 명세해 양쪽이 따르게 할 것.

### 3.2 프론트 포맷터 이중화
`frontend/src/utils/format.js`(9개 export, 15개 파일에서 사용)와 `utils/formatters.js`(4개 export, 3개 파일에서 사용)에 **`formatNumber`/`formatPercent`가 서로 다른 구현으로 중복**. → `formatters.js`를 `format.js`로 흡수 통합하고 import 경로 정리 (천단위 구분자 규칙 준수 확인).

### 3.3 거대 파일 분리

| 파일 | 줄수 | 분리안 |
|---|---|---|
| `backend/app/services/data_collector.py` | 1,557 | 가격 수집 / 매매동향 수집 / 지표 계산(metrics) 3개 모듈로 |
| `backend/app/routers/etfs.py` | 1,357 | batch-summary·intraday 등 인라인 비즈니스 로직을 services로 이동, 라우터는 얇게 |
| `frontend/src/pages/ETFDetail.jsx` | 1,047 | 섹션별 컴포넌트 추출 (이미 `components/etf/`에 일부 존재 — 나머지도) |
| `backend/app/services/perplexity_service.py` | 1,027 | 2.1 데드코드 제거 후 프롬프트 빌더로 축소 |
| `backend/app/routers/settings.py` | 708 | api-keys 관리 부분 분리 검토 |

### 3.4 소소한 중복
- `CACHE_TTL_SECONDS = int(float(os.getenv("CACHE_TTL_MINUTES", "0.5")) * 60)` 이 3개 라우터에 복붙됨 (`news.py:30`, `data.py:40`, `etfs.py:49`) → `config.py`로 이동 (config.py:38의 미사용 `CACHE_TTL_MINUTES` 자리 활용).
- 인메모리 캐시(`utils/cache.py`) + slowapi 인메모리 rate limit → **단일 프로세스 전제**. Mac 앱(단일 uvicorn)에선 문제없으나 웹 배포에서 워커 2개 이상이면 캐시 무효화·rate limit이 프로세스별로 갈라짐. 배포 문서에 제약 명시 필요.

---

## P4 — 문서 불일치 (코드가 정본, 문서를 수정)

| 문서 | 불일치 내용 | 실제 |
|---|---|---|
| `CLAUDE.md` | `naver_finance_scraper.py`가 스크레이퍼라고 기술 | 해당 파일 없음. 실제: `naver_stock_api.py`, `news_scraper.py`, `ticker_scraper.py` |
| `CLAUDE.md` | "SQLite와 PostgreSQL 추상화" | 이 브랜치는 SQLite 전용 (`database.py:12`) — P1-1.5 결정과 연동 |
| `docs/BRANCHES.md` | "main = 웹 전용" | main에도 `macos/` 존재 — 브랜치 정책 문서 현행화 필요 |
| `docs/API_SPECIFICATION.md` | 최신 엔드포인트 반영 여부 | 2.5 정리 후 일괄 대조·갱신 + `bash sdk/generate.sh` 재실행 |

---

## 권장 작업 순서

1. **P2-2.3 → 2.4 → 2.2** (기계적 삭제, 리스크 낮음. 각 단계 후 `uv run pytest` + `uv run flake8 app/`)
2. **P1-1.1** (to_thread 래핑 — 3곳, 즉효)
3. **P1-1.3** (lifespan 전환 + close_all 연결)
4. **P1-1.5 결정 → P1-1.4, P2-2.1, P2-2.5** (방향 결정이 필요한 항목)
5. **P1-1.2** (캐시 무효화 범위 축소)
6. **P3** (중복 제거·파일 분리 — 별도 세션 권장, 파일당 1커밋)
7. **P4** (문서 정리 — 코드 변경 마무리 후)

## 완료 판정 기준
- `cd backend && uv run pytest` 전체 통과
- `cd backend && uv run flake8 app/` 경고 0
- `cd frontend && npm test && npm run lint && npm run build` 통과
- 삭제한 엔드포인트가 있으면: frontend grep 0건 + `docs/API_SPECIFICATION.md` 갱신 + SDK 재생성
