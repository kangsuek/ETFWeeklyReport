# 코드 리뷰 개선 계획 (2026-07-20)

백엔드(`backend/app/`)와 프론트엔드(`frontend/src/`) 전체를 버그/정확성, 보안, 코드 품질/중복, 성능 4개 카테고리로 검토한 결과. 항목마다 `[ ]`로 진행 상태를 표시하며, 심각도 순으로 정렬했다.

## 진행 상태 표기
- `[ ]` 미착수 `[x]` 완료 `[skip]` 의도적으로 보류(사유 명시)

---

## A. 즉시 수정 (High)

- [x] **A1. `routers/etfs.py` `get_fundamentals` — PostgreSQL에서 holdings 조회가 깨지는 버그**
  방금 추가한 `SELECT MAX(date) FROM etf_holdings` 결과를 `row[0]`으로 읽었는데, PostgreSQL은 `RealDictCursor`를 쓰므로 정수 인덱스 접근이 불가능(KeyError). `AS latest_date` 별칭 + `USE_POSTGRES` 분기로 수정 완료.

- [x] **A2. `routers/settings.py` `GET /settings/api-keys?raw=true` — 인증 없이 평문 API 키 노출**
  형제 엔드포인트인 `PUT /settings/api-keys`는 `Depends(verify_api_key_dependency)`가 걸려 있는데 `raw=true` 조회는 인증이 전혀 없어 네이버 API 키(`NAVER_CLIENT_ID`/`SECRET`)가 누구에게나 평문으로 노출됨.

- [x] **A3. `services/scheduler.py` 시작 시 동기 블로킹 — 앱 기동 자체가 지연됨**
  `main.py`의 `async def startup_event()`가 `scheduler.start()`를 그대로 호출하고, 그 안에서 각 티커에 대해 동기 `requests.get()`을 도는 `collect_periodic_data`/`_collect_fundamentals_if_needed`가 실행됨. 이벤트 루프가 막혀 `/api/health`조차 응답 못 하는 구간이 생김 → Render 등 배포 환경에서 헬스체크 타임아웃 위험.

- [x] **A4. `routers/alerts.py` — 변경성 엔드포인트에 인증 누락**
  `POST /`, `PUT /{rule_id}`, `DELETE /{rule_id}`, `POST /trigger`에 `verify_api_key_dependency`가 빠져 있음. 다른 라우터의 동급 CRUD는 전부 보호돼 있음.

## B. 중요도 중간 (Medium)

- [x] **B1. `routers/scanner.py` `POST /collect-data` — 인증·레이트리밋 없는 장시간 크롤 트리거**
  인증도, 레이트리밋도 없어 누구나 반복 호출해 5~10분짜리 전체 크롤을 무한 재실행시킬 수 있음(리소스 고갈 벡터).

- [x] **B2. `services/scheduler.py:collect_catalog_data` — check-then-act 레이스**
  진행 여부를 확인 후 실행하는데 원자적이지 않음. 같은 파일의 `collect_periodic_data`/`collect_fundamentals`는 `threading.Lock(blocking=False)`로 올바르게 처리하고 있으니 동일 패턴 적용.

- [x] **B3. `services/scheduler.py:_collect_fundamentals_if_needed` — Postgres에서 count 조회 오독**
  `SELECT COUNT(*)` 결과를 `row[0]`으로 읽어 Postgres에서 깨짐. 예외가 `except Exception` + `logger.warning`으로 조용히 삼켜져서 "오늘 이미 수집됨" 체크가 항상 실패 → 매 재시작마다 불필요한 중복 수집.

- [x] **B4. `middleware/auth.py` — 죽은 코드가 "중앙 인증"이라는 착시를 줌**
  `PUBLIC_ENDPOINTS`/`is_public_endpoint()` 등은 호출하는 곳이 전혀 없음(grep 확인). 실제 인증은 라우트별 `Depends()`로만 이뤄지고 있어, 이 죽은 코드 때문에 B1/A4 같은 누락이 생겼을 가능성. 죽은 코드 제거 또는 실제로 연결.

- [x] **B5. `routers/etfs.py:get_batch_summary` — 뉴스만 N+1**
  가격/매매동향은 배치 조회로 최적화됐는데 뉴스는 티커별로 루프 돌며 개별 조회. 엔드포인트 docstring은 "N+1 최적화"라고 돼 있어 모순.

- [x] **B6. 프론트 `TickerManagementPanel.jsx` 순서 변경 — 실패 시 롤백 없음**
  optimistic update 후 실패하면 alert만 띄우고 캐시는 그대로 둠. 같은 개념을 다루는 `Dashboard.jsx`의 reorder는 `onMutate`/context 롤백을 올바르게 구현하고 있으니 그 패턴을 재사용.

- [x] **B7. 프론트 `format.js` vs `formatters.js` — 등락률 포맷/색상 이원화**
  페이지별로 다른 유틸을 써서 화살표(▲/▼) 유무, 다크모드 색상 대응 유무가 갈림. 프로젝트 컨벤션(숫자 표시 일관성) 위반.

