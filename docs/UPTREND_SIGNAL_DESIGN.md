# 상승/하락 흐름 확정 알림 (Trend Signal) 설계서

> **상태:** ✅ 구현 완료 (상승·하락 양방향) · **작성일:** 2026-07-04 · **대상 브랜치:** `feature/macos-app`
> **목적:** '종목 관리'에 등록된 종목이 **거래량 동반 돌파 → 수급 확인 → 재시험 성공**의
> 검증된 상승 전환 패턴을 완성했을 때 알림으로 알려준다.

> ### 📌 이 문서 이후 확장된 사항 (구현 반영됨)
>
> **1. 하락흐름(downtrend) — 본 설계의 완전한 거울상.** 아래 §2의 모든 규칙을 부호 대칭으로
> 뒤집어 같은 감지기(`_sign(direction)`)로 판정한다. `signal_events.direction`(`up`|`down`)에
> 저장되고, 알림 이력·미읽음 마커·화면이 방향별로 분리된다.
>
> | 항목 | 상승(up) | 하락(down) |
> |---|---|---|
> | 기준선 | 직전 20일 **최고가** 상향 돌파 | 직전 20일 **최저가** 하향 이탈 |
> | 캔들 위치 | 상단 마감 ≥ 0.6 | 하단 마감 ≥ 0.6 (=위치 ≤ 0.4) |
> | 수급 | 순매수 > 0 | 순매도 < 0 |
> | 과열 필터 | 5일 수익률 ≥ **+25%** 제외 | 5일 수익률 ≤ **−25%** 제외(투매 추격 방지) |
> | 실패선 | 돌파선 × **0.97** (아래로 붕괴) | 이탈선 × **1.03** (위로 회복) |
> | C1 재시험 | 저가가 밴드 접근 후 종가 재돌파 | **고가**가 밴드 접근 후 종가 **재이탈** |
> | C2 연속 유지 | 3일 연속 종가 > 돌파선 | 3일 연속 종가 < 이탈선 |
>
> **한 가격 마감(상·하한가 잠김) 예외:** 고가=저가인 봉은 방향과 무관하게 캔들 강도 **1.0**으로
> 본다(점상한가=최강 돌파, 점하한가=최강 이탈). `1 − 캔들위치`를 그대로 쓰면 하한가 잠김 봉이
> 0이 되어 기각되는 비대칭이 생기므로 `_effective_candle`로 처리한다.
>
> **2. 신선도 가드 (`SIGNAL_ALERT_FRESH_DAYS` = 10거래일).** 확정일이 최신 데이터로부터
> 이 기간보다 오래됐으면 **상태(`signal_events`)만 기록하고 알림·현재 배지는 억제**한다.
> 최초 스캔·장기 미기동 따라잡기의 소급 재생이 수개월 전 확정을 '새 신호'처럼 띄우는 것을 막는다.
>
> **3. 판정 범위 확장 (읽기 전용).** 알림 규칙 없이도 현재 상태를 조회하는 두 경로:
> - `evaluate_watchlist(direction)` — 이미 이력이 있는 **등록 종목** 전체를 즉시 재생
> - `evaluate_tickers(tickers, direction, limit)` — **조건검색 결과 등 임의 종목**의 이력을
>   그때그때 수집(종목당 약 2초)한 뒤 판정. `SIGNAL_BATCH_SCAN_MAX`(50) 상한.
>   `stock_catalog`(약 3,900종목)에는 20일 OHLC·수급 이력이 없어 전 종목 일괄 판정은 불가하다.
>
> 두 경로 모두 `signal_events`/`alert_history`를 **변경하지 않는다**(상태 머신은 스캔만 갱신).
> 판단 근거·산식은 이 문서가 정본이며, 구현 시 [METRICS_SPEC.md](./METRICS_SPEC.md)의
> "계산은 백엔드, 표시는 프론트" 원칙을 따른다.
>
> **⚠️ 실행 환경 전제:** 이 프로그램은 **24시간 서버가 아니라 macOS/Windows 데스크톱 앱**이다
> (Electron이 백엔드를 자식 프로세스로 기동). 따라서 크론 스케줄(평일 16:40 등)은 **그 시각에
> 앱이 켜져 있을 때만** 실행된다. 앱을 저녁에 열거나 며칠 만에 열면 그 사이의 수집·스캔이 통째로
> 누락된다. → **앱 시작 시 "따라잡기(catch-up)"가 선행**되어야 하며, 신호 스캔은 오늘 하루가
> 아니라 **마지막 실행 이후 놓친 모든 거래일을 소급 처리**해야 한다. (§4-1 참조)

---

## 1. 배경과 설계 원칙

분봉 단위의 단순 상하 반전은 노이즈가 심해 매매 신호로 부적합하다(과매매 유발).
대신 전통적으로 승률·손익비가 검증된 **일봉 기반 돌파-확인(breakout-confirmation) 패턴**을 채택한다.

핵심 원칙:

