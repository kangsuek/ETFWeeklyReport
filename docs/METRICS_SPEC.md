# 지표 산식 명세 (METRICS SPEC)

> **목적:** 백엔드↔프론트가 같은 지표를 서로 다르게 계산해 생긴 불일치
> (예: 변동성 라벨 사건 — 백엔드 1년 연환산 vs 프론트 최근 N일 일간)의 재발 방지.
> 모든 지표 **계산의 정본(single source of truth)은 백엔드**이며, 프론트엔드는 표시만 담당한다.
>
> **정본 구현:** `backend/app/services/metrics_service.py` (단위 테스트: `backend/tests/test_metrics_service.py`)

## 원칙

1. **계산은 백엔드, 표시는 프론트.** 프론트에서 새 지표가 필요하면 백엔드 API에 추가하고 응답을 표시한다.
2. **기간(표본)을 라벨에 명시한다.** 변동성·수익률 등 기간 의존 지표는 사용자에게 보여줄 때
   반드시 표본 기간을 함께 표기한다 (예: "최근 30일 일간 2.1%", "1년 연환산 35%").
3. **예외 — 차트 시리즈:** 가격 차트 위에 그리는 RSI/MACD **라인(시리즈)**은 이미 로드된 가격
   배열의 시각화이므로 `frontend/src/utils/technicalIndicators.js`에서 계산한다.
   단, 산식은 아래 명세와 동일해야 하며, 시그널 **텍스트/판정**(과매수·골든크로스 등)은
   백엔드 InsightsService가 정본이다.

## 산식

| 지표 | 산식 | 파라미터/기준 |
|---|---|---|
| 기간 수익률 | `(종료 종가 - 시작 종가) / 시작 종가 × 100` | 조회 기간의 첫/마지막 거래일 종가 |
| 연환산 수익률 | `((1 + 기간수익률)^(365 / 거래일수) - 1) × 100` (복리) | 거래일수 = 데이터 포인트 수. **60거래일(약 3개월) 미만은 연환산하지 않고 "N일 수익률"로 표기** |
| 일간 변동성 | 일간 수익률의 **모표준편차** × 100 (%) | 일간 수익률 = `(오늘 종가 - 전일 종가) / 전일 종가` |
| 연환산 변동성 | `일간 변동성 × √252` | 연간 거래일 252일 |
| 최대 낙폭 (MDD) | 시간순 진행하며 `max((고점 - 현재가) / 고점) × 100` | 조회 기간 내 종가 기준 |
| 샤프 비율 | `(연환산 수익률 - 무위험수익률) / 연환산 변동성` | 무위험수익률은 `get_etf_metrics` 구현 참조 |
| RSI | Wilder's smoothing, 기간 14 | 첫 평균은 SMA, 이후 `(이전평균 × 13 + 오늘값) / 14`. avg_loss=0이면 RS=100 |
| MACD | `EMA(12) - EMA(26)`, Signal = MACD의 `EMA(9)` | EMA 첫 값은 SMA, 승수 `2/(기간+1)` |
| 뉴스 감성/토픽 | 키워드 규칙 기반 | 정본: `backend/app/services/news_analyzer.py` (`GET /api/news/{ticker}?analyze=true`) |

## 인사이트 판정 기준 (InsightsService)

| 판정 | 기준 |
|---|---|
| 단기 상승/하락 추세 | 현재가 > MA5 > MA20 (상승) / 현재가 < MA5 < MA20 (하락) |
| 골든/데드크로스 (MA) | 5거래일 전 대비 MA5·MA20 교차 |
| 변동성 확대/안정 | 조회 기간 일간 변동성 > 3% (확대) / < 1% (안정) — **라벨에 "최근 N일 일간" 명시** |
| 20일 고가/저가 근접 | (고가-현재가) 또는 (현재가-저가)가 20일 범위의 5% 미만 |
| 연속 상승/하락 | `daily_change_pct` 기준 4일 이상 (최근 10일 내) |
| RSI 과매수/과매도 | RSI ≥ 70 (과매수) / ≤ 30 (과매도), 데이터 30건 이상일 때 |
| MACD 크로스 | 직전 대비 MACD-Signal 부호 교차, 데이터 40건 이상일 때 |
| 외국인/기관 연속 | 순매수(도) 3일 이상 연속 |
| 리스크: 높은 변동성 | 조회 기간 일간 변동성 > 4% |
| 리스크: 동반 순매도 | 외국인+기관 모두 3일 연속 순매도 |
| 리스크: 급락일 | 최근 5일 내 일간 -5% 초과 하락일 존재 |

## 상승흐름(uptrend) 신호 판정 (SignalDetector)

거래량 동반 돌파의 **확정(LV2)** 여부를 판정해 알림으로 발신한다. 상세 산식·파라미터·
상태 머신은 정본 문서 [UPTREND_SIGNAL_DESIGN.md](./UPTREND_SIGNAL_DESIGN.md) §2 참조.

| 판정 | 기준 (기본 파라미터) |
|---|---|
| LV1 돌파 | 종가 > 직전 20거래일 고가 + 거래량 ≥ 평균 2배 + 캔들 위치 ≥ 0.6 + 수급(당일 또는 3일 누적 순매수 > 0) + 5일 수익률 < 25% + 데이터 ≥ 30행 |
| LV2 확정 (재시험) | 저가가 돌파선 ±2% 접근 후 종가가 돌파선 재돌파, 재시험 중 저가가 돌파선×0.97 미붕괴 |
| LV2 확정 (연속유지) | 돌파일 포함 3거래일 연속 종가 > 돌파선 |
| 실패/만료 | 종가가 돌파선×0.97 미만 마감(failed) / 15거래일 내 미확정(expired) |
| 알림 억제 | 직전 LV2로부터 20거래일 이내 재확정 시(쿨다운) |

> "거래일" = `prices` 테이블 행(휴장일 달력 없음, 본 문서 원칙과 동일). 계산은 백엔드
> `signal_detector.py` 순수 함수가 정본, `as_of` 슬라이싱으로 미래 데이터 누수 차단.
>
> **하락흐름(downtrend)은 위 표의 거울상**이다(`direction='down'`): 20일 **저점 하향 이탈** +
> 하단 마감 + **순매도** + 과매도(-25%) 제외, 확정은 반등 후 **재이탈**/연속 이탈, 실패선은
> 이탈선×1.03. 같은 감지기를 부호(`_sign`)로 대칭 처리한다.

## 구현 위치 현황

| 소비처 | API | 계산 위치 |
|---|---|---|
| ETFDetail 인사이트 요약 | `GET /api/etfs/{ticker}/insights` | `insights_service.py` + `metrics_service.py` |
| ETFDetail 전략 요약 | 〃 | `insights_service.py` |
| ETF 헤더/카드 지표 | `GET /api/etfs/{ticker}/metrics` | `data_collector.get_etf_metrics` |
| 종목 비교 | `GET /api/etfs/compare` | `comparison_service.py` |
| 뉴스 타임라인 감성 | `GET /api/news/{ticker}?analyze=true` | `news_analyzer.py` |
| 차트 RSI/MACD 라인 | (가격 데이터 재활용) | `frontend/utils/technicalIndicators.js` (시각화 전용) |
| 상승흐름 신호·이력 | `GET /api/alerts/signals/{ticker}`, `GET /api/alerts/uptrend` | `signal_detector.py` (`scheduler` 16:40 잡·기동 따라잡기) |

> `get_etf_metrics`·`comparison_service`의 자체 산식은 위 명세와 일치해야 하며,
> 장기적으로 `metrics_service` 프리미티브 재사용으로 통합한다.