- [x] **B8. 프론트 `ETFCharts.jsx` "최근 N일 최고가" 라벨 값 오류**
  실제 lookback 일수 대신 `supports.length + resistances.length`(레벨 개수)를 표시. 사용자에게 잘못된 정보 노출.

- [x] **B9. 프론트 `TickerForm.jsx` 자동완성 — stale closure로 사용자 입력 덮어씀**
  `validateMutation.onSuccess`가 `setFormData({...formData, ...})`를 써서, 네트워크 응답 대기 중 사용자가 다른 필드를 수정하면 그 수정이 덮어써짐. 함수형 업데이터로 교체 필요.

## C. 코드 품질/구조 (Low~Medium, 시간 될 때)

- [ ] **C1. 백엔드 `if USE_POSTGRES: cursor=... else: cursor=...` 보일러플레이트 23곳 반복**
  `database.py`의 `get_cursor()`가 read 경로용으로 이미 있으나 write(commit 필요) 경로엔 동등한 헬퍼가 없어 계속 복붙됨 → A1류 버그의 근본 원인. `get_conn_and_cursor()` 헬퍼 추가해 점진적으로 교체.
- [ ] **C2. `etf_fundamentals_collector.py` — NAV/holdings INSERT 블록이 `collect_*`와 `collect_all`에 중복**
  private 헬퍼로 추출.
- [ ] **C3. `services/perplexity_service.py` 의 `analyze()`/`analyze_multi()` — 호출부 없는 죽은 코드**
- [ ] **C4. `utils/cache.py:get_cache()` 싱글턴 — 최초 호출의 `ttl_seconds`/`max_size`만 적용되고 이후 호출 인자는 무시됨** (풋건, 문서화라도 필요)
- [ ] **C5. 프론트 `TickerForm.jsx` 티커/종목명 자동완성 드롭다운 마크업 중복** (~35줄 블록 2곳) → 공용 컴포넌트로 추출
- [ ] **C6. 프론트 `main.jsx`/`SettingsContext.jsx` 테마 감지 로직 중복**

## D. 성능 (Low, 영향 적음 — 백로그)

- [ ] **D1. `routers/data.py` collect-all의 fundamentals 수집이 순차 for-loop** (가격 수집은 `ThreadPoolExecutor(5)` 병렬인데 불일치). 티커 수가 적어 지금은 영향 미미.
- [ ] **D2. 프론트 `ETFCard.jsx:renderMiniChart()` — `useMemo` 없이 매 렌더 재계산.** 카드가 이미 `memo`라 영향 적음.

## 보류/조치 불필요로 확인된 것
- SQL 인젝션: 발견된 f-string SQL은 전부 파라미터 바인딩 + 화이트리스트 컬럼명이라 안전함(조치 불필요).
- CORS: origin 화이트리스트 사용 중, 와일드카드 아님(조치 불필요).
- `NewsTimeline.jsx`의 외부 `news.url` href — 위험도 낮음(백엔드/네이버 출처, 사용자 직접입력 아님). 스킴 화이트리스트만 낮은 우선순위로 고려.
- `VITE_API_KEY`가 클라이언트 번들에 노출되는 것은 Vite 특성상 불가피 — 민감한 값을 게이트하는 용도가 아니라면 문제없음, 실제 용도 확인만 권장.

---

## 실행 순서
1. A1~A4 (즉시, 보안/기동 문제 우선)
2. B1~B9 (버그/보안/일관성)
3. C1 (헬퍼 추가로 재발 방지) → 이후 C2~C6은 여유 있을 때
4. D1~D2는 실제 병목이 확인되면 진행

---

## 완료 요약 (2026-07-20)

A/B 전 항목(A1~A4, B1~B9) 수정 및 검증 완료. C/D는 백로그로 남김.

**작업 중 발견한 추가 항목 (계획에 없었지만 함께 수정):**
- `ETFCard.jsx`에 다크모드 미지원 세 번째 등락률 색상 함수(`getChangeColor` 로컬 정의)가 있어 B7과 함께 `format.js`의 공용 함수로 교체.
- (별도 요청) `scripts/build-dmg.sh`가 `feature/macos-app`/`feature/windows-app`을 로컬 브랜치로 가정해 항상 실패하던 버그 수정 (`origin/<branch>`를 직접 참조하도록 변경). 실제 DMG 빌드 성공까지 확인.

**검증 방법:** 각 항목마다 실제 동작 확인(서버 재시작/헬스체크 응답시간, curl로 API 응답, 브라우저에서 실제 클릭 흐름, 동시성은 목으로 안전하게 재현) + 관련 테스트 스위트 실행. 모든 사전 존재 실패(pre-existing failure)는 변경 전/후 동일함을 stash 비교로 확인해 회귀가 아님을 검증.

**커밋 시 주의:** `backend/config/stocks.json`은 이 세션과 무관한 로컬 드리프트라 계속 제외. `build-dmg.sh` 실행 중 `git checkout origin/feature/{macos,windows}-app`가 `macos/`, `windows/` 트래킹 파일들을 일시적으로 덮어썼던 것은 원상복구함(커밋 대상 아님).