1. **돌파 자체가 아니라 "확인된 돌파"를 알린다.** 돌파의 40~50%는 실패하므로,
   1차 돌파는 참고 알림(LV1), 재시험 성공 또는 연속 유지 확인 후 확정 알림(LV2)을 보낸다.
2. **거래량과 수급으로 가짜 돌파를 거른다.** 거래량 배수 + 외국인·기관 순매수를 필터로 사용.
3. **과열 구간은 제외한다.** 이미 급등한 종목의 막판 돌파(소멸 갭)는 신호에서 배제.
4. **알림 남발 금지.** 종목당 쿨다운을 두고, 신호 등급을 구분한다.

---

## 2. 신호 정의

### 2-1. 용어

| 용어 | 정의 |
|------|------|
| 돌파선 (breakout level) | **당일 제외** 직전 20거래일 최고가(고가 기준) |
| 거래량 배수 | 당일 거래량 ÷ 직전 20거래일 평균 거래량 |
| 캔들 위치 | `(종가 - 저가) / (고가 - 저가)` — 1에 가까울수록 위꼬리 없이 강하게 마감 |
| 수급 순매수 | `trading_flow`의 외국인 순매수 + 기관 순매수 합 |

> **"거래일"의 정의 — 달력이 아니라 데이터 행.** 이 프로젝트에는 휴장일 달력이 없다.
> METRICS_SPEC 관행대로 **거래일 = `prices` 테이블의 행(네이버가 반환하는 실제 거래일)**로
> 센다. "직전 20거래일"은 당일 직전 20개 price 행이며, 캘린더 날짜를 역산하지 않는다.
> 이로써 공휴일·주말 처리 로직이 불필요해지고, 갭 문제는 "행이 충분히 최신인가"로 단순화된다(§4-2).

### 2-2. LV1 — 돌파 포착 (참고 알림)

당일 일봉이 확정된 시점(장 마감 수집 후)에 아래 **전부** 충족 시 발생:

| # | 조건 | 기본값 |
|---|------|--------|
| B1 | 종가 > 돌파선 | — |
| B2 | 거래량 배수 ≥ `VOL_MULT` | 2.0 |
| B3 | 캔들 위치 ≥ `CANDLE_POS_MIN` (위꼬리 긴 분산 캔들 배제) | 0.6 |
| B4 | 수급: **당일 순매수 > 0** 또는 **최근 3거래일 누적 순매수 > 0** (둘 중 하나) | — |
| B5 | 과열 아님: **당일 포함** 최근 5거래일 수익률(당일 종가 ÷ 5거래일 전 종가 − 1) < `OVERHEAT_5D` | +25% |
| B6 | 데이터 충분: 가격 데이터 ≥ `MIN_DATA_DAYS` | 30거래일 |

LV1 발생 시 `signal_events`에 `status='pending'` 레코드 생성, 돌파선을 기록한다.

> **종목당 활성 pending은 최대 1개.** pending 진행 중에 B1~B6을 다시 충족하는 날이 나와도
> (그 종가는 어차피 기존 돌파선 위이므로) 새 이벤트를 만들지 않고 기존 pending의
> C1/C2 판정 데이터로만 쓴다. 이중 pending → 이중 알림을 구조적으로 차단한다.

### 2-3. LV2 — 상승흐름 확정 (주 알림) ★

LV1 발생 후 `CONFIRM_WINDOW`(15거래일) 내에 아래 **둘 중 하나** 충족 시 확정:

| 경로 | 조건 |
|------|------|
| **C1. 재시험 성공** | 저가가 돌파선의 `RETEST_NEAR`(±2%) 이내로 접근한 날이 있고, **그날 또는 이후** 종가가 돌파선 위로 마감(접근과 재마감이 같은 날이어도 성립). 단, 재시험 기간 중 저가가 돌파선 × `FAIL_FLOOR`(0.97) 미만으로 깨진 적 없어야 함 |
| **C2. 연속 유지** | 돌파일 포함 `HOLD_DAYS`(3거래일) 연속 종가 > 돌파선 (되돌림 없이 바로 이어가는 강한 케이스) |

확정 시점에도 **수급 필터 재확인**: 확정일 기준 최근 3거래일 누적 수급 순매수 > 0.

> **C1의 저가 기준 vs failed의 종가 기준 — 의도된 비대칭.** 저가가 0.97을 깨도 종가가 회복하면
> `failed`는 아니다(§2-4는 **종가** 기준). 이 경우 C1 자격만 상실되고, 남은 확정 경로는 C2뿐이며
> C2도 이미 무산된 상태라면 그 pending은 `expired`로만 종결된다. 장중 급락으로 흔들린 돌파를
> 확정에서 배제하는 보수적 설계다.

> **상태 전이와 알림 발신은 별개다.** 상태 머신은 항상 진행(pending→confirmed 등)하고
> `signal_events`에 기록하지만, **사용자 알림(`alert_history` 기록·배지)은 정책(§3-4)에 종속**된다:
> LV1은 기본 꺼짐, LV2는 확정일이 직전 LV2로부터 `SIGNAL_COOLDOWN_DAYS`(20거래일) 이내이면 억제.
> 즉 쿨다운·on/off는 상태 판정이 아니라 **알림 발신 단계의 게이트**다.

### 2-4. 실패·만료 (알림 없음, 상태만 기록)

| 상태 | 조건 |
|------|------|
| `failed` | pending 중 종가가 돌파선 × `FAIL_FLOOR`(0.97) 미만으로 마감 (가짜 돌파 확정) |
| `expired` | `CONFIRM_WINDOW` 내 확정도 실패도 아님 |

### 2-5. 상태 머신

```
(조건 B1~B6 충족)          (C1 또는 C2)
     ──────────► pending ──────────► confirmed  → LV2 알림 ★
                   │  │
                   │  └── 종가 < 돌파선×0.97 ──► failed
                   └── 15거래일 경과 ──────────► expired
```

### 2-6. 파라미터 요약 (백엔드 상수, `constants.py`)

| 상수 | 기본값 | 설명 |
|------|--------|------|
| `SIGNAL_LOOKBACK_DAYS` | 20 | 돌파선·평균 거래량 산출 기간 |
| `SIGNAL_VOL_MULT` | 2.0 | 거래량 배수 임계 |
| `SIGNAL_CANDLE_POS_MIN` | 0.6 | 캔들 위치 하한 |
| `SIGNAL_OVERHEAT_5D` | 25.0 | 과열 제외 기준 (%) |
| `SIGNAL_MIN_DATA_DAYS` | 30 | 최소 데이터 일수 |
| `SIGNAL_CONFIRM_WINDOW` | 15 | 확정 대기 기간 (거래일) |
| `SIGNAL_RETEST_NEAR` | 0.02 | 재시험 접근 허용 폭 (±2%) |
| `SIGNAL_FAIL_FLOOR` | 0.97 | 실패 판정선 (돌파선 대비) |
| `SIGNAL_HOLD_DAYS` | 3 | 연속 유지 확정 일수 |
| `SIGNAL_COOLDOWN_DAYS` | 20 | 동일 종목 LV2 재알림 금지 기간 (거래일) |

> 기본값은 전통적 관행(오닐 CANSLIM의 거래량 40~50%↑보다 보수적인 2배,
> Donchian 20일 채널)을 따르되, 구현 후 시뮬레이션 기능으로 백테스트하여 조정한다.

---

## 3. 아키텍처

### 3-1. 전체 흐름 (두 개의 진입점)

신호 스캔은 **두 경로**로 트리거되며, 둘 다 같은 `scan_all(since)`를 호출한다(멱등).

```
경로 A — 앱 실행 중 크론                경로 B — 앱 시작 시 따라잡기 ★데스크톱 필수
─────────────────────────            ──────────────────────────────
[평일 16:40 signal_scan 잡]           [앱 기동 → lifespan startup]
  오늘 가격·수급 force 재수집                  │  (기존 _collect_*_if_needed 패턴 확장)
  (15:30 잠정치→확정치 반영)                   ▼
        │                             ① 마지막 스캔일 이후 놓친 거래일 계산
        │                             ② 데이터 갭 보충 수집 (가격·수급)
        │                             ③ 당일 16:40 이전 기동이면 오늘분은
        │                                판정하지 않음 (전 거래일까지만 재생)
        └──────────────┬──────────────────────┘
                       ▼
        signal_detector.scan_all(since=마지막_스캔일)
                       │  놓친 거래일을 오래된 순서로 하루씩 재생(replay)
                       │  → 각 종목 상태 머신 전이 (pending→confirmed/failed/expired)
                       ▼
        signal_events 테이블 (UNIQUE(ticker, breakout_date)로 재실행 안전)
                       │  알림 켜진 등급 발생 시 (기본: LV2만)
                       ▼
        alert_history 기록 (alert_type='uptrend', rule_id 연결) + last_signal_scan_date 갱신
                       │
                       ▼
        [프론트] uptrend 이력 폴링 (GET /api/alerts/uptrend)
                → uptrend 미읽음 배지 + Alerts "상승흐름 신호" 이력 섹션
                  (기존 3종 알림 벨/토스트와는 분리 — §3-5)
```

> **왜 16:40인가:** 신호가 쓰는 per-ticker `trading_flow`(외국인·기관 순매수)는 15:30 일일 수집이
> 채우는데, 네이버 투자자별 매매동향은 **장 마감 직후 잠정치**라 15:30 값이 저녁에 갱신될 수 있다.
> (현행 코드도 스크리닝용 카탈로그 수급을 별도로 16:00에 수집 — 장 마감 후 투자자 데이터에 지연을
> 두는 선례.) 따라서 스캔을 15:35에 붙이지 않고, **16:40에 오늘 가격·수급을 강제 재수집한 뒤
> (`force`) 판정**하여 가장 확정에 가까운 값을 쓴다. 잔여 잠정치 리스크는 수급이 **보조 필터**이고
> 확정(LV2)은 여러 거래일의 가격이 주도하므로 수용 가능하다.
>
> **왜 시작 시 따라잡기인가:** 데스크톱 앱은 16:40에 꺼져 있을 수 있다. 앱을 열 때마다
> 마지막 스캔 이후 놓친 거래일을 소급 처리해야 상태 머신(재시험·연속유지 판정)이 올바르게
> 진행된다. 앱이 열려 있을 때 크론이 도는 날은 경로 A가, 그 외에는 경로 B가 커버한다.

### 3-2. 백엔드

**신규: `services/signal_detector.py`**

- `detect_breakout(prices, flows) -> BreakoutSignal | None` — 순수 함수 (LV1 판정)
- `update_pending(signal, prices, flows) -> str` — pending 신호의 상태 전이 판정
- `scan_all(since: date | None)` — 활성 규칙 보유 종목 순회. **크론 잡(경로 A)**과
  **앱 시작 따라잡기(경로 B)** 양쪽에서 호출.
  - `since`부터 오늘까지의 **놓친 거래일을 오래된 순서로 하루씩 재생**하며 상태 머신 전이.
    (`since=None`이면 마지막 스캔일 = `last_signal_scan_date`에서 이어감)
  - **as-of 슬라이싱(미래 참조 금지):** 재생 날짜 D의 판정에는 **D까지의 price·flow 행만** 사용.
    돌파선·거래량 평균·수급 합계 모두 D 시점 기준으로 계산해야 소급 재생이 실시간 판정과 동일해진다.
  - 종목별로 데이터 갭 검증→보충→판정 순서. 하루도 안 놓쳤으면 즉시 반환(멱등).
  - `last_signal_scan_date`는 **전 종목 처리가 성공했을 때만** 마지막 판정 거래일로 갱신.
    일부 종목 실패(네이버 오류 등) 시 마커를 유지해 다음 스캔이 같은 구간을 재시도 —
    재생은 멱등이라 이미 처리된 종목을 다시 훑어도 안전하다.

**앱 시작 따라잡기: `_run_signal_scan_if_needed()`** (신규, `_collect_fundamentals_if_needed` 패턴 확장)

- `scheduler.start()` 말미(기존 `collect_periodic_data()` 즉시 실행 직후)에서 호출.
- `last_signal_scan_date`와 오늘을 비교해 놓친 거래일이 있으면 `scan_all(since)` 실행.
- **백그라운드로 실행**(즉시 실행 1회성 잡으로 등록): 갭 보충 수집이 낄 수 있어 수 분 걸릴 수 있으므로
  앱 기동(lifespan startup)을 블로킹하지 않는다.
- **스테일 알림 가드:** 따라잡기로 확정된 LV2라도 **확정일이 `CONFIRM_WINDOW`(15거래일)보다
  오래됐으면 알림을 띄우지 않고 이력에만 기록**한다(며칠 만에 앱 열었을 때 낡은 신호 폭탄 방지).
  최근 확정분만 토스트로 노출.

**알림 규칙 (기존 `alert_rules` 재사용)**

- 새 alert_type **`uptrend`** 추가 (`VALID_ALERT_TYPES`에 등록)
- `direction='above'` 고정, `target_price`는 미사용(0 허용하도록 검증 분기),
  `is_active`로 종목별 켜기/끄기, `last_triggered_at`으로 쿨다운 관리
- 종목별 opt-in 방식: 사용자가 규칙을 만든 종목만 스캔 (전 종목 강제 스캔 안 함)

**신규 테이블: `signal_events`** (상태 머신 저장소)

```sql
CREATE TABLE signal_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    rule_id INTEGER NOT NULL,          -- alert_rules(uptrend 규칙) 참조
    breakout_date DATE NOT NULL,       -- LV1 발생일
    breakout_level REAL NOT NULL,      -- 돌파선 (직전 20일 고가)
    volume_ratio REAL,                 -- 돌파일 거래량 배수
    candle_pos REAL,                   -- 돌파일 캔들 위치
    flow_net_3d INTEGER,               -- 돌파일 기준 3일 누적 수급
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/confirmed/failed/expired
    confirmed_date DATE,               -- LV2 확정일
    confirm_path TEXT,                 -- 'retest' | 'hold'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker),
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id),
    UNIQUE(ticker, breakout_date)
);
CREATE INDEX idx_signal_events_status ON signal_events(status, ticker);
```

**마지막 스캔일 저장 (`last_signal_scan_date`)** — 앱 재시작 간 따라잡기 기준점.
서버 메모리(스케줄러 인스턴스 변수)는 앱 종료 시 사라지므로 **DB에 영속**해야 한다.
간단히 신규 `app_state(key TEXT PRIMARY KEY, value TEXT)` 키-값 테이블에
`('last_signal_scan_date', 'YYYY-MM-DD')`로 저장하거나, 기존 메타 저장소가 있으면 재사용.
(펀더멘털 따라잡기가 `etf_holdings.date`로 판정하는 것과 동일한 발상을 신호에 맞게 명시적 상태로.)

**API 변경**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/alerts/uptrend` | uptrend 알림 이력 + `unread_count` (Query: `limit`, `offset`, `since`). 폴링·이력 화면 공용 |
| POST | `/api/alerts/uptrend/read` | 읽음 처리 (`uptrend_last_read_at` 마커 = now) → 미읽음 카운트 0 |
| DELETE | `/api/alerts/uptrend/{id}` · `?before=` | uptrend 이력 개별 삭제 / 기간 이전 일괄 정리 |
| GET | `/api/alerts/signals/{ticker}` | 종목별 signal_events 조회 (상세 페이지 배지·이력용) |
| POST/PUT/DELETE | `/api/alerts/…` | 기존 CRUD가 `uptrend` 규칙 타입을 수용하도록 검증 로직만 수정 |

> 기존 3종 알림 API(`/api/alerts/trigger`, `/api/alerts/history/{ticker}` 등)와 프론트 흐름은 **변경 없음**.
>
> **⚠️ 라우팅 등록 순서:** 기존에 `GET /api/alerts/{ticker}`(alerts.py:134)가 있으므로,
> 정적 경로 `GET /api/alerts/uptrend`는 반드시 **`{ticker}` 라우트보다 먼저 등록**해야 한다.
> FastAPI는 등록 순서대로 매칭하므로 뒤에 두면 `"uptrend"`가 티커로 해석돼 새 엔드포인트가 죽는다.
> (`/uptrend/read`, `/uptrend/{id}`, `/signals/{ticker}`는 세그먼트 수가 달라 충돌 없음.)

### 3-3. 프론트엔드

| 컴포넌트 | 변경 |
|----------|------|
| `PriceTargetPanel` | 4번째 탭 "상승흐름" — 켜기/끄기 토글 + 신호 상태 표시 (pending: "돌파 포착, 확인 대기 중", confirmed: 확정일·경로) |
| 기존 `AlertContext`/벨 | **변경 없음** — 3종 상태 알림은 현행 메모리·토스트 그대로 (§3-5) |
| uptrend 신호 UI (신규) | `GET /api/alerts/uptrend` 폴링(**저빈도, 기본 10분** — 신호는 16:40 스캔·앱 시작 시에만 생기므로 고빈도 불필요) → 미읽음 배지 + Alerts 페이지 "상승흐름 신호" 이력 섹션(페이지네이션·읽음·삭제). 백엔드가 감지·기록하므로 프론트는 조회만 |
| `ETFDetail` | 확정 신호 존재 시 헤더 근처 배지 "상승흐름 확정 (MM/DD)" |

**알림 문구 (천 단위 콤마 필수)**

- LV1: `"[삼성전자] 20일 신고가 돌파 (거래량 3.2배, 종가 78,400원) — 확인 대기"`
- LV2(재시험): `"[삼성전자] 상승흐름 확정 — 돌파선 76,900원 재시험 성공"`
- LV2(유지): `"[삼성전자] 상승흐름 확정 — 돌파 후 3일 연속 유지"`

### 3-4. 알림 정책

| 항목 | 정책 |
|------|------|
| LV1 (돌파 포착) | 기본 **끔** (설정에서 켤 수 있음 — 참고용, 실패 확률 있음을 문구에 명시) |
| LV2 (확정) | 기본 **켬** — 이 기능의 주 알림 |
| 쿨다운 | LV2 발생 후 20거래일간 동일 종목 재알림 금지 (`last_triggered_at` 기준). 단, 더 높은 돌파선의 새 LV1은 pending 기록은 함 |
| failed/expired | 알림 없음. 상세 페이지 신호 이력에서만 확인 가능 |

### 3-5. 알림의 두 종류 — 상태 알림 vs 신호 이력

두 알림은 **성격이 다르므로 이력 관리 대상도 다르다.** 섞지 않는다.

| | 기존 3종 알림 (목표가·급등락·매매시그널) | **uptrend 상승흐름 알림** |
|---|---|---|
| 성격 | **작업/상태 알림** — "지금 목표가 도달", "장중 급등" 같은 순간 통지 | **투자 판단 신호** — 며칠에 걸쳐 확정되는 매수 후보 |
| 감지 | 프론트(`useAlertChecker`), 상세 페이지 열려 있을 때 | 백엔드(`signal_detector`), 앱 시작·크론 시 |
| 유효기간 | 그 순간이 지나면 의미 옅음 | 확정 후에도 추적 가치 있음 |
| **이력 관리** | **불필요** — 세션성 토스트로 충분 | **필요** — 영속 이력 + 미읽음 배지 |

**→ 기존 3종 알림은 현행 그대로 둔다.** `AlertContext`(메모리)·토스트·세션 내 벨 목록을 바꾸지 않는다.
과거 이력을 서버에 쌓거나 읽음 상태를 영속할 필요가 없다.

**→ 히스토리·읽음 관리는 uptrend 신호에만 적용한다.**

**uptrend 알림 이력·읽음 (백엔드 정본)**

1. **저장.** uptrend 발생 시 `alert_history`에 `alert_type='uptrend'`, `rule_id`=해당 종목의
   uptrend 규칙 id(opt-in으로 이미 존재), `message`=§3-3 문구로 기록(기존 테이블 재사용).
   신호 상태 머신은 `signal_events`가, 사용자에게 보여줄 알림 항목은 `alert_history`가 담당.
   - **`triggered_at`은 스캔 시각(now)이 아니라 신호의 실제 확정 거래일**로 넣는다. 따라잡기로
     과거 신호를 뒤늦게 기록해도 읽음 마커 비교(아래)가 올바르게 동작하고, 시간순 정렬이 맞는다.
2. **읽음 상태 — 마커 방식.** `app_state`에 `uptrend_last_read_at`(timestamp) 저장.
   **미읽음 = `alert_history`에서 `alert_type='uptrend' AND triggered_at > uptrend_last_read_at`인 건수.**
   개별 read 플래그보다 단순하고, 데스크톱 재시작 간에도 유지된다.
   (스테일 가드로 토스트는 억제돼도, 사용자가 못 본 확정은 배지·이력에는 정상 노출된다.)
3. **API** (§3-2 표 참조): `GET /api/alerts/uptrend`(이력 + `unread_count`, 페이지네이션),
   `POST /api/alerts/uptrend/read`(마커=now), `DELETE /api/alerts/uptrend/{id}`·`?before=`(이력 정리).
4. **프론트.** uptrend 미읽음 배지 + 전용 이력 뷰. 기존 벨과 **분리하거나**(별도 "신호" 배지),
   같은 벨에 두더라도 uptrend만 영속·읽음 관리하고 3종은 세션성으로 공존시킨다.
   → 구현 시 UX 택1 (기본 권장: **Alerts 페이지에 "상승흐름 신호" 이력 섹션**을 별도로 두고,
   nav의 uptrend 미읽음 배지로 유도. 기존 벨 드롭다운은 현행 유지).

**보존 정책**

- uptrend `alert_history`는 누적, 조회는 페이지네이션. 기본 **180일 초과분**은 앱 시작 시 1회 점검 정리(선택).

---

## 4. 백엔드 수집기 변경사항 (신규/수정 필요)

> 신호 감지기는 **연속된 20거래일 이상의 정확한 가격·거래량·수급 데이터**를 전제한다.
> 현행 수집 로직을 점검한 결과, 이 전제를 깨는 4가지 공백이 있어 **수집기 자체를 보강해야 한다.**
> 기존 기능 재사용만으로는 신호 품질을 보장할 수 없다.

### 4-1. [신규] 신호 스캔 — 크론 잡 + 앱 시작 따라잡기 (데스크톱 필수)

- **문제 A (타이밍):** 신호가 쓰는 per-ticker `trading_flow`는 15:30 일일 수집이 채우지만
  네이버 투자자별 매매동향은 장 마감 직후 **잠정치**라 저녁에 갱신될 수 있다. 15:35에 스캔하면
  수급 필터(B4/LV2 재확인)가 잠정 값으로 판정될 수 있다. (스크리닝용 카탈로그 수급을 16:00에
  따로 수집하는 것도 같은 이유의 선례.)
- **문제 B (데스크톱 앱):** 크론은 그 시각 앱이 켜져 있어야만 실행된다. 앱을 저녁에/며칠 만에
  열면 그 사이 스캔이 통째로 누락되고, pending 신호의 재시험·연속유지 판정이 진행되지 않는다.
- **변경:**
  1. `scheduler.py`에 크론 잡 `signal_scan` 추가 — 평일 **16:40 KST**(펀더멘털 16:30 이후).
     **오늘 가격·수급을 `force` 재수집**한 뒤 `scan_all()` 호출. → 앱이 그 시각 켜져 있는 날 커버.
  2. **앱 시작 따라잡기** `_run_signal_scan_if_needed()`를 `scheduler.start()` 말미에 추가
     (기존 `_collect_fundamentals_if_needed()` 바로 다음). `last_signal_scan_date` 이후 놓친
     거래일이 있으면 데이터 갭 보충 후 `scan_all(since)` 소급 실행. → 크론을 놓친 날 커버.
     (잠정/확정 여부는 데이터로 구분할 수 없으므로 **시각 규칙**으로 처리: 당일 16:40 이전 기동이면
     오늘분은 판정하지 않고 전 거래일까지만 재생 — 오늘분은 16:40 크론 또는 다음 기동이 처리.)
  3. 두 경로 모두 `scan_all(since)` 하나로 수렴하며 멱등(재실행 안전). 스테일 알림 가드로
     오래된 확정은 이력만 남기고 토스트 억제(§3-2 참조).
- **파일:** `services/scheduler.py`(크론 잡 + 따라잡기 메서드), `services/signal_detector.py`(신규),
  `app_state` 테이블(마지막 스캔일 영속).

### 4-2. [수정] 신호 스캔 직전 데이터 갭 검증·보충

- **문제:** `collect_and_save_prices_smart`가 쓰는 `calculate_missing_days`는
  수집량을 `min(days_gap, requested_days)`로 캡한다. 주기·일일 수집은 모두 `days=1`이라,
  **하루라도 수집이 누락되면(서버 다운·네이버 실패·공휴일 오판) 그 갭은 일일 수집으로 영영 메워지지 않는다.**
  현재는 일요일 02:00 90일 백필만 갭을 메운다. 이 상태로 신호를 돌리면 20일 창 중간에
  구멍이 생겨 **돌파선·거래량 배수가 왜곡 → 가짜 신호 또는 신호 누락**이 발생한다.
- **핵심:** 휴장일 달력이 없으므로 "내부 누락일"을 캘린더로 탐지하지 않는다. 네이버는 요청 일수만큼
  **연속된 거래일을 반환**하므로, **충분한 달력일수만 요청하면 빠진 거래일 행이 자동으로 채워진다.**
  진짜 버그는 `calculate_missing_days`가 요청량을 `min(gap, requested_days=1)`로 캡해 **덜 가져오는 것**뿐이다.
- **변경:** `signal_detector`가 종목별 판정 **전에** `ensure_recent_history(ticker)` 호출.
  - 마지막 저장 가격일과 오늘의 간격(달력일)을 구해 **캡 없이 그만큼 요청** → 빠진 거래일 행 보충.
  - 보충 후 price 행 수가 `SIGNAL_MIN_DATA_DAYS`(30) 미만이면 데이터 부족으로 판정 보류(§4-4).
  - 신규 종목(이력 0)은 §4-3의 초기 백필로 처리.
  - (선택) 근본 개선: 일일 수집도 `days=1` 대신 `days=5`로 올려 단기 갭을 상시 자연 보충.

### 4-3. [수정] 신규 종목 등록 시 히스토리 자동 백필

- **문제:** `settings.py`의 `create_stock`은 stocks.json 추가 + 캐시 무효화만 한다.
  가격·수급 히스토리 수집을 **트리거하지 않는다.** 신규 등록 종목은 다음 수집부터
  하루치씩만 쌓여 신호에 필요한 30거래일 확보에 **한 달 이상** 걸린다.
- **변경:** `create_stock` 성공 후 백그라운드로 초기 백필 트리거
  (`asyncio.to_thread`로 `collect_and_save_prices` + `collect_and_save_trading_flow`,
  기본 **`days=90` 달력일** — 기존 주간 백필과 동일 단위, 약 60거래일 확보로
  `SIGNAL_MIN_DATA_DAYS`(30행)를 여유 있게 충족). 대량 등록·rate limit 고려해 백그라운드로 처리하고,
  수집 완료 전에는 해당 종목 신호 판정을 보류(§4-4의 데이터 충분성 가드가 처리).
- **파일:** `routers/settings.py`(`create_stock`), 필요 시 `services/data_collector.py` 헬퍼.

### 4-4. [수정] 수급·거래량 결측의 명시적 처리

- **문제:** `_collect_single_ticker`에서 **매매동향 수집 실패는 로그만 남기고**
  `ticker_success`에 반영하지 않는다(가격만 성공해도 종목 전체는 success 처리).
  신호 감지기는 수급을 필수 필터로 쓰므로, 수급 결측을 감지기가 인지하지 못하면
  **필터 없이 잘못된 신호**를 낼 수 있다.
- **변경:**
  - `signal_detector`는 판정에 필요한 가격·거래량·수급 중 **하나라도 결측/부족이면 신호 발생 안 하고 `pending` 판정 보류**(다음날 소급). 조용히 통과 금지.
  - `collection_status`에 매매동향 최신일(`last_trading_flow_date`)이 신뢰성 있게 기록되는지 확인하고, 감지기는 이 값으로 수급 신선도를 검증.
  - 거래량 0 또는 NULL 캔들은 배수 계산에서 제외하고 데이터 충분성 판단에 반영.

### 4-5. 변경 요약

| 파일 | 종류 | 내용 |
|------|------|------|
| `services/signal_detector.py` | 신규 | LV1/LV2 판정, 갭 검증, `scan_all(since)` 날짜 소급 재생 |
| `services/scheduler.py` | 수정 | 크론 잡 `signal_scan`(평일 16:40) + **`_run_signal_scan_if_needed()` 앱 시작 따라잡기** |
| `services/data_collector.py` | 수정 | `ensure_recent_history()` (캡 없는 달력일 요청으로 갭 보충 + 행 수 충분성 검증) |
| `services/trading_flow_collector.py` | 확인 | 수급 최신일 기록·결측 시그널 정확성 점검 |
| `routers/settings.py` | 수정 | `create_stock` 후 초기 백필(`days=90` 달력일) 트리거 |
| `routers/alerts.py` | 수정 | `uptrend` 규칙 수용, `uptrend` 이력(+`unread_count`)·`read`·삭제·`signals` 엔드포인트 |
| `constants.py` / `database.py` | 수정 | 파라미터 상수, `signal_events` 테이블, `app_state`(마지막 스캔일 + `uptrend_last_read_at`) |
| uptrend 신호 UI (신규) | 신규 | 미읽음 배지 + Alerts "상승흐름 신호" 이력 섹션(폴링·읽음·삭제). **기존 `AlertContext`/벨/`Alerts` 기존 이력은 변경 없음** |

---

## 5. 구현 단계

### Phase 1 — 수집기 보강 (신호의 데이터 전제 확보) ★선행
1. `data_collector.ensure_recent_history()` — 캡 없는 갭 보충 + 행 수 검증 (단위 테스트 포함)
2. `create_stock` 초기 백필(`days=90` 달력일) 트리거
3. 매매동향 결측 처리·`last_trading_flow_date` 기록 정확성 점검
4. **테스트**: 갭 있는 데이터·신규 종목·수급 결측 시나리오 (임시 DB, Given-When-Then)

### Phase 2 — 백엔드 감지기 + uptrend 이력 (핵심)
5. `constants.py` 파라미터 추가, `signal_events`·`app_state`(마지막 스캔일 + `uptrend_last_read_at`) 테이블 + 마이그레이션
6. `services/signal_detector.py` 구현 (`scan_all(since)` 날짜 소급 재생, §4-2·4-4 가드 포함)
7. `alerts.py`: `uptrend` 규칙 수용, uptrend 발생 시 `alert_history` 기록, `GET /api/alerts/signals/{ticker}`
8. uptrend 이력·읽음 API: `GET /api/alerts/uptrend`(+`unread_count`)·`POST …/read`·`DELETE …/{id}`
9. 스케줄러: 크론 잡 `signal_scan`(평일 16:40) + `_run_signal_scan_if_needed()` 앱 시작 따라잡기
10. **테스트**: LV1/C1/C2/failed/expired + 며칠치 소급 재생·스테일 가드 + 미읽음 카운트·재시작 후 이력 유지

### Phase 3 — 프론트 신호 연동
11. PriceTargetPanel "상승흐름" 탭, uptrend 미읽음 배지 + Alerts "상승흐름 신호" 이력 섹션(읽음·삭제), 상세 배지
12. msw 목 + 컴포넌트 테스트 (**기존 벨/AlertContext는 건드리지 않음**)

### Phase 4 — 검증·조정 (선택)
13. 등록 종목 과거 1년치로 신호 재현(replay) 스크립트 → 신호 빈도·이후 수익률 리포트
14. 파라미터 조정 (VOL_MULT, CONFIRM_WINDOW 등)

### 문서 갱신 대상 (구현 시)
- [API_SPECIFICATION.md](./API_SPECIFICATION.md) · [API_MANUAL.md](./API_MANUAL.md) — 신규 엔드포인트(uptrend 이력·read·삭제·signals)
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) — `signal_events`, `app_state`
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 신규 서비스·스케줄러 잡
- [FEATURES.md](./FEATURES.md) — uptrend 신호 알림·이력·미읽음 배지
- [METRICS_SPEC.md](./METRICS_SPEC.md) — 판정 기준 표에 uptrend 추가 (이 문서 링크)
- SDK 재생성: `bash sdk/generate.sh`

---

## 6. 한계와 주의 (사용자 안내 문구에 반영)

- 이 신호는 **추세추종 진입 후보 알림**이지 매수 지시가 아니다. 확정 신호도 실패할 수 있다.
- 일봉·수급 확정 후 판정하므로 알림은 **장 마감 후(16:40~) 도착**한다. 장중 실시간 아님 — 의도된 설계
  (장중 판정은 미확정 캔들·잠정 수급 기준이라 가짜 신호가 급증).
- **데스크톱 앱 특성:** 앱이 꺼져 있으면 그 시간 크론은 못 돈다. 다음에 앱을 열 때 따라잡기가
  놓친 거래일을 소급 처리하므로 **신호가 사라지지는 않지만, 앱을 연 시점에야** 알림이 도착한다.
  여러 날 만에 열면 그 사이 확정된 오래된 신호는 이력에만 남고 토스트로는 최근분만 뜬다(스테일 가드).
- 데이터가 네이버 수집 기반이므로 수집 실패일에는 판정이 하루 밀릴 수 있다.
  §4-2/4-4의 갭 보충·결측 보류 로직으로 **틀린 신호 대신 지연**되도록 설계한다.
- 손절·트레일링 스톱 등 **청산 관리 알림은 별도 설계** (본 문서 범위 외, 후속 검토).
